"""
Роутер для обработки команд клиента.
"""
import logging

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tg_bot.config import DJANGO_API_URL, MINI_APP_URL
from tg_bot.keyboards.client import (
    get_client_main_keyboard,
    get_catalog_keyboard,
    get_order_history_keyboard,
    get_unknown_user_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="client")


@router.message(Command("start"))
async def cmd_start(message: Message, user: dict = None):
    """Обработка команды /start для клиента."""
    tg_user = message.from_user
    name = (user or {}).get('name') or tg_user.first_name

    await message.answer(
        f"👋 Здравствуйте, {name}!\n\n"
        f"💧 <b>Osnova 2.0</b> — доставка питьевой воды\n\n"
        f"Нажмите кнопку ниже, чтобы открыть каталог и сделать заказ:",
        reply_markup=get_client_main_keyboard(),
        parse_mode='HTML'
    )


@router.message(F.text == "📋 Мои заказы")
async def show_my_orders(message: Message, user: dict = None):
    """Показать историю заказов клиента через Mini App."""
    await message.answer(
        "📦 <b>Ваши заказы</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть историю заказов:",
        reply_markup=get_order_history_keyboard(),
        parse_mode='HTML'
    )


@router.message(F.text == "📍 Мой адрес")
async def show_my_address(message: Message, user: dict = None):
    """Показать сохранённый адрес клиента."""
    tg_id = (user or {}).get('tg_id') or message.from_user.id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DJANGO_API_URL}/client/profile/",
                params={'tg_id': tg_id},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    address = data.get('address') or 'Адрес не указан'
                    name = data.get('name', '')
                    phone = data.get('phone', '')
                    await message.answer(
                        f"🏠 <b>Ваш профиль:</b>\n\n"
                        f"👤 Имя: {name}\n"
                        f"📞 Телефон: {phone}\n"
                        f"📍 Адрес: {address}\n\n"
                        f"Для изменения адреса обратитесь в поддержку.",
                        parse_mode='HTML'
                    )
                else:
                    await message.answer("❌ Не удалось загрузить профиль. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при получении профиля клиента: {e}")
        await message.answer("❌ Ошибка подключения к серверу.")


@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показать справку для клиента."""
    await message.answer(
        "📖 <b>Помощь:</b>\n\n"
        "🛒 <b>Заказать воду</b> — открывает каталог товаров\n"
        "📋 <b>Мои заказы</b> — история и статусы заказов\n"
        "📍 <b>Мой адрес</b> — ваш адрес доставки\n\n"
        "По вопросам обращайтесь к оператору.",
        parse_mode='HTML'
    )
