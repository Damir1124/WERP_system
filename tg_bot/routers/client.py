"""
Роутер для обработки команд клиента.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tg_bot.keyboards.client import (
    get_client_main_keyboard,
    get_catalog_keyboard,
    get_order_history_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="client")


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start для клиента."""
    user_data = message.from_user
    logger.info(f"Клиент {user_data.id} запустил бота")
    
    await message.answer(
        f"👋 Здравствуйте, {user_data.first_name}!\n"
        "Вы авторизованы как клиент.\n"
        "Здесь вы можете заказать воду, посмотреть историю заказов и получить помощь.",
        reply_markup=get_client_main_keyboard()
    )


@router.message(F.text == "🛒 Каталог и заказ")
async def show_catalog(message: Message):
    """Показать каталог товаров."""
    # TODO: запрос к API /api/bot/client/products/
    await message.answer(
        "📦 **Каталог товаров:**\n"
        "• Вода 20л с тарой — 25 000 сум\n"
        "• Вода 20л без тары — 20 000 сум\n"
        "• Кулер напольный — 1 200 000 сум\n"
        "• Помпа для бутыли — 80 000 сум\n\n"
        "Нажмите на товар для заказа.",
        reply_markup=get_catalog_keyboard()
    )


@router.message(F.text == "📋 Мои заказы")
async def show_my_orders(message: Message):
    """Показать историю заказов клиента."""
    # TODO: запрос к API /api/bot/client/orders/
    await message.answer(
        "📅 **Ваши последние заказы:**\n"
        "1. #101 — Вода 20л × 2 — 50 000 сум — 🚚 В пути\n"
        "2. #100 — Вода 20л × 1 — 25 000 сум — ✅ Доставлен\n"
        "3. #99 — Кулер напольный × 1 — 1 200 000 сум — ✅ Доставлен",
        reply_markup=get_order_history_keyboard()
    )


@router.message(F.text == "📍 Мой адрес")
async def show_my_address(message: Message):
    """Показать сохранённый адрес клиента."""
    # TODO: запрос к API /api/bot/client/profile/
    await message.answer(
        "🏠 **Ваш адрес доставки:**\n"
        "г. Самарканд, ул. Мира, д. 12, кв. 34\n\n"
        "Чтобы изменить адрес, обратитесь в поддержку."
    )


@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показать справку для клиента."""
    await message.answer(
        "📖 **Помощь по командам клиента:**\n"
        "• *Каталог и заказ* — выбрать товар и оформить заказ\n"
        "• *Мои заказы* — история и статусы ваших заказов\n"
        "• *Мой адрес* — проверить адрес доставки\n"
        "• *Помощь* — это сообщение\n\n"
        "Для открытия Mini App нажмите кнопку «Каталог и заказ»."
    )


# Callback-хэндлеры
@router.callback_query(F.data.startswith("product_"))
async def select_product(callback: CallbackQuery):
    """Выбор товара из каталога."""
    product_id = callback.data.split("_")[-1]
    # TODO: переход к оформлению заказа
    await callback.answer(f"Товар #{product_id} выбран")
    await callback.message.edit_text(
        f"Вы выбрали товар #{product_id}.\n"
        "Укажите количество и адрес доставки."
    )


@router.callback_query(F.data.startswith("order_detail_"))
async def show_order_detail(callback: CallbackQuery):
    """Показать детали заказа."""
    order_id = callback.data.split("_")[-1]
    # TODO: запрос к API /api/bot/client/order/{order_id}/status/
    await callback.answer(f"Заказ #{order_id}")
    await callback.message.edit_text(
        f"📦 **Заказ #{order_id}**\n"
        "Статус: 🚚 В пути\n"
        "Курьер: Иван Иванов\n"
        "Телефон курьера: +998901234567\n"
        "Ориентировочное время доставки: 30 мин."
    )