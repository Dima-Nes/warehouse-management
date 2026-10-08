"""
inventory/admin.py
Регистрация и настройка моделей inventory в административной панели Django.
Студент: Нестерук Д.С., группа ПО-2409
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройка панели администратора для категорий номенклатуры."""

    list_display = ('name', 'products_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

    def products_count(self, obj):
        """Количество товаров в данной категории."""
        count = obj.products.count()
        return format_html('<b>{}</b> шт.', count)
    products_count.short_description = 'Товаров в категории'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Настройка панели администратора для каталога товаров.
    Включает фильтры, быстрый поиск и цветовую индикацию дефицита.
    """

    list_display = (
        'sku',
        'name',
        'category',
        'unit',
        'price',
        'stock_status_badge',
        'quantity',
        'min_quantity',
        'total_cost_display',
    )
    list_filter = ('category', 'unit')
    search_fields = ('sku', 'name', 'description')
    list_editable = ('price',)
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Основная информация', {
            'fields': ('sku', 'name', 'category', 'description')
        }),
        ('Учётные параметры и цена', {
            'fields': ('unit', 'price', 'quantity', 'min_quantity')
        }),
        ('Системные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def stock_status_badge(self, obj):
        """Индикатор состояния остатка в списке."""
        if obj.is_out_of_stock:
            return format_html('<span style="color:#dc2626; font-weight:bold;">● Нет на складе</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color:#d97706; font-weight:bold;">▲ Дефицит</span>')
        return format_html('<span style="color:#16a34a; font-weight:bold;">✓ В наличии</span>')
    stock_status_badge.short_description = 'Статус'

    def total_cost_display(self, obj):
        """Отображение суммарной стоимости."""
        return f"{obj.total_cost:,.2f} руб."
    total_cost_display.short_description = 'Сумма остатка'
