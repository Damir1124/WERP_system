"""Клавиатуры для оператора (reply)."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_operator_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню оператора: создание, пул, в процессе, помощь."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="➕ Создать заказ"))
    builder.add(KeyboardButton(text="📦 Заказы"))
    builder.add(KeyboardButton(text="📋 В процессе"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup(resize_keyboard=True)