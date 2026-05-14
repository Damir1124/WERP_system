"""
Клавиатуры для клиента (reply и inline).
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from tg_bot.config import MINI_APP_URL


def get_client_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню клиента с кнопкой открытия Mini App."""
    builder = ReplyKeyboardBuilder()
    # Кнопка открытия Mini App клиента
    builder.add(KeyboardButton(
        text="🛒 Заказать воду",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/client/")
    ))
    builder.add(KeyboardButton(text="📋 Мои заказы"))
    builder.add(KeyboardButton(text="📍 Мой адрес"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_unknown_user_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для незарегистрированного пользователя."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📝 Зарегистрироваться как клиент",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/client/")
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """Открыть каталог через Mini App."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🛒 Открыть каталог",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/client/")
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_order_history_keyboard() -> InlineKeyboardMarkup:
    """Открыть историю заказов через Mini App."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📦 Открыть мои заказы",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/client/")
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_order_confirmation_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Подтверждение заказа (после выбора товара)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить заказ",
        callback_data=f"confirm_order_{order_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="✏️ Изменить количество",
        callback_data=f"edit_quantity_{order_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="cancel_order"
    ))
    builder.adjust(1)
    return builder.as_markup()
