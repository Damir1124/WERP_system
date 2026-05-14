#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from apps.workers.models import Worker

# Создаём Worker с tg_id, если не существует
if not Worker.objects.filter(tg_id=123456789).exists():
    worker = Worker.objects.create(
        full_name='Тестовый Курьер',
        tg_id=123456789,
        is_admin=False,
        worker_type='courier'
    )
    print('Создан Worker с tg_id=123456789')
else:
    worker = Worker.objects.get(tg_id=123456789)
    print('Worker уже существует')

# Выводим всех Worker
workers = Worker.objects.all()
print('Всего Worker:', workers.count())
for w in workers:
    print(f'ID: {w.id}, tg_id: {w.tg_id}, is_admin: {w.is_admin}, type: {w.worker_type}, name: {w.full_name}')