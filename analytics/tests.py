"""
analytics/tests.py
Тесты для подсистемы аналитики, прогнозирования и формирования отчётов.

Студент: Нестерук Д.С., группа ПО-2409
"""

import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.utils import timezone

from accounts.models import CustomUser
from inventory.models import Category, Product, StockMovement
from suppliers.models import Supplier
from analytics.services import (
    calculate_product_forecast,
    get_all_products_forecast,
    get_movement_dynamics_data,
    get_category_distribution_data,
    get_top_outgoing_products,
    generate_inventory_csv,
    send_low_stock_notification,
)


class AnalyticsServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='manager_user',
            email='manager@test.com',
            password='Password123!',
            role=CustomUser.Role.MANAGER
        )
        self.category = Category.objects.create(name='Электроника')
        self.supplier = Supplier.objects.create(name='ООО ТестПоставка', inn='123456789')

        # Товар 1: с умеренным расходом
        self.product1 = Product.objects.create(
            sku='TEST-001',
            name='Тестовый кабель',
            category=self.category,
            supplier=self.supplier,
            price=Decimal('10.00'),
            quantity=60,
            min_quantity=10,
        )

        # Товар 2: дефицитный
        self.product2 = Product.objects.create(
            sku='TEST-002',
            name='Резистор 10кОм',
            category=self.category,
            supplier=self.supplier,
            price=Decimal('2.50'),
            quantity=5,
            min_quantity=15,
        )

        # Добавим движения расхода для product1 (суммарно 30 единиц за последние дни)
        StockMovement.objects.create(
            product=self.product1,
            operation_type=StockMovement.OperationType.OUT,
            quantity=30,
            created_by=self.user,
            document='Расходная накладная № 1'
        )

    def test_forecast_calculation_with_usage(self):
        """Проверка расчёта ADU и срока исчерпания для товара с расходом."""
        forecast = calculate_product_forecast(self.product1, days=30, lead_time_days=7)
        # 30 единиц расхода за 30 дней -> ADU = 1.0
        self.assertEqual(forecast['adu'], 1.0)
        self.assertEqual(forecast['total_usage'], 30)
        # Остаток 60 / ADU 1.0 = 60.0 дней
        self.assertEqual(forecast['days_until_stockout'], 60.0)
        self.assertIsNotNone(forecast['stockout_date'])
        self.assertEqual(forecast['status'], 'normal')
        # ROP = ADU * 7 + min_qty (10) = 17
        self.assertEqual(forecast['reorder_point'], 17)

    def test_forecast_calculation_low_stock(self):
        """Проверка статуса для дефицитного товара без расхода."""
        forecast = calculate_product_forecast(self.product2, days=30, lead_time_days=7)
        self.assertEqual(forecast['adu'], 0.0)
        self.assertEqual(forecast['current_quantity'], 5)
        # Остаток (5) <= min_qty (15) -> warning
        self.assertEqual(forecast['status'], 'warning')

    def test_movement_dynamics_data(self):
        """Проверка структуры данных динамики движений."""
        data = get_movement_dynamics_data(days=30)
        self.assertIn('labels', data)
        self.assertIn('datasets', data)
        self.assertEqual(len(data['labels']), 30)
        self.assertEqual(len(data['datasets']), 2)

    def test_category_distribution_data(self):
        """Проверка данных круговой диаграммы категорий."""
        data = get_category_distribution_data()
        self.assertIn('labels', data)
        self.assertIn('quantities', data)
        self.assertIn('Электроника', data['labels'])

    def test_top_outgoing_products(self):
        """Проверка ТОП расходуемых товаров."""
        data = get_top_outgoing_products(limit=5, days=30)
        self.assertTrue(len(data['labels']) > 0)
        self.assertIn('Тестовый кабель (TEST-001)', data['labels'][0])
        self.assertEqual(data['data'][0], 30)

    def test_generate_inventory_csv(self):
        """Проверка генерации CSV файла остатков."""
        csv_text = generate_inventory_csv(only_low_stock=False)
        self.assertIn('Артикул (SKU);Наименование товара', csv_text)
        self.assertIn('TEST-001', csv_text)
        self.assertIn('TEST-002', csv_text)

        # Фильтр дефицита
        deficit_csv = generate_inventory_csv(only_low_stock=True)
        self.assertIn('TEST-002', deficit_csv)
        self.assertNotIn('TEST-001', deficit_csv)

    def test_send_low_stock_notification(self):
        """Проверка отправки почтового оповещения о дефиците."""
        mail.outbox.clear()
        res = send_low_stock_notification(recipient_email='alerts@test.com')
        self.assertTrue(res['success'])
        self.assertEqual(res['count'], 1)  # Только product2 дефицитный
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('TEST-002', mail.outbox[0].body)
        self.assertIn('alerts@test.com', mail.outbox[0].to)


class AnalyticsViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = CustomUser.objects.create_user(
            username='mgr',
            email='mgr@test.com',
            password='Password123!',
            role=CustomUser.Role.MANAGER
        )
        self.category = Category.objects.create(name='Инструменты')
        self.product = Product.objects.create(
            sku='TOOL-01',
            name='Отвертка PH2',
            category=self.category,
            price=Decimal('15.00'),
            quantity=20,
            min_quantity=5,
        )

    def test_access_denied_for_anonymous(self):
        """Анонимный доступ перенаправляется на страницу логина."""
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_view_for_manager(self):
        """Менеджер успешно открывает дашборд аналитики."""
        self.client.login(username='mgr', password='Password123!')
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Аналитика и статистика склада')
        self.assertContains(response, 'dynamicsChart')

    def test_forecast_view(self):
        """Страница предиктивного прогноза загружается корректно."""
        self.client.login(username='mgr', password='Password123!')
        response = self.client.get(reverse('analytics:forecast'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Прогноз исчерпания запасов')
        self.assertContains(response, 'TOOL-01')

    def test_api_endpoints(self):
        """JSON API отдают валидный JSON 200 OK."""
        self.client.login(username='mgr', password='Password123!')

        resp1 = self.client.get(reverse('analytics:api_dynamics'))
        self.assertEqual(resp1.status_code, 200)
        self.assertIn('datasets', resp1.json())

        resp2 = self.client.get(reverse('analytics:api_categories'))
        self.assertEqual(resp2.status_code, 200)
        self.assertIn('quantities', resp2.json())

        resp3 = self.client.get(reverse('analytics:api_top_outgoing'))
        self.assertEqual(resp3.status_code, 200)
        self.assertIn('labels', resp3.json())

    def test_export_csv_view(self):
        """Экспорт CSV возвращает файл с UTF-8 BOM."""
        self.client.login(username='mgr', password='Password123!')
        response = self.client.get(reverse('analytics:export_inventory'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))  # UTF-8 BOM
        self.assertIn('TOOL-01'.encode('utf-8'), response.content)
