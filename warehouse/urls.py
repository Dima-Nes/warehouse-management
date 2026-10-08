from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Кастомизация заголовков панели администратора
admin.site.site_header = 'Система управления складом'
admin.site.site_title = 'Панель администратора'
admin.site.index_title = 'Управление базой данных склада'

urlpatterns = [
    # Панель администратора Django
    path('admin/', admin.site.urls),

    # Авторизация и аккаунты
    path('accounts/', include('accounts.urls')),

    # Основные разделы приложения
    path('', include('inventory.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('analytics/', include('analytics.urls')),
]

# Обслуживание медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
