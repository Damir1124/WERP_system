"""
Утилиты для работы с Telegram Mini App и проверки подписей.
"""
import hashlib
import hmac
import json
import os
import urllib.parse

from django.conf import settings
from apps.workers.models import Worker
from apps.clients.models import Client


def _parse_init_data(init_data: str) -> dict:
    """
    Разбирает initData на пары key=value БЕЗ декодирования значений.
    """
    result = {}
    if not init_data:
        return result
    for chunk in init_data.split('&'):
        if '=' in chunk:
            key, value = chunk.split('=', 1)
            result[key] = value
    return result


def verify_telegram_init_data(init_data: str) -> bool:
    """
    Проверяет подпись initData от Telegram Mini App.
    """
    if not init_data:
        return False

    if not getattr(settings, 'BOT_BRIDGE_VERIFY_INIT_DATA', False):
        return True

    parsed = _parse_init_data(init_data)
    hash_value = parsed.get('hash')
    if not hash_value:
        return False

    del parsed['hash']
    sorted_params = sorted(parsed.items(), key=lambda x: x[0])
    data_check_string = '\n'.join(
        f"{k}={v}" for k, v in sorted_params
    )

    bot_token = os.getenv('BOT_TOKEN') or getattr(settings, 'BOT_TOKEN', None)
    if not bot_token:
        return True

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, hash_value)


def extract_user_id_from_init_data(init_data: str) -> int | None:
    """Извлекает Telegram ID пользователя из initData."""
    try:
        parsed = _parse_init_data(init_data)
        user_str = parsed.get('user')
        if not user_str:
            return None
        user = json.loads(urllib.parse.unquote(user_str))
        return user.get('id')
    except Exception:
        return None


def resolve_user_role(tg_id: int) -> dict:
    """
    Единая функция определения роли пользователя.

    Порядок:
    1. Worker по tg_id (всегда приоритет)
    2. Client по tg_id
    3. Неизвестный

    Возвращает словарь:
    - role: COURIER / OWNER / OPERATOR / CLIENT / UNKNOWN
    - target_app: courier / admin / client / registration / None
    - bot_role: courier / admin / operator / owner / client / unknown (для бота)
    - name: str
    - worker_id: int | None
    - client_id: int | None
    - authenticated: bool
    """
    worker = Worker.objects.filter(tg_id=tg_id).first()
    if worker:
        if worker.worker_type == Worker.WorkerType.COURIER:
            return {
                'role': 'COURIER',
                'target_app': 'courier',
                'bot_role': 'courier',
                'name': worker.full_name,
                'worker_id': worker.id,
                'client_id': None,
                'authenticated': True,
            }
        elif worker.worker_type == Worker.WorkerType.OWNER:
            return {
                'role': 'OWNER',
                'target_app': 'admin',
                'bot_role': 'owner',
                'name': worker.full_name,
                'worker_id': worker.id,
                'client_id': None,
                'authenticated': True,
            }
        elif worker.worker_type == Worker.WorkerType.OPERATOR:
            return {
                'role': 'OPERATOR',
                'target_app': 'operator',
                'bot_role': 'operator',
                'name': worker.full_name,
                'worker_id': worker.id,
                'client_id': None,
                'authenticated': True,
            }
        elif worker.is_admin:
            return {
                'role': 'ADMIN',
                'target_app': 'admin',
                'bot_role': 'admin',
                'name': worker.full_name,
                'worker_id': worker.id,
                'client_id': None,
                'authenticated': True,
            }
        else:
            return {
                'role': 'WORKER',
                'target_app': None,
                'bot_role': None,
                'name': worker.full_name,
                'worker_id': worker.id,
                'client_id': None,
                'authenticated': True,
            }

    client = Client.objects.filter(tg_id=tg_id).first()
    if client:
        return {
            'role': 'CLIENT',
            'target_app': 'client',
            'bot_role': 'client',
            'name': client.name,
            'worker_id': None,
            'client_id': client.id,
            'authenticated': True,
        }

    return {
        'role': 'UNKNOWN',
        'target_app': 'registration',
        'bot_role': 'unknown',
        'name': None,
        'worker_id': None,
        'client_id': None,
        'authenticated': False,
    }