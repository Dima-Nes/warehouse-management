"""
inventory/views.py
Контроллеры приложения inventory: дашборд, каталог товаров,
складские операции (приход, расход/списание) и журнал движений.

Студент: Нестерук Д.С., группа ПО-2409
"""

import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, F, Sum
from django.core.exceptions import ValidationError

from .models import Product, Category, StockMovement
from .forms import StockInForm, StockOutForm, MovementFilterForm
from .services import register_movement
from accounts.decorators import warehouse_staff_required, manager_or_admin_required


# ===========================================================================
# ДАШБОРД
# ===========================================================================

@login_required
def dashboard(request):
    """
    Главный аналитический дашборд системы.
    Передаёт в шаблон ключевые KPI.
    """
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(quantity__lte=F('min_quantity')).count()
    out_of_stock_count = Product.objects.filter(quantity=0).count()

    try:
        from suppliers.models import Supplier, PurchaseOrder
        total_suppliers = Supplier.objects.count()
        open_orders = PurchaseOrder.objects.filter(
            status__in=['draft', 'sent']
        ).count()
    except Exception:
        total_suppliers = 0
        open_orders = 0

    # Последние 5 операций для блока «Активность»
    recent_movements = StockMovement.objects.select_related(
        'product', 'created_by'
    ).all()[:5]

    context = {
        'total_products':    total_products,
        'low_stock_count':   low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_suppliers':   total_suppliers,
        'open_orders':       open_orders,
        'recent_movements':  recent_movements,
        'today':             datetime.date.today(),
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
