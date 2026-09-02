"""
Конфигурация Celery для WERP_system.

Запуск воркера:
    celery -A WERP_system worker --loglevel=info

Запуск планировщика (Celery Beat):
    celery -A WERP_system beat --loglevel=info
"""
import os

from celery import Celery

# Устанавливаем модуль настроек Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')

# Инициализируем Django (нужно для autodiscover_tasks и ORM в задачах)
import django
django.setup()

app = Celery('WERP_system')

# Читаем конфигурацию из settings.py (все настройки с префиксом CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Делаем наш app текущим по умолчанию, чтобы @shared_task
# регистрировал задачи именно в нём (а не создавал новый app).
app.set_default()

# Явно импортируем модули задач. Приложения вложены в пакет apps.*,
# поэтому autodiscover_tasks() может не найти их автоматически.
# Явный импорт гарантирует регистрацию задач при старте worker/beat.
import apps.bot_bridge.tasks  # noqa: E402,F401
import apps.accounting.tasks  # noqa: E402,F401
import apps.dashboard.tasks  # noqa: E402,F401
import apps.warehouse.tasks  # noqa: E402,F401


@app.task(bind=True)
def debug_task(self):
    """Отладочная задача для проверки работы воркера."""
    print(f'Request: {self.request!r}')