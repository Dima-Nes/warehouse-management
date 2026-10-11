"""
suppliers/admin.py
Регистрация моделей поставщиков в панели администратора Django.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.contrib import admin
from .models import Supplier, PurchaseOrder, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline-отображение позиций заказа в карточке заказа."""
    model = OrderItem
    extra = 1
    fields = ('product', 'quantity', 'purchase_price')
    autocomplete_fields = []


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display  = ('name', 'inn', 'contact_person', 'phone', 'email', 'created_at')
    search_fields = ('name', 'inn', 'contact_person', 'email')
    list_filter   = ('created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Реквизиты', {'fields': ('name', 'inn', 'address')}),
        ('Контакты',  {'fields': ('contact_person', 'phone', 'email')}),
        ('Прочее',    {'fields': ('notes', 'created_at')}),
    )


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display   = ('number', 'supplier', 'status', 'planned_date', 'created_at')
    list_filter    = ('status', 'supplier', 'created_at')
    search_fields  = ('number', 'supplier__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines        = [OrderItemInline]
    fieldsets = (
        ('Заказ', {'fields': ('number', 'supplier', 'status', 'planned_date')}),
        ('Комментарий', {'fields': ('comment',)}),
        ('Системная информация', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
