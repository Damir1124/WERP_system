"""
Middleware для авторизации пользователей по Telegram ID.
Определяет роль пользователя (курьер, клиент, администратор) и сохраняет её в data.
"""
import logging
from typing import Any, Awaitable, Callable, Dict

import aiohttp
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from tg_bot.config import DJANGO_API_URL

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware, который для каждого апдейта:
    1. Извлекает Telegram ID отправителя.
    2. Делает запрос к Django API для идентификации роли.
    3. Сохраняет роль и данные пользователя в data['user'].
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Извлекаем пользователя Telegram из события
        tg_user: TgUser = data.get('event_from_user')
        if not tg_user:
            # Если нет пользователя (например, канал пост), пропускаем
            return await handler(event, data)

        tg_id = tg_user.id
        data['tg_id'] = tg_id

        # Пытаемся получить роль из Django API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{DJANGO_API_URL}/identify/",
                    params={'tg_id': tg_id},
                    timeout=5
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        # Единая логика: bot_role для фильтрации роутеров бота
                        role = result.get('bot_role', result.get('role', 'unknown'))
                        target_app = result.get('target_app')
                        name = result.get('name', '')
                        worker_id = result.get('worker_id')
                        client_id = result.get('client_id')
                        user_id = worker_id or client_id
                    else:
                        role = 'unknown'
                        target_app = None
                        name = ''
                        user_id = None
                        worker_id = None
                        client_id = None
        except Exception as e:
            logger.warning(f"Ошибка при идентификации tg_id={tg_id}: {e}")
            role = 'unknown'
            target_app = None
            name = ''
            user_id = None
            worker_id = None
            client_id = None

        # Сохраняем данные пользователя
        data['user'] = {
            'tg_id': tg_id,
            'role': role,
            'target_app': target_app,
            'name': name,
            'id': user_id,
            'worker_id': worker_id,
            'client_id': client_id,
            'is_authenticated': role != 'unknown'
        }

        logger.info(f"✅ Пользователь tg_id={tg_id} идентифицирован как роль='{role}', имя='{name}'")

        return await handler(event, data)