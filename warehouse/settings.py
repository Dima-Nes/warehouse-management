"""
Django settings for warehouse project.
Система управления складом с элементами прогнозирования и аналитики

Студент: Нестерук Дмитрий Сергеевич, группа ПО-2409
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ===========================================================================
# БЕЗОПАСНОСТЬ
# ===========================================================================
SECRET_KEY = 'django-insecure-warehouse-project-po2409-nesteruk-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# ===========================================================================
# ПРИЛОЖЕНИЯ
# ===========================================================================
INSTALLED_APPS = [
    # Стандартные приложения Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Наши приложения
    'accounts',     # Пользователи и роли
    'inventory',    # Товары, категории, складские остатки и движения
    'suppliers',    # Поставщики и заказы
    'analytics',    # Аналитика и прогнозирование
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'warehouse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Общая папка шаблонов на уровне проекта
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'warehouse.wsgi.application'


# ===========================================================================
# БАЗА ДАННЫХ — PostgreSQL
# Убедись что PostgreSQL.app запущен и инициализирован
# ===========================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'warehouse_db',        # Имя базы данных
        'USER': 'dmitrij',             # Системный пользователь Mac (PostgreSQL.app)
        'PASSWORD': '',                # Пустой пароль по умолчанию в PostgreSQL.app
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# ===========================================================================
# КАСТОМНАЯ МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ
# ===========================================================================
AUTH_USER_MODEL = 'accounts.CustomUser'

# Перенаправление после входа и выхода
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'


# ===========================================================================
# ВАЛИДАЦИЯ ПАРОЛЕЙ
# ===========================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ===========================================================================
# ЛОКАЛИЗАЦИЯ
# ===========================================================================
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Minsk'
USE_I18N = True
USE_TZ = True


# ===========================================================================
# СТАТИЧЕСКИЕ ФАЙЛЫ (CSS, JS, изображения)
# ===========================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ===========================================================================
# EMAIL — SMTP (пока выводим в консоль для разработки)
# ===========================================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# В production заменить на:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your@email.com'
# EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'warehouse@example.com'

# Порог уведомлений (по умолчанию отправляем если остаток упал ниже min_quantity)
LOW_STOCK_EMAIL_RECIPIENT = 'admin@example.com'


# ===========================================================================
# ПРОЧЕЕ
# ===========================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
