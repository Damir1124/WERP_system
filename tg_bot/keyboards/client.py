"""
Клавиатуры для клиента (reply и inline).
Все взаимодействия — через кнопки Telegram, без Mini App.
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_client_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню клиента."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🛒 Заказать воду"))
    builder.add(KeyboardButton(text="📋 Мои заказы"))
    builder.add(KeyboardButton(text="📍 Мой адрес"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите действие")


# ─── Клавиатуры для FSM заказа воды ───────────────────────────────────────────

def get_location_request_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой отправки геолокации."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📍 Отправить местоположение", request_location=True))
    builder.add(KeyboardButton(text="⬅️ Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой отправки номера телефона."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Отправить номер", request_contact=True))
    builder.add(KeyboardButton(text="⬅️ Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_quantity_keyboard() -> InlineKeyboardMarkup:
    """
    Inline-клавиатура с сеткой чисел для быстрого выбора количества.
    Показывает числа от 2 до 10 в сетке 3x3. Больше можно ввести вручную.
    """
    builder = InlineKeyboardBuilder()
    # Сетка 3x3: числа от 2 до 10
    for n in range(2, 11):
        builder.add(InlineKeyboardButton(text=str(n), callback_data=f"client_qty_{n}"))
    builder.adjust(3)
    return builder.as_markup()


def get_phone_confirm_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для подтверждения существующего номера."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Да, использовать", callback_data="phone_confirm_yes"))
    builder.add(InlineKeyboardButton(text="📱 Изменить номер", callback_data="phone_confirm_change"))
    builder.adjust(2)
    return builder.as_markup()


def get_address_selection_keyboard(addresses: list) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора адреса из сохранённых.
    
    Args:
        addresses: Список словарей с ключами id, address_text, latitude, longitude
    """
    builder = InlineKeyboardBuilder()
    
    for addr in addresses:
        label = addr.get('address_text', '').strip()
        if not label and addr.get('latitude') and addr.get('longitude'):
            label = f"📍 {float(addr['latitude']):.4f}, {float(addr['longitude']):.4f}"
        if not label:
            label = f"Адрес #{addr['id']}"
        if len(label) > 35:
            label = label[:32] + '...'
        
        builder.row(InlineKeyboardButton(
            text=f"🏠 {label}",
            callback_data=f"client_addr_select_{addr['id']}"
        ))
    
    builder.row(InlineKeyboardButton(
        text="➕ Добавить новый адрес",
        callback_data="client_addr_new"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="client_addr_back"
    ))
    
    return builder.as_markup()


def get_order_confirm_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для подтверждения заказа."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="client_order_confirm"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="client_order_cancel"))
    builder.adjust(1)
    return builder.as_markup()
