"""
inventory/views.py
Контроллеры приложения inventory:
  — Дашборд
  — Каталог товаров (список)
  — CRUD товаров и категорий  (Итерация 3)
  — Складские операции: приход, расход/списание, журнал движений

Студент: Нестерук Д.С., группа ПО-2409
"""

import json
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, F, Sum
from django.core.exceptions import ValidationError

from .models import Product, Category, StockMovement
from .forms import CategoryForm, ProductForm, StockInForm, StockOutForm, MovementFilterForm
from .services import register_movement
from accounts.decorators import warehouse_staff_required, manager_or_admin_required
from analytics.services import (
    get_movement_dynamics_data,
    get_category_distribution_data,
    calculate_product_forecast,
)


# ===========================================================================
# ДАШБОРД (Итерация 5: Сводная аналитика и оперативный контроль)
# ===========================================================================

@login_required
def dashboard(request):
    """
    Главный сводный дашборд системы управления складом.
    Передаёт в шаблон 5 ключевых KPI, 2 интерактивных графика Chart.js,
    таблицу товаров, требующих срочного заказа, и последние складские проводки.
    """
    all_products = Product.objects.select_related('category', 'supplier').all()
    total_products = all_products.count()
    low_stock_count = all_products.filter(quantity__lte=F('min_quantity')).count()
    out_of_stock_count = all_products.filter(quantity=0).count()
    total_warehouse_value = sum(p.total_cost for p in all_products)

    try:
        from suppliers.models import Supplier, PurchaseOrder
        total_suppliers = Supplier.objects.count()
        active_orders_count = PurchaseOrder.objects.filter(
            status__in=[PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.SENT]
        ).count()
    except Exception:
        total_suppliers = 0
        active_orders_count = 0

    # Данные для двух графиков Chart.js
    dynamics_data = get_movement_dynamics_data(days=30)
    category_data = get_category_distribution_data()

    # Таблица «Товары, требующие срочного заказа»
    urgent_items = []
    for p in all_products:
        forecast = calculate_product_forecast(p, days=30)
        if forecast['status'] in ['critical', 'warning']:
            urgent_items.append(forecast)

    def sort_urgency(item):
        days = item['days_until_stockout'] if item['days_until_stockout'] is not None else 9999
        return (days, item['current_quantity'])

    urgent_items.sort(key=sort_urgency)
    urgent_items = urgent_items[:7]

    # Последние 5 складских проводок
    recent_movements = StockMovement.objects.select_related(
        'product', 'created_by'
    ).all()[:5]

    context = {
        'total_products':        total_products,
        'total_warehouse_value': total_warehouse_value,
        'low_stock_count':       low_stock_count,
        'out_of_stock_count':     out_of_stock_count,
        'total_suppliers':       total_suppliers,
        'active_orders_count':   active_orders_count,
        'urgent_items':          urgent_items,
        'recent_movements':      recent_movements,
        'dynamics_json':         json.dumps(dynamics_data, ensure_ascii=False),
        'category_json':         json.dumps(category_data, ensure_ascii=False),
        'today':                 datetime.date.today(),
    }
    return render(request, 'inventory/dashboard.html', context)



# ===========================================================================
# КАТАЛОГ ТОВАРОВ
# ===========================================================================

@login_required
def product_list(request):
    """
    Список всех товаров в каталоге.
    Поддерживает поиск по названию/артикулу и фильтрацию по категории.
    """
    search_query = request.GET.get('q', '').strip()
    category_id  = request.GET.get('category', '').strip()

    products = Product.objects.select_related('category', 'supplier').all()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(sku__icontains=search_query)
        )
    if category_id:
        products = products.filter(category_id=category_id)

    categories = Category.objects.annotate(products_count=Count('products'))

    context = {
        'products':     products,
        'categories':   categories,
        'search_query': search_query,
        'category_id':  category_id,
        'total_count':  products.count(),
    }
    return render(request, 'inventory/product_list.html', context)


# ===========================================================================
# СКЛАДСКИЕ ОПЕРАЦИИ
# ===========================================================================

@warehouse_staff_required
def stock_in_view(request):
    """
    Оприходование товара (Приход).
    Доступно: admin, manager, warehouse_staff.
    """
    if request.method == 'POST':
        form = StockInForm(request.POST)
        if form.is_valid():
            try:
                movement = register_movement(
                    product=form.cleaned_data['product'],
                    operation_type=StockMovement.OperationType.IN,
                    quantity=form.cleaned_data['quantity'],
                    user=request.user,
                    document=form.cleaned_data.get('document', ''),
                    note=form.cleaned_data.get('note', ''),
                )
                messages.success(
                    request,
                    f'Приход: {movement.product.name} — '
                    f'+{movement.quantity} {movement.product.get_unit_display()}. '
                    f'Новый остаток: {movement.product.__class__.objects.get(pk=movement.product.pk).quantity}.'
                )
                return redirect('inventory:stock_in')
            except ValidationError as exc:
                messages.error(request, exc.message)
    else:
        # Предзаполняем товар, если передан GET-параметр
        initial = {}
        product_pk = request.GET.get('product')
        if product_pk:
            initial['product'] = product_pk
        form = StockInForm(initial=initial)

    context = {
        'form':       form,
        'page_title': 'Приход товара',
        'op_type':    'in',
    }
    return render(request, 'inventory/stock_in.html', context)


@warehouse_staff_required
def stock_out_view(request):
    """
    Расход / Списание / Перемещение товара.
    Доступно: admin, manager, warehouse_staff.
    """
    if request.method == 'POST':
        form = StockOutForm(request.POST)
        if form.is_valid():
            try:
                movement = register_movement(
                    product=form.cleaned_data['product'],
                    operation_type=form.cleaned_data['operation_type'],
                    quantity=form.cleaned_data['quantity'],
                    user=request.user,
                    document=form.cleaned_data.get('document', ''),
                    note=form.cleaned_data.get('note', ''),
                )
                op_label = StockMovement.OperationType(movement.operation_type).label
                new_qty = movement.product.__class__.objects.get(pk=movement.product.pk).quantity
                messages.success(
                    request,
                    f'{op_label}: {movement.product.name} — '
                    f'−{movement.quantity} {movement.product.get_unit_display()}. '
                    f'Новый остаток: {new_qty}.'
                )
                return redirect('inventory:stock_out')
            except ValidationError as exc:
                messages.error(request, exc.message)
    else:
        initial = {}
        product_pk = request.GET.get('product')
        if product_pk:
            initial['product'] = product_pk
        form = StockOutForm(initial=initial)

    context = {
        'form':       form,
        'page_title': 'Расход / Списание товара',
        'op_type':    'out',
    }
    return render(request, 'inventory/stock_out.html', context)


# ===========================================================================
# ЖУРНАЛ СКЛАДСКИХ ОПЕРАЦИЙ
# ===========================================================================

@login_required
def movement_history_view(request):
    """
    Журнал всех складских проводок с фильтрацией по товару, типу и датам.
    """
    filter_form = MovementFilterForm(request.GET or None)

    movements = StockMovement.objects.select_related(
        'product__category', 'created_by', 'purchase_order'
    ).all()

    if filter_form.is_valid():
        if filter_form.cleaned_data.get('product'):
            movements = movements.filter(product=filter_form.cleaned_data['product'])

        if filter_form.cleaned_data.get('operation_type'):
            movements = movements.filter(
                operation_type=filter_form.cleaned_data['operation_type']
            )

        if filter_form.cleaned_data.get('date_from'):
            movements = movements.filter(
                created_at__date__gte=filter_form.cleaned_data['date_from']
            )

        if filter_form.cleaned_data.get('date_to'):
            movements = movements.filter(
                created_at__date__lte=filter_form.cleaned_data['date_to']
            )

    total_count = movements.count()

    # Агрегат: итоговые суммы по типам для информационной панели
    stats = {}
    for op in StockMovement.OperationType:
        stats[op.value] = movements.filter(operation_type=op.value).aggregate(
            total=Sum('quantity')
        )['total'] or 0

    context = {
        'movements':   movements[:200],   # Последние 200 записей
        'filter_form': filter_form,
        'total_count': total_count,
        'stats':       stats,
        'op_types':    StockMovement.OperationType,
    }
    return render(request, 'inventory/movement_history.html', context)


# ===========================================================================
# CRUD ТОВАРОВ (Итерация 3)
# ===========================================================================

@login_required
def product_detail(request, pk):
    """
    Детальная карточка товара.
    Показывает технические характеристики, текущий остаток, статус дефицита
    и историю последних складских операций по данному товару.
    """
    product = get_object_or_404(
        Product.objects.select_related('category', 'supplier'),
        pk=pk
    )

    # Последние 15 проводок по товару
    recent_movements = (
        StockMovement.objects
        .filter(product=product)
        .select_related('created_by', 'purchase_order')
        .order_by('-created_at')[:15]
    )

    context = {
        'product':          product,
        'recent_movements': recent_movements,
    }
    return render(request, 'inventory/product_detail.html', context)


@manager_or_admin_required
def product_create(request):
    """
    Создание новой карточки товара.
    Доступно: admin, manager.
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(
                request,
                f'Товар «{product.name}» (SKU: {product.sku}) успешно добавлен в каталог.'
            )
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm()

    context = {
        'form':         form,
        'page_title':   'Новый товар',
        'submit_label': 'Добавить товар',
    }
    return render(request, 'inventory/product_form.html', context)


@manager_or_admin_required
def product_update(request, pk):
    """
    Редактирование карточки товара.
    Доступно: admin, manager.
    """
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Данные товара «{product.name}» успешно обновлены.'
            )
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)

    context = {
        'form':         form,
        'product':      product,
        'page_title':   f'Редактирование: {product.name}',
        'submit_label': 'Сохранить изменения',
    }
    return render(request, 'inventory/product_form.html', context)


@manager_or_admin_required
def product_delete(request, pk):
    """
    Удаление товара (POST из модального окна).
    Защита: нельзя удалить товар с историей движений.
    """
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        movements_count = product.movements.count()
        if movements_count:
            messages.error(
                request,
                f'Нельзя удалить «{product.name}»: существует {movements_count} складских операций. '
                f'Сначала перенесите или аннулируйте операции.'
            )
            return redirect('inventory:product_detail', pk=product.pk)

        name = product.name
        product.delete()
        messages.success(request, f'Товар «{name}» удалён из каталога.')
        return redirect('inventory:product_list')

    return redirect('inventory:product_detail', pk=product.pk)


# ===========================================================================
# CRUD КАТЕГОРИЙ (Итерация 3)
# ===========================================================================

@manager_or_admin_required
def category_list(request):
    """
    Список категорий с числом товаров в каждой.
    """
    categories = Category.objects.annotate(
        products_count=Count('products')
    ).order_by('name')

    context = {
        'categories': categories,
    }
    return render(request, 'inventory/category_list.html', context)


@manager_or_admin_required
def category_create(request):
    """Создание новой категории."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Категория «{category.name}» создана.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()

    context = {
        'form':         form,
        'page_title':   'Новая категория',
        'submit_label': 'Создать категорию',
    }
    return render(request, 'inventory/category_form.html', context)


@manager_or_admin_required
def category_update(request, pk):
    """Редактирование существующей категории."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Категория «{category.name}» обновлена.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)

    context = {
        'form':         form,
        'category':     category,
        'page_title':   f'Редактирование: {category.name}',
        'submit_label': 'Сохранить изменения',
    }
    return render(request, 'inventory/category_form.html', context)


@manager_or_admin_required
def category_delete(request, pk):
    """
    Удаление категории (POST).
    Защита: PROTECT на уровне БД не позволит удалить категорию с товарами.
    """
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        if category.products.exists():
            messages.error(
                request,
                f'Нельзя удалить категорию «{category.name}»: '
                f'в ней {category.products.count()} товаров.'
            )
            return redirect('inventory:category_list')

        name = category.name
        category.delete()
        messages.success(request, f'Категория «{name}» удалена.')
        return redirect('inventory:category_list')

    return redirect('inventory:category_list')
