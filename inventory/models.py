"""
inventory/models.py
Модели номенклатуры склада: категории и товары.
Студент: Нестерук Д.С., группа ПО-2409
"""

from decimal import Decimal
from django.db import models


class Category(models.Model):
    """
    Категория товаров (номенклатурная группа).
    Примеры: «Электроника», «Крепеж», «Инструменты», «Упаковка».
    """

    name = models.CharField(
        max_length=120,
        unique=True,
        verbose_name='Название категории',
        help_text='Уникальное название товарной группы'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
        help_text='Краткая характеристика номенклатурной группы'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Карточка товара (номенклатурная единица склада).
    Содержит артикул (SKU), базовую цену, текущий и минимальный остаток,
    а также единицу измерения.
    """

    class Unit(models.TextChoices):
        PCS   = 'pcs', 'шт.'
        KG    = 'kg',  'кг'
        LITER = 'l',   'л'
        METER = 'm',   'м'
        BOX   = 'box', 'упак.'

    sku = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name='Артикул (SKU)',
        help_text='Уникальный идентификатор позиции на складе'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Наименование товара'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория'
    )
    unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.PCS,
        verbose_name='Единица измерения'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Базовая цена (руб.)',
        help_text='Учётная стоимость за одну единицу'
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Текущий остаток',
        help_text='Фактическое количество товара на складе'
    )
    min_quantity = models.PositiveIntegerField(
        default=5,
        verbose_name='Минимальный остаток',
        help_text='Порог для формирования сигнала о дефиците'
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Основной поставщик',
        help_text='Поставщик, у которого закупается данный товар'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание товара'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self) -> bool:
        """Признак дефицита: текущий остаток меньше или равен минимальному."""
        return self.quantity <= self.min_quantity

    @property
    def is_out_of_stock(self) -> bool:
        """Признак полного отсутствия товара на складе."""
        return self.quantity == 0

    @property
    def total_cost(self) -> Decimal:
        """Суммарная балансовая стоимость текущего остатка."""
        return Decimal(self.price) * Decimal(self.quantity)


class StockMovement(models.Model):
    """
    Складская проводка — запись о движении товара.

    Каждая операция (приход, расход, перемещение, списание) фиксируется
    отдельной строкой журнала. Фактический остаток Product.quantity
    пересчитывается сервисом register_movement() атомарно.
    """

    class OperationType(models.TextChoices):
        IN       = 'in',       'Приход'
        OUT      = 'out',      'Расход'
        TRANSFER = 'transfer', 'Внутреннее перемещение'
        WRITEOFF = 'writeoff', 'Списание'

    # Типы операций, которые увеличивают остаток
    INCREASE_TYPES = {OperationType.IN}
    # Типы операций, которые уменьшают остаток
    DECREASE_TYPES = {OperationType.OUT, OperationType.WRITEOFF, OperationType.TRANSFER}

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name='Товар'
    )
    operation_type = models.CharField(
        max_length=10,
        choices=OperationType.choices,
        verbose_name='Тип операции'
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
        help_text='Количество единиц товара по данной операции'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата и время операции'
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Автор операции'
    )
    document = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Основание / документ',
        help_text='Ссылка на документ-основание (номер накладной, акта и т.д.)'
    )
    note = models.TextField(
        blank=True,
        verbose_name='Примечание'
    )
    # Связь с заказом на закупку (опционально — для автоматических приходных проводок)
    purchase_order = models.ForeignKey(
        'suppliers.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Заказ на закупку'
    )

    class Meta:
        verbose_name = 'Складская операция'
        verbose_name_plural = 'Складские операции'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['operation_type', '-created_at']),
        ]

    def __str__(self):
        return (
            f'{self.get_operation_type_display()} — '
            f'{self.product.name} × {self.quantity} '
            f'({self.created_at.strftime("%d.%m.%Y %H:%M") if self.created_at else "—"})'
        )

    @property
    def is_incoming(self) -> bool:
        """Проводка увеличивает остаток."""
        return self.operation_type in self.INCREASE_TYPES

    @property
    def operation_badge_class(self) -> str:
        """Bootstrap-класс бейджа в зависимости от типа операции."""
        mapping = {
            self.OperationType.IN:       'bg-success',
            self.OperationType.OUT:      'bg-primary',
            self.OperationType.TRANSFER: 'bg-info text-dark',
            self.OperationType.WRITEOFF: 'bg-danger',
        }
        return mapping.get(self.operation_type, 'bg-secondary')

