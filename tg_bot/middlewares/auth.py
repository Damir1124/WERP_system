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
                        role = result.get('role', 'unknown')
                        name = result.get('name', '')
                        user_id = result.get('id')
                    else:
                        role = 'unknown'
                        name = ''
                        user_id = None
        except Exception as e:
            logger.warning(f"Ошибка при идентификации tg_id={tg_id}: {e}")
            role = 'unknown'
            name = ''
            user_id = None

        # Сохраняем данные пользователя
        data['user'] = {
            'tg_id': tg_id,
            'role': role,
            'name': name,
            'id': user_id,
            'is_authenticated': role != 'unknown'
        }

        logger.debug(f"Пользователь tg_id={tg_id} идентифицирован как {role}")

        return await handler(event, data)