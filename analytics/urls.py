"""
analytics/urls.py
URL-маршруты подсистемы аналитики и прогнозирования.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # -----------------------------------------------------------------------
    # Сводный дашборд аналитики
    # -----------------------------------------------------------------------
    path('', views.analytics_dashboard, name='dashboard'),

    # -----------------------------------------------------------------------
    # Предиктивный прогноз исчерпания запасов
    # -----------------------------------------------------------------------
    path('forecast/', views.forecast_view, name='forecast'),

    # -----------------------------------------------------------------------
    # JSON API для Chart.js
    # -----------------------------------------------------------------------
    path('api/dynamics/', views.api_movement_dynamics, name='api_dynamics'),
    path('api/categories/', views.api_category_distribution, name='api_categories'),
    path('api/top-outgoing/', views.api_top_outgoing, name='api_top_outgoing'),

    # -----------------------------------------------------------------------
    # Экспорт отчётов в CSV
    # -----------------------------------------------------------------------
    path('export/inventory/', views.export_inventory_csv_view, name='export_inventory'),

    # -----------------------------------------------------------------------
    # Отправка email-оповещений о дефиците
    # -----------------------------------------------------------------------
    path('alerts/send/', views.send_stock_alert_view, name='send_stock_alert'),
]
