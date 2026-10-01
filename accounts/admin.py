from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Панель администратора для пользователей с поддержкой ролей."""

    model = CustomUser

    # Колонки в списке пользователей
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    # Добавляем поле role к стандартным полям редактирования
    fieldsets = UserAdmin.fieldsets + (
        ('Роль в системе', {'fields': ('role',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Роль в системе', {'fields': ('role',)}),
    )
