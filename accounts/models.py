from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя с поддержкой ролей.
    Расширяет стандартную модель Django User.
    Роли:
        - admin (Администратор): полный доступ, управление пользователями
        - manager (Менеджер): заказы, аналитика, поставщики
        - warehouse_staff (Сотрудник склада): приход/расход/перемещение
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        MANAGER = 'manager', 'Менеджер'
        WAREHOUSE_STAFF = 'warehouse_staff', 'Сотрудник склада'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WAREHOUSE_STAFF,
        verbose_name='Роль',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    # ------------------------------------------------------------------ #
    # Вспомогательные свойства для удобных проверок в шаблонах и views   #
    # ------------------------------------------------------------------ #

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_warehouse_staff(self):
        return self.role == self.Role.WAREHOUSE_STAFF
