"""
inventory/urls.py
URL-маршруты приложения inventory: дашборд, каталог товаров,
CRUD номенклатуры, складские операции и журнал движений.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # -----------------------------------------------------------------------
    # Главный дашборд
    # -----------------------------------------------------------------------
    path('', views.dashboard, name='dashboard'),

    # -----------------------------------------------------------------------
    # Каталог товаров
    # -----------------------------------------------------------------------
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # -----------------------------------------------------------------------
    # Категории
    # -----------------------------------------------------------------------
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # -----------------------------------------------------------------------
    # Складские операции
    # -----------------------------------------------------------------------
    path('stock/in/', views.stock_in_view, name='stock_in'),
    path('stock/out/', views.stock_out_view, name='stock_out'),
    path('stock/history/', views.movement_history_view, name='movement_history'),
]
