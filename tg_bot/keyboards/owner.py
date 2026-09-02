"""Клавиатуры для администратора (owner) в Telegram-боте."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_owner_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню администратора (reply)."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="📦 Заказы"))
    builder.add(KeyboardButton(text="➕ Создать заказ"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup(resize_keyboard=True)
