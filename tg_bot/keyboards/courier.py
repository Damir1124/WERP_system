"""
Клавиатуры для курьера (reply и inline).
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from tg_bot.config import MINI_APP_URL


def get_courier_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню курьера с кнопкой открытия Mini App."""
    builder = ReplyKeyboardBuilder()
    # Главная кнопка — открыть рабочий стол (Mini App)
    builder.add(KeyboardButton(
        text="🖥 Открыть рабочий стол",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/courier/")
    ))
    builder.add(KeyboardButton(text="📦 Пул заказов"))
    builder.add(KeyboardButton(text="🚚 Мой рейс"))
    builder.add(KeyboardButton(text="📋 Смены"))
    builder.add(KeyboardButton(text="👥 Коллеги"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_shift_actions_keyboard() -> InlineKeyboardMarkup:
    """Действия со сменой (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🟢 Открыть смену", callback_data="open_shift"))
    builder.add(InlineKeyboardButton(text="🚀 Начать рейс", callback_data="start_trip"))
    builder.add(InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="close_shift"))
    builder.add(InlineKeyboardButton(
        text="📊 Открыть рабочий стол",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/courier/")
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_trip_actions_keyboard() -> InlineKeyboardMarkup:
    """Действия с рейсом (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📊 Открыть рабочий стол",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/courier/")
    ))
    builder.add(InlineKeyboardButton(text="📦 Взять заказ из пула", callback_data="take_from_pool"))
    builder.add(InlineKeyboardButton(text="✅ Подтвердить доставку", callback_data="confirm_delivery"))
    builder.add(InlineKeyboardButton(text="🏁 Закрыть рейс", callback_data="close_trip"))
    builder.adjust(1)
    return builder.as_markup()


def get_order_confirmation_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Выбор container_op для подтверждения заказа."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 ОБМЕН (полная → пустая)",
        callback_data=f"container_op_EXCHANGE_{order_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="💰 ПРОДАЖА С ТАРОЙ",
        callback_data=f"container_op_SELL_WITH_{order_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="⚠️ БРАК (возврат)",
        callback_data=f"container_op_DEFECTIVE_{order_id}"
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_pool_keyboard() -> InlineKeyboardMarkup:
    """Пул заказов — открыть через Mini App."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📦 Открыть пул заказов",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/courier/")
    ))
    builder.adjust(1)
    return builder.as_markup()
