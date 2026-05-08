"""
Клавиатуры для клиента (reply и inline).
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_client_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню клиента (reply)."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🛒 Каталог и заказ"))
    builder.add(KeyboardButton(text="📋 Мои заказы"))
    builder.add(KeyboardButton(text="📍 Мой адрес"))
    builder.add(KeyboardButton(text="🆘 Помощь"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """Каталог товаров (inline)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Вода 20л с тарой — 25 000 сум",
        callback_data="product_1"
    ))
    builder.add(InlineKeyboardButton(
        text="Вода 20л без тары — 20 000 сум",
        callback_data="product_2"
    ))
    builder.add(InlineKeyboardButton(
        text="Кулер напольный — 1 200 000 сум",
        callback_data="product_3"
    ))
    builder.add(InlineKeyboardButton(
        text="Помпа для бутыли — 80 000 сум",
        callback_data="product_4"
    ))
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить каталог",
        callback_data="refresh_catalog"
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_order_history_keyboard() -> InlineKeyboardMarkup:
    """История заказов с кнопками деталей."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📦 Заказ #101 (В пути)",
        callback_data="order_detail_101"
    ))
    builder.add(InlineKeyboardButton(
        text="📦 Заказ #100 (Доставлен)",
        callback_data="order_detail_100"
    ))
    builder.add(InlineKeyboardButton(
        text="📦 Заказ #99 (Доставлен)",
        callback_data="order_detail_99"
    ))
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить историю",
        callback_data="refresh_history"
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
        text="🚫 Отменить",
        callback_data=f"cancel_order_{order_id}"
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_payment_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа оплаты."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="💵 Наличными при получении",
        callback_data="payment_CASH"
    ))
    builder.add(InlineKeyboardButton(
        text="💳 Картой онлайн",
        callback_data="payment_CARD"
    ))
    builder.adjust(1)
    return builder.as_markup()