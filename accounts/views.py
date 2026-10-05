"""
accounts/views.py
Контроллеры подсистемы аутентификации и управления учётными записями.
Студент: Нестерук Д.С., группа ПО-2409
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegisterForm
from .models import CustomUser


# ---------------------------------------------------------------------------
# Вспомогательная функция: перенаправление по роли после входа
# ---------------------------------------------------------------------------

def _redirect_after_login(user):
    """
    Возвращает URL для перенаправления на основе роли пользователя.
    Администратор и менеджер попадают на дашборд.
    Сотрудник склада — на страницу регистрации складских операций.
    """
    if user.is_admin or user.is_manager:
        return 'inventory:dashboard'
    return 'inventory:dashboard'  # в будущем: 'inventory:stock_in'


# ---------------------------------------------------------------------------
# Вход в систему
# ---------------------------------------------------------------------------

@require_http_methods(['GET', 'POST'])
def login_view(request):
    """
    Страница входа в систему.
    GET:  показывает форму входа.
    POST: проверяет учётные данные, при успехе перенаправляет по роли.
    Если пользователь уже вошёл — сразу перенаправляем на дашборд.
    """
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request,
                f'Добро пожаловать, {user.get_full_name() or user.username}!'
            )
            # Поддержка параметра ?next= для перенаправления после входа
            next_url = request.GET.get('next') or _redirect_after_login(user)
            # Если next_url — имя url-паттерна, используем redirect с именем
            try:
                return redirect(next_url)
            except Exception:
                return redirect('inventory:dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')

    return render(request, 'accounts/login.html', {'form': form})


# ---------------------------------------------------------------------------
# Выход из системы
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['POST'])
def logout_view(request):
    """
    Выход из системы. Принимает только POST для защиты от CSRF-атак.
    Форма выхода должна использовать метод POST с {% csrf_token %}.
    """
    username = request.user.get_full_name() or request.user.username
    logout(request)
    messages.info(request, f'Вы вышли из системы. До свидания, {username}!')
    return redirect('accounts:login')


# ---------------------------------------------------------------------------
# Регистрация нового пользователя
# ---------------------------------------------------------------------------

@require_http_methods(['GET', 'POST'])
def register_view(request):
    """
    Страница регистрации нового пользователя.
    Доступна только для неаутентифицированных пользователей.
    После успешной регистрации — автоматический вход и перенаправление.
    """
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            # Автоматически входим после регистрации
            login(request, user)
            messages.success(
                request,
                f'Учётная запись создана. Добро пожаловать, {user.get_full_name() or user.username}!'
            )
            return redirect(_redirect_after_login(user))
        else:
            messages.error(
                request,
                'Пожалуйста, исправьте ошибки в форме.'
            )

    return render(request, 'accounts/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Страница "Доступ запрещён" (403)
# ---------------------------------------------------------------------------

def access_denied_view(request):
    """
    Страница отказа в доступе. Отображается при недостаточных правах.
    """
    return render(request, 'accounts/access_denied.html', status=403)


# ---------------------------------------------------------------------------
# Профиль пользователя (заглушка, будет расширена позже)
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    """Страница профиля текущего пользователя."""
    return render(request, 'accounts/profile.html', {
        'user': request.user,
    })
