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
