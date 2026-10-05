"""
accounts/decorators.py
Декораторы для проверки прав доступа на основе ролей пользователя.
Использование:
    @login_required
    @role_required('admin', 'manager')
    def my_view(request): ...

Студент: Нестерук Д.С., группа ПО-2409
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """
    Декоратор для ограничения доступа к view по ролям пользователя.

    Принимает одну или несколько допустимых ролей.
    Если роль пользователя не совпадает — перенаправляет на страницу
    403 (доступ запрещён) с понятным сообщением об ошибке.

    Пример:
        @role_required('admin')                      # только администратор
        @role_required('admin', 'manager')           # admin или manager
        @role_required('manager', 'warehouse_staff') # manager или кладовщик
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role in roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            messages.error(
                request,
                f'У вас недостаточно прав для выполнения этого действия. '
                f'Требуется роль: {", ".join(roles)}.'
            )
            return redirect('accounts:access_denied')
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Сокращение: только администраторы."""
    return role_required('admin')(view_func)


def manager_or_admin_required(view_func):
    """Сокращение: менеджеры и администраторы."""
    return role_required('admin', 'manager')(view_func)


def warehouse_staff_required(view_func):
    """Сокращение: сотрудники склада, менеджеры и администраторы."""
    return role_required('admin', 'manager', 'warehouse_staff')(view_func)
