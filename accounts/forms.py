"""
accounts/forms.py
Формы аутентификации и регистрации пользователей.
Студент: Нестерук Д.С., группа ПО-2409
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate

from .models import CustomUser


class LoginForm(AuthenticationForm):
    """
    Форма входа — расширяет стандартную AuthenticationForm Django.
    Добавляет Bootstrap-классы и русские подписи.
    """

    username = forms.CharField(
        label='Имя пользователя',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя пользователя',
            'autofocus': True,
        }),
    )

    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
        }),
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'password')

    def confirm_login_allowed(self, user):
        """
        Запрещаем вход неактивным пользователям с понятным сообщением.
        """
        if not user.is_active:
            raise forms.ValidationError(
                'Учётная запись заблокирована. Обратитесь к администратору.',
                code='inactive',
            )


class RegisterForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.
    Расширяет стандартную UserCreationForm — добавляет поле роли
    и обязательный email.
    """

    first_name = forms.CharField(
        label='Имя',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя',
        }),
    )

    last_name = forms.CharField(
        label='Фамилия',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите фамилию',
        }),
    )

    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@company.ru',
        }),
    )

    username = forms.CharField(
        label='Имя пользователя',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Только латинские буквы, цифры, @/./+/-/_',
        }),
    )

    role = forms.ChoiceField(
        label='Роль',
        choices=CustomUser.Role.choices,
        initial=CustomUser.Role.WAREHOUSE_STAFF,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Минимум 6 символов',
        }),
    )

    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль ещё раз',
        }),
    )

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'username', 'email', 'role', 'password1', 'password2')

    def clean_email(self):
        """Проверяем уникальность email."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'Пользователь с таким email уже зарегистрирован.'
            )
        return email

    def clean_username(self):
        """Приводим username к нижнему регистру для единообразия."""
        username = self.cleaned_data.get('username', '').strip()
        return username

    def save(self, commit=True):
        """Сохраняем пользователя с ролью и email."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user
