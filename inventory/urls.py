"""
inventory/urls.py
URL-маршруты приложения inventory (товары, склад, дашборд).
"""

from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Главный дашборд
    path('', views.dashboard, name='dashboard'),

    # Каталог товаров (Дни 4–5)
    path('products/', views.product_list, name='product_list'),
]
