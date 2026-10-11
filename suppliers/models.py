"""
suppliers/models.py
Модели подсистемы поставщиков и заказов на закупку.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.db import models
from django.core.validators import RegexValidator


class Supplier(models.Model):
    """
    Контрагент-поставщик товаров.
    Хранит реквизиты, контактные данные и примечания.
    """

    phone_validator = RegexValidator(
        regex=r'^\+?[\d\s\-\(\)]{7,20}$',
        message='Введите корректный номер телефона (7–20 символов, цифры/+/-/пробелы/скобки).'
    )

    name = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        verbose_name='Наименование организации',
        help_text='Полное официальное наименование поставщика'
    )
    inn = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='УНП / ИНН',
        help_text='Учётный номер плательщика или ИНН'
    )
    contact_person = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Контактное лицо',
        help_text='ФИО ответственного менеджера поставщика'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator],
        verbose_name='Телефон'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    address = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Юридический адрес'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Примечания',
        help_text='Условия работы, сроки доставки и другие заметки'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def active_orders_count(self):
        """Количество активных (не завершённых/отменённых) заказов."""
        return self.purchase_orders.exclude(
            status__in=[PurchaseOrder.Status.DELIVERED, PurchaseOrder.Status.CANCELLED]
        ).count()


class PurchaseOrder(models.Model):
    """
    Заказ на закупку товаров у поставщика.
    Проходит жизненный цикл: Создан → Отправлен → Выполнен / Отменён.
    """

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Создан'
        SENT      = 'sent',      'Отправлен поставщику'
        DELIVERED = 'delivered', 'Выполнен / Поступил'
        CANCELLED = 'cancelled', 'Отменён'

    # Допустимые переходы статусов: ключ → список доступных следующих статусов
    STATUS_TRANSITIONS = {
        Status.DRAFT:     [Status.SENT, Status.CANCELLED],
        Status.SENT:      [Status.DELIVERED, Status.CANCELLED],
        Status.DELIVERED: [],
        Status.CANCELLED: [],
    }

    number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name='Номер документа',
        help_text='Уникальный номер заказа на закупку, например: ЗК-2026-001'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name='Поставщик'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    planned_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Плановая дата поставки'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Заказ на закупку'
        verbose_name_plural = 'Заказы на закупку'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.supplier.name}'

    @property
    def total_amount(self):
        """Итоговая сумма заказа: сумма по всем позициям."""
        from decimal import Decimal
        result = sum(
            item.quantity * item.purchase_price
            for item in self.items.all()
        )
        return result if result else Decimal('0.00')

    def get_allowed_transitions(self):
        """Возвращает список доступных следующих статусов для текущего заказа."""
        return self.STATUS_TRANSITIONS.get(self.status, [])

    def can_transition_to(self, new_status):
        """Проверяет, допустим ли переход в указанный статус."""
        return new_status in self.get_allowed_transitions()

    @property
    def status_badge_class(self):
        """Bootstrap-класс бейджа в зависимости от статуса."""
        mapping = {
            self.Status.DRAFT:     'bg-secondary',
            self.Status.SENT:      'bg-primary',
            self.Status.DELIVERED: 'bg-success',
            self.Status.CANCELLED: 'bg-danger',
        }
        return mapping.get(self.status, 'bg-secondary')


class OrderItem(models.Model):
    """
    Позиция (строка) заказа на закупку.
    Содержит ссылку на товар, заказываемое количество и цену закупки.
    """

    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
        help_text='Заказываемое количество единиц товара'
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена закупки (руб.)',
        help_text='Цена за единицу товара по данному заказу'
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        unique_together = [('order', 'product')]

    def __str__(self):
        return f'{self.product.name} × {self.quantity} шт.'

    @property
    def line_total(self):
        """Стоимость позиции: количество × цена закупки."""
        return self.quantity * self.purchase_price
