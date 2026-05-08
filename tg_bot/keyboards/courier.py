"""
Клавиатуры для курьера (reply и inline).
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_courier_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню курьера (reply)."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📦 Пул заказов"))
    builder.add(KeyboardButton(text="🚚 Мой рейс"))
    builder.add(KeyboardButton(text="📋 Смены и рейсы"))
    builder.add(KeyboardButton(text="👥 Коллеги"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_shift_actions_keyboard() -> InlineKeyboardMarkup:
    """Действия со сменой (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Детали смены", callback_data="shift_details"))
    builder.add(InlineKeyboardButton(text="🚀 Начать рейс", callback_data="start_trip"))
    builder.add(InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="close_shift"))
    builder.adjust(1)
    return builder.as_markup()


def get_trip_actions_keyboard() -> InlineKeyboardMarkup:
    """Действия с рейсом (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📦 Взять заказ из пула", callback_data="take_from_pool"))
    builder.add(InlineKeyboardButton(text="✅ Подтвердить доставку", callback_data="confirm_delivery"))
    builder.add(InlineKeyboardButton(text="📊 Сводка рейса", callback_data="trip_summary"))
    builder.add(InlineKeyboardButton(text="🏁 Закрыть рейс", callback_data="close_trip"))
    builder.adjust(1)
    return builder.as_markup()


def get_order_confirmation_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Выбор container_op для подтверждения заказа."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 ОБМЕН (полная → пустая)",
        callback_data=f"container_op_EXCHANGE"
    ))
    builder.add(InlineKeyboardButton(
        text="💰 ПРОДАЖА С ТАРОЙ (полная ушла)",
        callback_data=f"container_op_SELL_WITH"
    ))
    builder.add(InlineKeyboardButton(
        text="⚠️ БРАК (возврат бракованной)",
        callback_data=f"container_op_DEFECTIVE"
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_pool_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пула заказов."""
    builder = InlineKeyboardBuilder()
    # Пример заказов (в реальности динамически)
    builder.add(InlineKeyboardButton(
        text="Заказ #101 — Вода 20л × 2 — ул. Мира, 12",
        callback_data="order_assign_101"
    ))
    builder.add(InlineKeyboardButton(
        text="Заказ #102 — Вода 20л × 1 — ул. Ленина, 5",
        callback_data="order_assign_102"
    ))
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить пул",
        callback_data="refresh_pool"
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_colleagues_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для списка коллег (можно позвонить)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📞 Иван Иванов",
        url="tel:+998901234567"
    ))
    builder.add(InlineKeyboardButton(
        text="📞 Петр Петров",
        url="tel:+998902345678"
    ))
    builder.add(InlineKeyboardButton(
        text="📞 Сергей Сергеев",
        url="tel:+998903456789"
    ))
    builder.adjust(1)
    return builder.as_markup()