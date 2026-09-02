"""
Клавиатуры для администратора (reply и inline).
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню администратора (reply)."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📊 Статистика сегодня"))
    builder.add(KeyboardButton(text="🚚 Активные смены"))
    builder.add(KeyboardButton(text="📦 Склад (алерты)"))
    builder.add(KeyboardButton(text="📋 Последние заказы"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Действия со статистикой (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить",
        callback_data="refresh_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🚚 Смены сегодня",
        callback_data="show_shifts"
    ))
    builder.add(InlineKeyboardButton(
        text="📦 Склад",
        callback_data="show_stock"
    ))
    builder.add(InlineKeyboardButton(
        text="📈 Финансы за неделю",
        callback_data="finance_week"
    ))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_shifts_keyboard() -> InlineKeyboardMarkup:
    """Действия со сменами (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить",
        callback_data="refresh_shifts"
    ))
    builder.add(InlineKeyboardButton(
        text="📞 Позвонить курьеру",
        url="tel:+998901234567"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Детали смены",
        callback_data="shift_details_1"
    ))
    builder.add(InlineKeyboardButton(
        text="📋 Все смены за день",
        callback_data="all_shifts"
    ))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_stock_alerts_keyboard() -> InlineKeyboardMarkup:
    """Действия с алертами склада (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить",
        callback_data="refresh_stock"
    ))
    builder.add(InlineKeyboardButton(
        text="📦 Весь склад",
        callback_data="full_stock"
    ))
    builder.add(InlineKeyboardButton(
        text="📝 Заказать поставку",
        callback_data="order_supply"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Движения",
        callback_data="stock_movements"
    ))
    builder.adjust(2, 2)
    return builder.as_markup()


def get_finance_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для финансовых отчётов."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📅 За сегодня",
        callback_data="finance_today"
    ))
    builder.add(InlineKeyboardButton(
        text="📅 За неделю",
        callback_data="finance_week"
    ))
    builder.add(InlineKeyboardButton(
        text="📅 За месяц",
        callback_data="finance_month"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 График прибыли",
        callback_data="profit_chart"
    ))
    builder.adjust(2, 2)
    return builder.as_markup()