"""
analytics/services.py
Сервисный модуль предиктивной аналитики, прогнозирования исчерпания запасов,
агрегации данных для визуализации и email-оповещений о дефиците.

Студент: Нестерук Д.С., группа ПО-2409
"""

import csv
import datetime
from decimal import Decimal
from io import StringIO
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Sum, Q, F
from django.utils import timezone

from inventory.models import Product, StockMovement, Category


# ---------------------------------------------------------------------------
# 1. ПРЕДИКТИВНЫЙ АЛГОРИТМ И ПРОГНОЗИРОВАНИЕ ЗАПАСОВ
# ---------------------------------------------------------------------------

def calculate_product_forecast(product: Product, days: int = 30, lead_time_days: int = 7) -> Dict[str, Any]:
    """
    Рассчитать прогноз расхода и сроки исчерпания запаса для одного товара.

    Параметры:
        product:        Экземпляр модели Product.
        days:           Период анализа истории расхода (по умолчанию 30 дней).
        lead_time_days: Ожидаемый срок поставки от поставщика в днях (по умолчанию 7).

    Возвращает словарь:
        - product: экземпляр товара
        - current_quantity: текущий остаток
        - min_quantity: минимальный порог
        - period_days: число дней анализа
        - total_usage: суммарный расход за период
        - adu: среднесуточный расход (Average Daily Usage)
        - days_until_stockout: дней до исчерпания запаса (float или None)
        - stockout_date: прогнозная дата полного исчерпания (date или None)
        - reorder_point: точка заказа (ROP)
        - recommended_reorder_qty: рекомендуемый объём дозаказа
        - reorder_date: рекомендованная дата размещения заказа (date или None)
        - status: 'critical' | 'warning' | 'normal' | 'no_demand'
        - status_label: текстовое описание статуса
        - status_badge_class: Bootstrap-класс для индикатора
    """
    now = timezone.now()
    start_date = now - datetime.timedelta(days=days)

    # Суммируем фактический расход (out) за период
    out_usage = StockMovement.objects.filter(
        product=product,
        operation_type=StockMovement.OperationType.OUT,
        created_at__gte=start_date
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # Также учитываем списания (writeoff), если они были
    writeoff_usage = StockMovement.objects.filter(
        product=product,
        operation_type=StockMovement.OperationType.WRITEOFF,
        created_at__gte=start_date
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_usage = out_usage + writeoff_usage

    # Среднесуточный расход (ADU)
    adu = round(total_usage / days, 2) if days > 0 else 0.0

    current_qty = product.quantity
    min_qty = product.min_quantity

    # Точка заказа (Reorder Point, ROP): спрос за время доставки + страховой запас (min_quantity)
    # ROP = (ADU * lead_time) + min_quantity
    rop = int(round(adu * lead_time_days + min_qty))

    days_until_stockout: Optional[float] = None
    stockout_date: Optional[datetime.date] = None
    reorder_date: Optional[datetime.date] = None
    today = timezone.localdate()

    if current_qty == 0:
        days_until_stockout = 0.0
        stockout_date = today
        reorder_date = today
        status = 'critical'
        status_label = 'Товар исчерпан'
        status_badge_class = 'bg-danger'
        # Рекомендуем заказать запас на 30 дней + мин. порог
        recommended_reorder_qty = max(min_qty * 2, int(round(adu * 30 + min_qty))) if adu > 0 else max(min_qty, 10)

    elif adu > 0:
        days_until_stockout = round(current_qty / adu, 1)
        stockout_date = today + datetime.timedelta(days=int(days_until_stockout))

        # Дата дозаказа: за lead_time_days до stockout_date, но не раньше сегодня
        reorder_day_offset = max(0, int(days_until_stockout - lead_time_days))
        reorder_date = today + datetime.timedelta(days=reorder_day_offset)

        # Рекомендуемый объём: пополнение до покрытия 30-дневного расхода + min_quantity
        target_stock = int(round(adu * 30 + min_qty))
        recommended_reorder_qty = max(0, target_stock - current_qty)
        if recommended_reorder_qty == 0 and current_qty <= min_qty:
            recommended_reorder_qty = max(min_qty, int(round(adu * 14)))

        if days_until_stockout <= lead_time_days or current_qty <= min_qty:
            status = 'critical'
            status_label = 'Срочный заказ'
            status_badge_class = 'bg-danger'
        elif days_until_stockout <= 14:
            status = 'warning'
            status_label = 'Внимание: истощение'
            status_badge_class = 'bg-warning text-dark'
        else:
            status = 'normal'
            status_label = 'Запас достаточен'
            status_badge_class = 'bg-success'

    else:
        # adu == 0 — за выбранный период расхода не было
        days_until_stockout = None
        stockout_date = None
        reorder_date = None
        recommended_reorder_qty = max(0, min_qty - current_qty) if current_qty < min_qty else 0

        if current_qty <= min_qty:
            status = 'warning'
            status_label = 'Ниже минимума (нет расхода)'
            status_badge_class = 'bg-warning text-dark'
        else:
            status = 'no_demand'
            status_label = 'Без движения'
            status_badge_class = 'bg-secondary'

    return {
        'product': product,
        'current_quantity': current_qty,
        'min_quantity': min_qty,
        'period_days': days,
        'lead_time_days': lead_time_days,
        'total_usage': total_usage,
        'adu': adu,
        'days_until_stockout': days_until_stockout,
        'stockout_date': stockout_date,
        'reorder_point': rop,
        'recommended_reorder_qty': recommended_reorder_qty,
        'reorder_date': reorder_date,
        'status': status,
        'status_label': status_label,
        'status_badge_class': status_badge_class,
    }


def get_all_products_forecast(days: int = 30, lead_time_days: int = 7, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Получить прогноз по всем товарам склада с сортировкой по срочности заказа.
    """
    queryset = Product.objects.select_related('category', 'supplier').all()
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    forecasts = [
        calculate_product_forecast(p, days=days, lead_time_days=lead_time_days)
        for p in queryset
    ]

    # Сортировка: сначала критические (наименьшее число дней до исчерпания), затем warning, normal, no_demand
    def sort_key(item):
        status_priority = {'critical': 0, 'warning': 1, 'normal': 2, 'no_demand': 3}
        prio = status_priority.get(item['status'], 9)
        days_val = item['days_until_stockout'] if item['days_until_stockout'] is not None else 9999
        return (prio, days_val, item['product'].name)

    forecasts.sort(key=sort_key)
    return forecasts


# ---------------------------------------------------------------------------
# 2. АГРЕГАЦИЯ ДАННЫХ ДЛЯ ГРАФИКОВ CHART.JS
# ---------------------------------------------------------------------------

def get_movement_dynamics_data(days: int = 30) -> Dict[str, Any]:
    """
    Динамика поступлений (IN) и отгрузок (OUT) за последние N дней.
    Возвращает структуру для передачи в Chart.js line/bar chart.
    """
    today = timezone.localdate()
    start_date = today - datetime.timedelta(days=days - 1)

    # Список дат в формате 'ДД.ММ'
    date_list = [start_date + datetime.timedelta(days=i) for i in range(days)]
    labels = [d.strftime('%d.%m') for d in date_list]

    # Запрашиваем движения за период
    movements = StockMovement.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=today,
        operation_type__in=[StockMovement.OperationType.IN, StockMovement.OperationType.OUT]
    ).values('created_at__date', 'operation_type').annotate(total_qty=Sum('quantity'))

    in_map = {}
    out_map = {}
    for m in movements:
        d = m['created_at__date']
        op = m['operation_type']
        qty = m['total_qty'] or 0
        if op == StockMovement.OperationType.IN:
            in_map[d] = in_map.get(d, 0) + qty
        elif op == StockMovement.OperationType.OUT:
            out_map[d] = out_map.get(d, 0) + qty

    in_data = [in_map.get(d, 0) for d in date_list]
    out_data = [out_map.get(d, 0) for d in date_list]

    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Поступление (Приход)',
                'data': in_data,
                'borderColor': '#198754',
                'backgroundColor': 'rgba(25, 135, 84, 0.15)',
                'tension': 0.3,
                'fill': True,
            },
            {
                'label': 'Отгрузка (Расход)',
                'data': out_data,
                'borderColor': '#0d6efd',
                'backgroundColor': 'rgba(13, 110, 253, 0.15)',
                'tension': 0.3,
                'fill': True,
            }
        ]
    }


def get_category_distribution_data() -> Dict[str, Any]:
    """
    Структура запасов по категориям (круговая диаграмма):
    Количество товаров и суммарная балансовая стоимость по каждой категории.
    """
    categories = Category.objects.all().order_by('name')

    labels = []
    quantities = []
    costs = []

    palette = [
        '#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0',
        '#6f42c1', '#fd7e14', '#20c997', '#6c757d', '#d63384'
    ]

    for cat in categories:
        products = cat.products.all()
        total_qty = sum(p.quantity for p in products)
        total_cost = float(sum(p.total_cost for p in products))

        if total_qty > 0 or total_cost > 0:
            labels.append(cat.name)
            quantities.append(total_qty)
            costs.append(round(total_cost, 2))

    if not labels:
        labels = ['Нет данных']
        quantities = [0]
        costs = [0.0]

    colors = [palette[i % len(palette)] for i in range(len(labels))]

    return {
        'labels': labels,
        'quantities': quantities,
        'costs': costs,
        'colors': colors,
    }


def get_top_outgoing_products(limit: int = 5, days: int = 30) -> Dict[str, Any]:
    """
    ТОП-N самых расходуемых позиций за последние N дней (горизонтальная гистограмма).
    """
    start_date = timezone.now() - datetime.timedelta(days=days)

    top_movements = (
        StockMovement.objects
        .filter(
            operation_type=StockMovement.OperationType.OUT,
            created_at__gte=start_date
        )
        .values('product__name', 'product__sku')
        .annotate(total_out=Sum('quantity'))
        .order_by('-total_out')[:limit]
    )

    labels = []
    data = []

    for item in top_movements:
        name = item['product__name']
        sku = item['product__sku']
        labels.append(f"{name} ({sku})")
        data.append(item['total_out'])

    return {
        'labels': labels,
        'data': data,
    }


# ---------------------------------------------------------------------------
# 3. ЭКСПОРТ ОТЧЁТОВ В CSV (UTF-8 С BOM ДЛЯ EXCEL)
# ---------------------------------------------------------------------------

def generate_inventory_csv(only_low_stock: bool = False) -> str:
    """
    Сформировать CSV-файл номенклатуры и остатков с кодировкой UTF-8 BOM,
    корректно открывающийся в Microsoft Excel и LibreOffice Calc.
    """
    output = StringIO()
    writer = csv.writer(output, delimiter=';', dialect='excel')

    # Заголовок таблицы
    writer.writerow([
        'Артикул (SKU)',
        'Наименование товара',
        'Категория',
        'Поставщик',
        'Ед. изм.',
        'Цена за ед. (руб.)',
        'Текущий остаток',
        'Мин. порог',
        'Статус запаса',
        'Балансовая стоимость (руб.)',
    ])

    queryset = Product.objects.select_related('category', 'supplier').all().order_by('name')
    if only_low_stock:
        queryset = queryset.filter(quantity__lte=F('min_quantity'))

    for p in queryset:
        if p.is_out_of_stock:
            status_text = 'Отсутствует'
        elif p.is_low_stock:
            status_text = 'Дефицит'
        else:
            status_text = 'В норме'

        writer.writerow([
            p.sku,
            p.name,
            p.category.name if p.category else '—',
            p.supplier.name if p.supplier else '—',
            p.get_unit_display(),
            f"{p.price:.2f}".replace('.', ','),
            p.quantity,
            p.min_quantity,
            status_text,
            f"{p.total_cost:.2f}".replace('.', ','),
        ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# 4. EMAIL-ОПОВЕЩЕНИЯ О ДЕФИЦИТЕ
# ---------------------------------------------------------------------------

def send_low_stock_notification(recipient_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Проверить дефицитные позиции (quantity <= min_quantity)
    и отправить служебное email-уведомление администратору/менеджеру.
    """
    recipient = recipient_email or getattr(settings, 'LOW_STOCK_EMAIL_RECIPIENT', 'admin@example.com')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'warehouse@example.com')

    deficit_products = Product.objects.filter(
        quantity__lte=F('min_quantity')
    ).select_related('category', 'supplier').order_by('quantity')

    count = deficit_products.count()

    if count == 0:
        return {
            'success': True,
            'count': 0,
            'message': 'Дефицитных позиций не обнаружено. Отправка уведомления не требуется.'
        }

    lines = [
        "СИСТЕМА УПРАВЛЕНИЯ СКЛАДОМ — ОПОВЕЩЕНИЕ О ДЕФИЦИТЕ",
        "=" * 60,
        f"Дата формирования: {timezone.now().strftime('%d.%m.%Y %H:%M')}",
        f"Количество позиций, требующих внимания: {count}",
        "-" * 60,
        f"{'SKU':<12} | {'Наименование':<25} | {'Остаток':<8} | {'Мин.':<5} | {'Поставщик'}",
        "-" * 60,
    ]

    for p in deficit_products:
        supp_name = p.supplier.name if p.supplier else "Не указан"
        lines.append(
            f"{p.sku:<12} | {p.name[:25]:<25} | {p.quantity:<8} | {p.min_quantity:<5} | {supp_name}"
        )

    lines.extend([
        "-" * 60,
        "Пожалуйста, сформируйте заказы на закупку в веб-интерфейсе системы:",
        f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/suppliers/orders/create/",
        "=" * 60,
    ])

    subject = f"⚠️ Внимание: {count} товарных позиций в дефиците на складе"
    body = "\n".join(lines)

    try:
        sent = send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return {
            'success': True,
            'count': count,
            'sent': sent,
            'recipient': recipient,
            'message': f"Служебное уведомление по {count} дефицитным позициям успешно отправлено на {recipient}."
        }
    except Exception as exc:
        return {
            'success': False,
            'count': count,
            'error': str(exc),
            'message': f"Ошибка отправки email: {exc}"
        }
