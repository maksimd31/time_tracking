"""Test settings: изолированная конфигурация для локального запуска pytest без PostgreSQL.
Использует SQLite, локальный кеш и безопасные упрощения.
"""
from .settings import *  # noqa
import os

DEBUG = True

# Обеспечиваем SECRET_KEY
if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = 'test-secret-key'  # noqa: F405

# SQLite вместо Postgres, игнорируем переменные окружения БД
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # noqa: F405
    }
}

# Кеш в памяти (без Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-locmem'
    }
}

# Celery: максимально быстрый sync режим
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Почта в памяти
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Ускорение тестов — более быстрый парольный хэшер (по желанию)
if os.getenv('FAST_TESTS', 'True') == 'True':
    PASSWORD_HASHERS = [  # noqa: F405
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

# Отключить безопасностные middleware/настройки, влияющие на тесты (не критично)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# STATICFILES: для тестов можно не собирать, но Django должен знать директории
STATIC_ROOT = None  # noqa: F405

# Логирование упрощаем (чтобы не засорять вывод)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'}
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING'},
        'celery': {'handlers': ['console'], 'level': 'WARNING'},
    }
}

