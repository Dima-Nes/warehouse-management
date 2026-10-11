"""
inventory/services.py
Транзакционный сервис для регистрации складских операций.

Вся бизнес-логика пересчёта остатков сосредоточена здесь, а не в view,
чтобы её можно было вызывать из разных точек (web-форма, автоматика заказов и т.д.).

Студент: Нестерук Д.С., группа ПО-2409
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F

from .models import Product, StockMovement


def register_movement(
    *,
    product: Product,
    operation_type: str,
    quantity: int,
    user=None,
    document: str = '',
    note: str = '',
    purchase_order=None,
) -> StockMovement:
    """
    Зарегистрировать складскую операцию и обновить остаток товара.

    Параметры:
        product        — экземпляр Product (должен быть select_for_update внутри транзакции)
        operation_type — одно из StockMovement.OperationType (строковое значение)
        quantity       — положительное целое число
        user           — CustomUser, совершивший операцию (может быть None)
        document       — текстовая ссылка на документ-основание
        note           — произвольное примечание
        purchase_order — PurchaseOrder, если операция создаётся автоматически из заказа

    Возвращает: созданный экземпляр StockMovement.

    Исключения:
        ValidationError — если количество <= 0 или на складе недостаточно товара
                          для операций расхода/списания/перемещения.
    """

    if quantity <= 0:
        raise ValidationError('Количество должно быть больше нуля.')

    op = StockMovement.OperationType

    with transaction.atomic():
        # Блокируем строку товара в БД, чтобы исключить гонку остатков
        locked_product = (
            Product.objects
            .select_for_update()
            .get(pk=product.pk)
        )

        if operation_type in StockMovement.INCREASE_TYPES:
            # Приход: увеличиваем остаток
            Product.objects.filter(pk=locked_product.pk).update(
                quantity=F('quantity') + quantity
            )

        elif operation_type in StockMovement.DECREASE_TYPES:
            # Расход / Списание / Перемещение: проверяем наличие, уменьшаем
            if locked_product.quantity < quantity:
                raise ValidationError(
                    f'Недостаточно товара на складе. '
                    f'Запрошено: {quantity} {locked_product.get_unit_display()}, '
                    f'в наличии: {locked_product.quantity} {locked_product.get_unit_display()}.'
                )
            Product.objects.filter(pk=locked_product.pk).update(
                quantity=F('quantity') - quantity
            )

        else:
            raise ValidationError(f'Неизвестный тип операции: {operation_type}')

        # Фиксируем проводку
        movement = StockMovement.objects.create(
            product=locked_product,
            operation_type=operation_type,
            quantity=quantity,
            created_by=user,
            document=document,
            note=note,
            purchase_order=purchase_order,
        )

    return movement


def post_purchase_order_delivery(purchase_order, user=None) -> list[StockMovement]:
    """
    Автоматически создать приходные проводки по всем позициям заказа
    при смене статуса заказа в «Выполнен / Поступил».

    Вызывается из suppliers/views.py при переходе статуса → delivered.

    Возвращает: список созданных StockMovement.
    """
    movements = []
    for item in purchase_order.items.select_related('product').all():
        movement = register_movement(
            product=item.product,
            operation_type=StockMovement.OperationType.IN,
            quantity=item.quantity,
            user=user,
            document=f'Заказ № {purchase_order.number}',
            note=f'Автоматический приход при закрытии заказа {purchase_order.number}',
            purchase_order=purchase_order,
        )
        movements.append(movement)
    return movements
