"""
analytics/views.py
Контроллеры подсистемы аналитики и прогнозирования:
- Сводный аналитический дашборд с интерактивными графиками
- Предиктивный прогноз исчерпания складских запасов (ADU / Stockout Date)
- JSON API для асинхронного обновления Chart.js
- Экспорт отчётов в формате CSV (Excel-совместимый)
- Отправка email-оповещений о дефиците

Студент: Нестерук Д.С., группа ПО-2409
"""

import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.utils import timezone

from accounts.decorators import manager_or_admin_required
from inventory.models import Product, Category, StockMovement
from .services import (
    calculate_product_forecast,
    get_all_products_forecast,
    get_movement_dynamics_data,
    get_category_distribution_data,
    get_top_outgoing_products,
    generate_inventory_csv,
    send_low_stock_notification,
)


# ===========================================================================
# 1. СВОДНЫЙ АНАЛИТИЧЕСКИЙ ДАШБОРД
# ===========================================================================

@manager_or_admin_required
def analytics_dashboard(request):
    """
    Главная страница аналитики склада.
    Включает агрегированные финансовые и количественные KPI,
    а также исходные данные для трёх графиков Chart.js.
    """
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(quantity__lte=F('min_quantity')).count()
    out_of_stock_count = Product.objects.filter(quantity=0).count()

    # Суммарная балансовая стоимость склада
    all_products = Product.objects.all()
    total_warehouse_value = sum(p.total_cost for p in all_products)
    total_units_in_stock = sum(p.quantity for p in all_products)

    # Движения за последние 30 дней
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    month_movements = StockMovement.objects.filter(created_at__gte=thirty_days_ago)
    incoming_total = month_movements.filter(
        operation_type=StockMovement.OperationType.IN
    ).aggregate(total=Sum('quantity'))['total'] or 0

    outgoing_total = month_movements.filter(
        operation_type=StockMovement.OperationType.OUT
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # Данные для графиков
    dynamics_data = get_movement_dynamics_data(days=30)
    category_data = get_category_distribution_data()
    top_outgoing_data = get_top_outgoing_products(limit=5, days=30)

    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_warehouse_value': total_warehouse_value,
        'total_units_in_stock': total_units_in_stock,
        'incoming_total': incoming_total,
        'outgoing_total': outgoing_total,

        # JSON-сериализованные данные для мгновенной инициализации Chart.js
        'dynamics_json': json.dumps(dynamics_data, ensure_ascii=False),
        'category_json': json.dumps(category_data, ensure_ascii=False),
        'top_outgoing_json': json.dumps(top_outgoing_data, ensure_ascii=False),
    }
    return render(request, 'analytics/dashboard.html', context)


# ===========================================================================
# 2. ПРЕДИКТИВНЫЙ ПРОГНОЗ ИСЧЕРПАНИЯ ЗАПАСОВ
# ===========================================================================

@manager_or_admin_required
def forecast_view(request):
    """
    Интерактивный отчёт предиктивного анализа.
    Рассчитывает ADU (Average Daily Usage), дни до исчерпания, ROP и
    рекомендации по дозаказу.
    """
    days_param = request.GET.get('days', '30')
    try:
        days = int(days_param)
        if days not in [14, 30, 60, 90]:
            days = 30
    except ValueError:
        days = 30

    category_id = request.GET.get('category', '').strip()
    category_id_int = int(category_id) if category_id.isdigit() else None

    lead_time_param = request.GET.get('lead_time', '7')
    try:
        lead_time = int(lead_time_param)
    except ValueError:
        lead_time = 7

    forecasts = get_all_products_forecast(
        days=days,
        lead_time_days=lead_time,
        category_id=category_id_int
    )

    categories = Category.objects.all().order_by('name')

    # Сводка по статусам прогноза
    critical_count = sum(1 for f in forecasts if f['status'] == 'critical')
    warning_count = sum(1 for f in forecasts if f['status'] == 'warning')
    normal_count = sum(1 for f in forecasts if f['status'] == 'normal')
    no_demand_count = sum(1 for f in forecasts if f['status'] == 'no_demand')

    context = {
        'forecasts': forecasts,
        'days': days,
        'lead_time': lead_time,
        'categories': categories,
        'selected_category': category_id_int,
        'critical_count': critical_count,
        'warning_count': warning_count,
        'normal_count': normal_count,
        'no_demand_count': no_demand_count,
        'total_analyzed': len(forecasts),
    }
    return render(request, 'analytics/forecast.html', context)


# ===========================================================================
# 3. JSON API ДЛЯ CHART.JS
# ===========================================================================

@manager_or_admin_required
def api_movement_dynamics(request):
    """JSON API: Динамика отгрузок и поступлений за N дней."""
    try:
        days = int(request.GET.get('days', 30))
    except ValueError:
        days = 30
    data = get_movement_dynamics_data(days=days)
    return JsonResponse(data)


@manager_or_admin_required
def api_category_distribution(request):
    """JSON API: Структура запасов по категориям."""
    data = get_category_distribution_data()
    return JsonResponse(data)


@manager_or_admin_required
def api_top_outgoing(request):
    """JSON API: ТОП самых расходуемых товаров."""
    try:
        limit = int(request.GET.get('limit', 5))
        days = int(request.GET.get('days', 30))
    except ValueError:
        limit, days = 5, 30
    data = get_top_outgoing_products(limit=limit, days=days)
    return JsonResponse(data)


# ===========================================================================
# 4. ЭКСПОРТ В CSV (EXCEL)
# ===========================================================================

@manager_or_admin_required
def export_inventory_csv_view(request):
    """
    Экспорт всех товарных позиций и остатков склада в формате CSV (UTF-8 BOM).
    """
    only_low_stock = request.GET.get('deficit', '0') == '1'
    csv_content = generate_inventory_csv(only_low_stock=only_low_stock)

    date_str = timezone.now().strftime('%Y-%m-%d')
    filename = f"warehouse_deficit_{date_str}.csv" if only_low_stock else f"warehouse_inventory_{date_str}.csv"

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    # Добавляем UTF-8 BOM для безупречного открытия в Excel без искажения кириллицы
    response.write('\ufeff')
    response.write(csv_content)
    return response


# ===========================================================================
# 5. ОТПРАВКА EMAIL-ОПОВЕЩЕНИЙ
# ===========================================================================

@manager_or_admin_required
def send_stock_alert_view(request):
    """
    Ручной или полуавтоматический запуск проверки дефицита и отправки email.
    """
    if request.method == 'POST':
        result = send_low_stock_notification()
        if result['success']:
            if result['count'] > 0:
                messages.success(request, result['message'])
            else:
                messages.info(request, result['message'])
        else:
            messages.error(request, result['message'])

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'analytics:dashboard'
    return redirect(next_url)
