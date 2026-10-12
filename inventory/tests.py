"""
inventory/tests.py
Сквозной аудит ролей и тестирование подсистемы складского учета:
- Доступ пользователей по ролям (admin, manager, warehouse_staff)
- Сводный дашборд с 5 KPI и графиками
- Транзакционная регистрация складских проводок и валидация остатков

Студент: Нестерук Д.С., группа ПО-2409
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError

from accounts.models import CustomUser
from inventory.models import Category, Product, StockMovement
from inventory.services import register_movement
from suppliers.models import Supplier, PurchaseOrder, OrderItem


class RoleAccessAuditTests(TestCase):
    """Сквозная проверка матрицы доступа под разными ролями."""

    def setUp(self):
        self.client = Client()

        self.admin = CustomUser.objects.create_user(
            username='admin_test',
            email='admin@test.local',
            password='Password123!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.manager = CustomUser.objects.create_user(
            username='manager_test',
            email='manager@test.local',
            password='Password123!',
            role=CustomUser.Role.MANAGER
        )
        self.staff = CustomUser.objects.create_user(
            username='staff_test',
            email='staff@test.local',
            password='Password123!',
            role=CustomUser.Role.WAREHOUSE_STAFF
        )

        self.category = Category.objects.create(name='ТестКатегория')
        self.supplier = Supplier.objects.create(name='ТестПоставщик')
        self.product = Product.objects.create(
            sku='AUDIT-01',
            name='Тестовый датчик',
            category=self.category,
            supplier=self.supplier,
            price=Decimal('50.00'),
            quantity=10,
            min_quantity=5,
        )

    def test_admin_has_full_access(self):
        """Администратор имеет доступ ко всем разделам системы."""
        self.client.login(username='admin_test', password='Password123!')

        urls = [
            reverse('inventory:dashboard'),
            reverse('inventory:product_list'),
            reverse('inventory:product_detail', args=[self.product.pk]),
            reverse('inventory:product_create'),
            reverse('inventory:stock_in'),
            reverse('inventory:stock_out'),
            reverse('inventory:movement_history'),
            reverse('suppliers:supplier_list'),
            reverse('suppliers:order_list'),
            reverse('analytics:dashboard'),
            reverse('analytics:forecast'),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Администратор не смог открыть {url}")

    def test_manager_has_management_access(self):
        """Менеджер имеет доступ ко всем оперативным и аналитическим разделам."""
        self.client.login(username='manager_test', password='Password123!')

        urls = [
            reverse('inventory:dashboard'),
            reverse('inventory:product_list'),
            reverse('inventory:product_create'),
            reverse('inventory:stock_in'),
            reverse('inventory:stock_out'),
            reverse('suppliers:supplier_list'),
            reverse('suppliers:order_list'),
            reverse('analytics:dashboard'),
            reverse('analytics:forecast'),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Менеджер не смог открыть {url}")

    def test_warehouse_staff_restricted_access(self):
        """Сотрудник склада имеет доступ к складу и движениям, но ограничен в закупках и аналитике."""
        self.client.login(username='staff_test', password='Password123!')

        # Разрешенные страницы
        allowed_urls = [
            reverse('inventory:dashboard'),
            reverse('inventory:product_list'),
            reverse('inventory:product_detail', args=[self.product.pk]),
            reverse('inventory:stock_in'),
            reverse('inventory:stock_out'),
            reverse('inventory:movement_history'),
        ]
        for url in allowed_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Кладовщик должен иметь доступ к {url}")

        # Запрещенные разделы (перенаправление на access_denied)
        forbidden_urls = [
            reverse('suppliers:supplier_list'),
            reverse('suppliers:order_list'),
            reverse('analytics:dashboard'),
            reverse('inventory:product_create'),
        ]
        for url in forbidden_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f"Кладовщик не должен иметь доступ к {url}")


class InventoryDashboardAndServiceTests(TestCase):
    """Проверка расчёта KPI дашборда и транзакционного сервиса проводок."""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='boss',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.client.login(username='boss', password='Password123!')

        self.category = Category.objects.create(name='Комплектующие')
        self.supplier = Supplier.objects.create(name='Поставщик №1')
        self.product = Product.objects.create(
            sku='DASH-01',
            name='Дисплей 1602',
            category=self.category,
            supplier=self.supplier,
            price=Decimal('20.00'),
            quantity=15,
            min_quantity=5,
        )

    def test_dashboard_renders_with_kpi_and_charts(self):
        """Главный дашборд отображает 5 KPI, 2 графика и срочные позиции."""
        resp = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Панель управления складом')
        self.assertContains(resp, 'dynamicsChart')
        self.assertContains(resp, 'categoryChart')
        self.assertEqual(resp.context['total_products'], 1)
        self.assertEqual(resp.context['total_warehouse_value'], Decimal('300.00'))

    def test_register_movement_transaction(self):
        """Регистрация расхода корректно уменьшает остаток товара."""
        m = register_movement(
            product=self.product,
            operation_type=StockMovement.OperationType.OUT,
            quantity=5,
            user=self.user,
            document='Расходная накладная 1'
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)
        self.assertEqual(m.quantity, 5)

    def test_register_movement_insufficient_stock_fails(self):
        """Попытка списать больше, чем есть на складе, вызывает ValidationError."""
        with self.assertRaises(ValidationError):
            register_movement(
                product=self.product,
                operation_type=StockMovement.OperationType.OUT,
                quantity=100,  # Запрошено больше 15
                user=self.user
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 15)  # Остаток не изменился
