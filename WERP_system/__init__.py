# Импортируем Celery при старте Django, чтобы задачи загружались автоматически
from .celery import app as celery_app

__all__ = ('celery_app',)