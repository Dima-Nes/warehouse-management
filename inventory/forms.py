"""
inventory/forms.py
Формы для складских операций: приход, расход/списание.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Product, StockMovement


class BootstrapMixin:
    """Добавляет Bootstrap 5 классы всем полям формы."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if isinstance(widget, forms.Select):
                widget.attrs['class'] = f'{existing} form-select'.strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = f'{existing} form-control'.strip()
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs['class'] = f'{existing} form-control'.strip()


class StockInForm(BootstrapMixin, forms.Form):
    """
    Форма оприходования товара (Приход).
    Используется для ручного прихода через web-форму.
    """

    product = forms.ModelChoiceField(
        queryset=Product.objects.select_related('category').order_by('name'),
        label='Товар',
        empty_label='— Выберите товар —',
    )
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1}),
    )
    document = forms.CharField(
        label='Документ-основание',
        max_length=200,
        required=False,
        help_text='Номер накладной, акта и т.д.',
        widget=forms.TextInput(attrs={'placeholder': 'Например: Накладная № 15'}),
    )
    note = forms.CharField(
        label='Примечание',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty <= 0:
            raise ValidationError('Количество должно быть больше нуля.')
        return qty


class StockOutForm(BootstrapMixin, forms.Form):
    """
    Форма расхода / списания товара.
    Тип операции выбирается из ограниченного набора (Расход, Списание, Перемещение).
    """

    ALLOWED_TYPES = [
        StockMovement.OperationType.OUT,
        StockMovement.OperationType.WRITEOFF,
        StockMovement.OperationType.TRANSFER,
    ]

    product = forms.ModelChoiceField(
        queryset=Product.objects.select_related('category').order_by('name'),
        label='Товар',
        empty_label='— Выберите товар —',
    )
    operation_type = forms.ChoiceField(
        label='Тип операции',
        choices=[
            (t, StockMovement.OperationType(t).label)
            for t in ALLOWED_TYPES
        ],
    )
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1}),
    )
    document = forms.CharField(
        label='Документ-основание',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Например: Акт списания № 3'}),
    )
    note = forms.CharField(
        label='Примечание',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def clean(self):
        cleaned_data = super().clean()
        product  = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')

        if product and quantity:
            if product.quantity < quantity:
                raise ValidationError(
                    f'Недостаточно товара: в наличии {product.quantity} '
                    f'{product.get_unit_display()}, запрошено {quantity}.'
                )
        return cleaned_data


class MovementFilterForm(forms.Form):
    """
    Форма фильтрации журнала складских операций.
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.order_by('name'),
        required=False,
        empty_label='— Все товары —',
        label='Товар',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    operation_type = forms.ChoiceField(
        required=False,
        choices=[('', '— Все типы —')] + StockMovement.OperationType.choices,
        label='Тип операции',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    date_from = forms.DateField(
        required=False,
        label='С даты',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    date_to = forms.DateField(
        required=False,
        label='По дату',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
