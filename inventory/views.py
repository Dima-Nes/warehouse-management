"""
inventory/views.py
Контроллеры приложения inventory: дашборд, каталог товаров.
Студент: Нестерук Д.С., группа ПО-2409
"""

import datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F

from .models import Product, Category


@login_required
def dashboard(request):
    """
    Главный аналитический дашборд системы.
    Передаёт в шаблон ключевые показатели:
    — общее число товарных позиций в каталоге
    — количество позиций с остатком ниже минимума (дефицит)
    — количество поставщиков в реестре
    — количество открытых заказов
    """
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(quantity__lte=F('min_quantity')).count()

    try:
        from suppliers.models import Supplier
        total_suppliers = Supplier.objects.count()
    except Exception:
        total_suppliers = 0

    open_orders = 0  # Будет реализовано в подсистеме заказов

    context = {
        'total_products':  total_products,
        'low_stock_count': low_stock_count,
        'total_suppliers': total_suppliers,
        'open_orders':     open_orders,
        'today':           datetime.date.today(),
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def product_list(request):
    """
    Список всех товаров в каталоге.
    Поддерживает поиск по названию/артикулу и фильтрацию по категории.
    """
    search_query = request.GET.get('q', '').strip()
    category_id  = request.GET.get('category', '').strip()

    products = Product.objects.select_related('category').all()

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
