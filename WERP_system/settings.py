import os
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Читаем секреты из окружения
DEBUG = os.getenv('DEBUG', 'False') == 'True'

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Временный ключ только для локальной разработки
        SECRET_KEY = 'dev-insecure-key-for-local-development-only'
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('DJANGO_SECRET_KEY обязателен в продакшене (задайте в .env)')

# В продакшене — только реальный домен из .env.
# ngrok-домены разрешены только при DEBUG (локальная разработка).
_default_hosts = '127.0.0.1,localhost'
if DEBUG:
    _default_hosts += ',.ngrok-free.dev'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', _default_hosts).split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'channels',
    'corsheaders',
    
    # Local apps
    'apps.accounting',
    'apps.clients',
    'apps.logistics',
    'apps.products',
    'apps.warehouse',
    'apps.workers',
    'apps.bot_bridge',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'WERP_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.dashboard.context_processors.admin_dashboard_counts',
            ],
        },
    },
]

WSGI_APPLICATION = 'WERP_system.wsgi.application'

# Database - Полностью берем из .env
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5454'),
    }
}

# Остальные настройки
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Channels configuration for WebSockets
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")],
        },
    },
}

# --- Celery: фоновые задачи и расписание ---
# Брокер — отдельная база Redis (db 2), чтобы не смешивать с кэшем (db 1)
# и каналами WebSockets (db 0).
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/2")
# Результаты задач не нужны для уведомлений — экономим память Redis
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/2")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Samarkand'
CELERY_ENABLE_UTC = True

# Расписание периодических задач (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    # Напоминания о взносах по рассрочкам — каждый день в 09:00
    'send-installment-reminders-daily': {
        'task': 'apps.accounting.tasks.send_installment_reminders_task',
        'schedule': crontab(hour=9, minute=0),
    },
    # Сброс просроченных балансов зарплат — каждый день в 00:30
    'reset-expired-salaries-daily': {
        'task': 'apps.accounting.tasks.reset_expired_salaries_task',
        'schedule': crontab(hour=0, minute=30),
    },
    # Начисление зарплат — 1-го числа каждого месяца в 08:00
    'accrue-salaries-monthly': {
        'task': 'apps.accounting.tasks.accrue_salaries_task',
        'schedule': crontab(hour=8, minute=0, day_of_month='1'),
    },
    # Пересчёт Finance за вчера (страховка от пропущенных сигналов) — каждый день в 00:05
    'recalc-finance-yesterday-daily': {
        'task': 'apps.dashboard.tasks.recalc_finance_for_date_task',
        'schedule': crontab(hour=0, minute=5),
    },
}

# ASGI application for Django Channels
ASGI_APPLICATION = "WERP_system.asgi.application"

LANGUAGE_CODE = 'ru-ru' # Поставил русский для удобства ERP
TIME_ZONE = 'Asia/Samarkand' # Твой часовой пояс
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS settings
# Разрешаем все ngrok-домены + localhost для разработки
_cors_extra = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_extra if o.strip()] or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Всегда добавляем localhost для разработки
if "http://localhost:5173" not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append("http://localhost:5173")
if "http://127.0.0.1:5173" not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append("http://127.0.0.1:5173")

# ngrok-домены разрешаем ТОЛЬКО при DEBUG (локальная разработка через туннель).
# В продакшене CORS_ALLOWED_ORIGINS задаётся в .env (реальный домен Mini App).
CORS_ALLOWED_ORIGIN_REGEXES = []
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\.ngrok-free\.dev$",
        r"^https://.*\.ngrok\.io$",
    ]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-telegram-id',
    'x-telegram-init-data',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Bot auth via X-Telegram-ID header ---
# В продакшене строгая проверка ВКЛЮЧЕНА по умолчанию (безопасно).
# Для локальной разработки можно отключить через .env: BOT_BRIDGE_REQUIRE_TG_HEADER=False
BOT_BRIDGE_REQUIRE_TG_HEADER = os.getenv('BOT_BRIDGE_REQUIRE_TG_HEADER', 'True') == 'True'

# --- Verification of Telegram initData signature ---
# В продакшене строгая проверка HMAC-подписи ВКЛЮЧЕНА по умолчанию (безопасно).
# Для локальной разработки можно отключить через .env: BOT_BRIDGE_VERIFY_INIT_DATA=False
BOT_BRIDGE_VERIFY_INIT_DATA = os.getenv('BOT_BRIDGE_VERIFY_INIT_DATA', 'True') == 'True'

# --- Telegram admin chat for shift/trip closure reports ---
# Дополнительный чат (например, группа), куда автоматически отправляются отчёты
# о закрытии рейсов и смен курьеров. Отчёты всегда уходят ВСЕМ сотрудникам с
# worker_type=OWNER и заполненным tg_id; ADMIN_CHAT_ID добавляется к ним.
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# --- SSL / HTTPS (продакшен) ---
# Включаются только когда DEBUG=False (защита от случайного включения в разработке).
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
