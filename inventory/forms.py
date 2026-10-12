"""
inventory/forms.py
Формы приложения inventory:
  — ProductForm, CategoryForm   (CRUD номенклатуры)
  — StockInForm, StockOutForm   (складские операции)
  — MovementFilterForm          (фильтр журнала)

Студент: Нестерук Д.С., группа ПО-2409
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Category, Product, StockMovement


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


# ===========================================================================
# ФОРМЫ НОМЕНКЛАТУРЫ
# ===========================================================================

class CategoryForm(BootstrapMixin, forms.ModelForm):
    """
    Форма создания и редактирования категории товаров.
    """

    class Meta:
        model = Category
        fields = ['name', 'description']
        labels = {
            'name':        'Название категории',
            'description': 'Описание',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        return self.cleaned_data.get('name', '').strip()


class ProductForm(BootstrapMixin, forms.ModelForm):
    """
    Форма создания и редактирования карточки товара.
    Включает выбор категории, поставщика, единицы измерения.
    """

    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'category', 'supplier',
            'unit', 'price', 'quantity', 'min_quantity',
            'description',
        ]
        labels = {
            'sku':          'Артикул (SKU)',
            'name':         'Наименование товара',
            'category':     'Категория',
            'supplier':     'Основной поставщик',
            'unit':         'Единица измерения',
            'price':        'Базовая цена (руб.)',
            'quantity':     'Текущий остаток',
            'min_quantity': 'Минимальный остаток',
            'description':  'Описание товара',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price':       forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'quantity':    forms.NumberInput(attrs={'min': 0}),
            'min_quantity': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = '— Выберите категорию —'
        self.fields['supplier'].empty_label = '— Без поставщика —'
        self.fields['supplier'].required = False

    def clean_sku(self):
        return self.cleaned_data.get('sku', '').strip().upper()

    def clean_name(self):
        return self.cleaned_data.get('name', '').strip()

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise ValidationError('Цена не может быть отрицательной.')
        return price


# ===========================================================================
# ФОРМЫ СКЛАДСКИХ ОПЕРАЦИЙ
# ===========================================================================

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
