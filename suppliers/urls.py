"""
suppliers/urls.py
URL-маршруты подсистемы поставщиков и заказов на закупку.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    # -----------------------------------------------------------------------
    # Поставщики
    # -----------------------------------------------------------------------
    # Реестр поставщиков
    path('', views.supplier_list, name='supplier_list'),
    # Карточка поставщика
    path('<int:pk>/', views.supplier_detail, name='supplier_detail'),
    # Создание поставщика
    path('create/', views.supplier_create, name='supplier_create'),
    # Редактирование поставщика
    path('<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    # Удаление поставщика (только POST)
    path('<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # -----------------------------------------------------------------------
    # Заказы на закупку
    # -----------------------------------------------------------------------
    # Реестр заказов
    path('orders/', views.order_list, name='order_list'),
    # Создание заказа
    path('orders/create/', views.order_create, name='order_create'),
    # Детальная страница заказа
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    # Редактирование заказа
    path('orders/<int:pk>/edit/', views.order_update, name='order_update'),
    # Удаление заказа
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),
    # Смена статуса заказа (только POST)
    path('orders/<int:pk>/status/', views.order_change_status, name='order_change_status'),
]
