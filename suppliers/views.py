"""
suppliers/views.py
Контроллеры подсистемы поставщиков и заказов на закупку.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction

from accounts.decorators import manager_or_admin_required
from .models import Supplier, PurchaseOrder, OrderItem
from .forms import SupplierForm, PurchaseOrderForm, OrderStatusForm, OrderItemFormSet


# ===========================================================================
# ПОСТАВЩИКИ
# ===========================================================================

@manager_or_admin_required
def supplier_list(request):
    """
    Реестр поставщиков с поиском по наименованию, ИНН и контакту.
    Передаёт аннотированный QuerySet с числом заказов.
    """
    search_query = request.GET.get('q', '').strip()

    suppliers = Supplier.objects.annotate(
        orders_count=Count('purchase_orders')
    ).all()

    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(inn__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    context = {
        'suppliers':    suppliers,
        'search_query': search_query,
        'total_count':  suppliers.count(),
    }
    return render(request, 'suppliers/supplier_list.html', context)


@manager_or_admin_required
def supplier_detail(request, pk):
    """
    Карточка поставщика: реквизиты, связанные товары и список заказов.
    """
    supplier = get_object_or_404(Supplier, pk=pk)
    orders = supplier.purchase_orders.all().order_by('-created_at')[:10]
    products = supplier.products.select_related('category').all()

    context = {
        'supplier': supplier,
        'orders':   orders,
        'products': products,
    }
    return render(request, 'suppliers/supplier_detail.html', context)


@manager_or_admin_required
def supplier_create(request):
    """
    Форма создания нового поставщика.
    GET — отображаем пустую форму.
    POST — валидируем и сохраняем.
    """
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(
                request,
                f'Поставщик «{supplier.name}» успешно добавлен в реестр.'
            )
            return redirect('suppliers:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm()

    context = {
        'form':      form,
        'page_title': 'Новый поставщик',
        'submit_label': 'Создать поставщика',
    }
    return render(request, 'suppliers/supplier_form.html', context)


@manager_or_admin_required
def supplier_update(request, pk):
    """
    Форма редактирования существующего поставщика.
    """
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Данные поставщика «{supplier.name}» успешно обновлены.'
            )
            return redirect('suppliers:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)

    context = {
        'form':         form,
        'supplier':     supplier,
        'page_title':   f'Редактирование: {supplier.name}',
        'submit_label': 'Сохранить изменения',
    }
    return render(request, 'suppliers/supplier_form.html', context)


@manager_or_admin_required
def supplier_delete(request, pk):
    """
    Удаление поставщика (POST-запрос из модального окна).
    Защита: нельзя удалить поставщика с активными заказами.
    """
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        active_orders = supplier.purchase_orders.exclude(
            status__in=[PurchaseOrder.Status.DELIVERED, PurchaseOrder.Status.CANCELLED]
        ).count()

        if active_orders:
            messages.error(
                request,
                f'Невозможно удалить поставщика «{supplier.name}»: '
                f'имеются активные заказы ({active_orders} шт.).'
            )
            return redirect('suppliers:supplier_detail', pk=supplier.pk)

        name = supplier.name
        supplier.delete()
        messages.success(request, f'Поставщик «{name}» удалён из реестра.')
        return redirect('suppliers:supplier_list')

    # GET — перенаправляем обратно (удаление только через POST)
    return redirect('suppliers:supplier_detail', pk=supplier.pk)


# ===========================================================================
# ЗАКАЗЫ НА ЗАКУПКУ
# ===========================================================================

@manager_or_admin_required
def order_list(request):
    """
    Реестр заказов с фильтрацией по статусу и поставщику.
    """
    status_filter   = request.GET.get('status', '').strip()
    supplier_filter = request.GET.get('supplier', '').strip()
    search_query    = request.GET.get('q', '').strip()

    orders = PurchaseOrder.objects.select_related('supplier').prefetch_related('items').all()

    if status_filter:
        orders = orders.filter(status=status_filter)
    if supplier_filter:
        orders = orders.filter(supplier_id=supplier_filter)
    if search_query:
        orders = orders.filter(
            Q(number__icontains=search_query) |
            Q(supplier__name__icontains=search_query)
        )

    suppliers = Supplier.objects.all()

    context = {
        'orders':          orders,
        'suppliers':       suppliers,
        'status_choices':  PurchaseOrder.Status.choices,
        'status_filter':   status_filter,
        'supplier_filter': supplier_filter,
        'search_query':    search_query,
        'total_count':     orders.count(),
    }
    return render(request, 'suppliers/order_list.html', context)


@manager_or_admin_required
def order_create(request):
    """
    Создание нового заказа на закупку с набором позиций (OrderItemFormSet).
    Используем транзакцию для атомарного сохранения.
    """
    if request.method == 'POST':
        form    = PurchaseOrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save()
                formset.instance = order
                formset.save()

            messages.success(
                request,
                f'Заказ на закупку № {order.number} успешно создан.'
            )
            return redirect('suppliers:order_detail', pk=order.pk)
    else:
        form    = PurchaseOrderForm()
        formset = OrderItemFormSet()

    context = {
        'form':       form,
        'formset':    formset,
        'page_title': 'Новый заказ на закупку',
    }
    return render(request, 'suppliers/order_form.html', context)


@manager_or_admin_required
def order_detail(request, pk):
    """
    Детальная страница заказа.
    Позволяет просматривать позиции и менять статус заказа.
    """
    order = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product'),
        pk=pk
    )
    status_form = OrderStatusForm(order)

    context = {
        'order':       order,
        'status_form': status_form,
        'items':       order.items.select_related('product__category').all(),
    }
    return render(request, 'suppliers/order_detail.html', context)


@manager_or_admin_required
def order_change_status(request, pk):
    """
    Обработчик POST-запроса смены статуса заказа.
    Проверяет допустимость перехода и сохраняет новый статус.
    """
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == 'POST':
        status_form = OrderStatusForm(order, request.POST)
        if status_form.is_valid():
            new_status = status_form.cleaned_data['new_status']

            if order.can_transition_to(new_status):
                order.status = new_status
                order.save(update_fields=['status', 'updated_at'])
                messages.success(
                    request,
                    f'Статус заказа № {order.number} изменён на '
                    f'«{PurchaseOrder.Status(new_status).label}».'
                )
            else:
                messages.error(
                    request,
                    f'Переход в статус «{PurchaseOrder.Status(new_status).label}» недопустим.'
                )
        else:
            messages.error(request, 'Некорректный статус.')

    return redirect('suppliers:order_detail', pk=order.pk)


@manager_or_admin_required
def order_update(request, pk):
    """
    Редактирование заказа (только в статусе «Создан»).
    """
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if order.status != PurchaseOrder.Status.DRAFT:
        messages.warning(
            request,
            f'Заказ № {order.number} нельзя редактировать в статусе '
            f'«{order.get_status_display()}».'
        )
        return redirect('suppliers:order_detail', pk=order.pk)

    if request.method == 'POST':
        form    = PurchaseOrderForm(request.POST, instance=order)
        formset = OrderItemFormSet(request.POST, instance=order)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()

            messages.success(
                request,
                f'Заказ № {order.number} успешно обновлён.'
            )
            return redirect('suppliers:order_detail', pk=order.pk)
    else:
        form    = PurchaseOrderForm(instance=order)
        formset = OrderItemFormSet(instance=order)

    context = {
        'form':       form,
        'formset':    formset,
        'order':      order,
        'page_title': f'Редактирование заказа № {order.number}',
    }
    return render(request, 'suppliers/order_form.html', context)


@manager_or_admin_required
def order_delete(request, pk):
    """
    Удаление заказа (только в статусе «Создан» или «Отменён»).
    """
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == 'POST':
        if order.status in [PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.CANCELLED]:
            number = order.number
            order.delete()
            messages.success(request, f'Заказ № {number} удалён.')
            return redirect('suppliers:order_list')
        else:
            messages.error(
                request,
                f'Нельзя удалить заказ в статусе «{order.get_status_display()}».'
            )

    return redirect('suppliers:order_detail', pk=order.pk)
