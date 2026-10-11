"""
suppliers/forms.py
Формы для работы с поставщиками и заказами на закупку.

Студент: Нестерук Д.С., группа ПО-2409
"""

from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from .models import Supplier, PurchaseOrder, OrderItem


# ---------------------------------------------------------------------------
# Вспомогательный CSS-миксин для Bootstrap 5
# ---------------------------------------------------------------------------
class BootstrapMixin:
    """Добавляет Bootstrap-классы всем полям формы."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = f'{existing} form-check-input'.strip()
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = f'{existing} form-select'.strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = f'{existing} form-control'.strip()
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs['class'] = f'{existing} form-control'.strip()


# ---------------------------------------------------------------------------
# Форма поставщика
# ---------------------------------------------------------------------------
class SupplierForm(BootstrapMixin, forms.ModelForm):
    """
    Форма создания и редактирования поставщика.
    Валидирует УНП/ИНН, email и телефон.
    """

    class Meta:
        model = Supplier
        fields = [
            'name', 'inn', 'contact_person',
            'phone', 'email', 'address', 'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'name':           'Наименование организации',
            'inn':            'УНП / ИНН',
            'contact_person': 'Контактное лицо',
            'phone':          'Телефон',
            'email':          'Email',
            'address':        'Юридический адрес',
            'notes':          'Примечания',
        }

    def clean_inn(self):
        """Проверяем, что УНП/ИНН содержит только цифры (если заполнен)."""
        inn = self.cleaned_data.get('inn', '').strip()
        if inn and not inn.isdigit():
            raise ValidationError('УНП/ИНН должен содержать только цифры.')
        return inn

    def clean_email(self):
        """Приводим email к нижнему регистру."""
        return self.cleaned_data.get('email', '').lower().strip()

    def clean_name(self):
        """Trim пробелов с обеих сторон наименования."""
        return self.cleaned_data.get('name', '').strip()


# ---------------------------------------------------------------------------
# Форма заказа на закупку
# ---------------------------------------------------------------------------
class PurchaseOrderForm(BootstrapMixin, forms.ModelForm):
    """
    Форма создания и редактирования заказа на закупку.
    Выбор поставщика, плановой даты и комментария.
    """

    class Meta:
        model = PurchaseOrder
        fields = ['number', 'supplier', 'planned_date', 'comment']
        widgets = {
            'planned_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'number':       'Номер документа',
            'supplier':     'Поставщик',
            'planned_date': 'Плановая дата поставки',
            'comment':      'Комментарий',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Пустой вариант для выпадающего списка поставщиков
        self.fields['supplier'].empty_label = '— Выберите поставщика —'

    def clean_number(self):
        """Убираем лишние пробелы из номера документа."""
        return self.cleaned_data.get('number', '').strip()


# ---------------------------------------------------------------------------
# Форма смены статуса заказа
# ---------------------------------------------------------------------------
class OrderStatusForm(forms.Form):
    """
    Форма одного поля: выбор нового статуса заказа.
    Динамически ограничивает choices допустимыми переходами.
    """

    new_status = forms.ChoiceField(
        label='Новый статус',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, order, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = order.get_allowed_transitions()
        self.fields['new_status'].choices = [
            (s, PurchaseOrder.Status(s).label)
            for s in allowed
        ]
        if not allowed:
            self.fields['new_status'].widget.attrs['disabled'] = True


# ---------------------------------------------------------------------------
# Инлайн-формсет позиций заказа
# ---------------------------------------------------------------------------
class OrderItemForm(BootstrapMixin, forms.ModelForm):
    """Форма одной позиции заказа (используется в формсете)."""

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'purchase_price']
        widgets = {
            'product':        forms.Select(),
            'quantity':       forms.NumberInput(attrs={'min': 1}),
            'purchase_price': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
        }
        labels = {
            'product':        'Товар',
            'quantity':       'Количество',
            'purchase_price': 'Цена закупки (руб.)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].empty_label = '— Выберите товар —'

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty <= 0:
            raise ValidationError('Количество должно быть больше нуля.')
        return qty

    def clean_purchase_price(self):
        price = self.cleaned_data.get('purchase_price')
        if price is not None and price <= 0:
            raise ValidationError('Цена закупки должна быть больше нуля.')
        return price


# Формсет для позиций заказа (min=1, extra=1 пустая строка для новых)
OrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
