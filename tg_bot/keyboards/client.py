"""
Клавиатуры для клиента.
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from tg_bot.config import LAUNCHER_URL
from tg_bot.constants import (
    LANGUAGES, t,
    BTN_BACK, BTN_SKIP, BTN_ADD_ADDRESS, BTN_NEW_ADDRESS,
    BTN_DELETE, BTN_YES, BTN_NO,
    BTN_SEND_LOCATION, BTN_SEND_PHONE,
    MAIN_MENU_BTN, MY_ADDRESSES_BTN, LANG_BTN, COOLERS_BTN,
    ADDRESS_LABELS,
)


# ─── Языки ─────────────────────────────────────────────────────────────────────

def get_lang_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка: [🇷🇺 Русский] [🇺🇿 O'zbek] [🇬🇧 English]"""
    builder = InlineKeyboardBuilder()
    for code, label in LANGUAGES.items():
        builder.add(InlineKeyboardButton(text=label, callback_data=f"lang_{code}"))
    builder.adjust(3)
    return builder.as_markup()


# ─── Главное меню ──────────────────────────────────────────────────────────────

def get_main_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Главное меню клиента."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t(MAIN_MENU_BTN, lang)))
    builder.add(KeyboardButton(text=t(MY_ADDRESSES_BTN, lang)))
    builder.add(KeyboardButton(text=t(LANG_BTN, lang)))
    builder.add(KeyboardButton(text=t(COOLERS_BTN, lang)))
    builder.add(KeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=LAUNCHER_URL)))
    builder.adjust(1, 1, 2, 1)
    return builder.as_markup(resize_keyboard=True)


# ─── Количество ────────────────────────────────────────────────────────────────

def get_quantity_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Reply-клавиатура с сеткой чисел 2-10 и кнопкой Главное меню."""
    from tg_bot.constants import BTN_MAIN_MENU, t
    builder = ReplyKeyboardBuilder()
    for n in range(2, 11):
        builder.add(KeyboardButton(text=str(n)))
    builder.add(KeyboardButton(text=t(BTN_MAIN_MENU, lang)))
    # 3 колонки для чисел, последняя строка — Главное меню
    builder.adjust(3, 3, 3, 1)
    return builder.as_markup(resize_keyboard=True)


# ─── Адреса ────────────────────────────────────────────────────────────────────

def get_address_list_keyboard(addresses: list, lang: str = 'ru') -> InlineKeyboardMarkup:
    """
    Список адресов для выбора.
    Каждая кнопка: "{label or 'Адрес #N'} — {address_text или '📍 Геолокация'}"
    + кнопка [➕ Новый адрес]
    """
    builder = InlineKeyboardBuilder()
    for addr in addresses:
        label = addr.label or f"Адрес #{addr.id}"
        text = addr.address_text or '📍 Геолокация'
        builder.row(InlineKeyboardButton(
            text=f"{label} — {text}",
            callback_data=f"sel_addr_{addr.id}"
        ))
    builder.row(InlineKeyboardButton(
        text=t(BTN_NEW_ADDRESS, lang),
        callback_data="new_addr"
    ))
    return builder.as_markup()


def get_address_label_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Быстрые метки для адреса + Пропустить."""
    builder = ReplyKeyboardBuilder()
    # Показываем метки на текущем языке
    labels_map = {
        'ru': ['Дом', 'Офис', 'Работа'],
        'uz': ['Uy', 'Ofis', 'Ish'],
        'en': ['Home', 'Office', 'Work'],
    }
    for label in labels_map.get(lang, labels_map['ru']):
        builder.add(KeyboardButton(text=label))
    builder.add(KeyboardButton(text=t(BTN_SKIP, lang)))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_location_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой геолокации."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t(BTN_SEND_LOCATION, lang), request_location=True))
    builder.add(KeyboardButton(text=t(BTN_BACK, lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─── Телефон ───────────────────────────────────────────────────────────────────

def get_phone_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отправки номера."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t(BTN_SEND_PHONE, lang), request_contact=True))
    builder.add(KeyboardButton(text=t(BTN_BACK, lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─── Управление адресами ───────────────────────────────────────────────────────

def get_my_addresses_keyboard(addresses: list, lang: str = 'ru') -> InlineKeyboardMarkup:
    """
    Список адресов с кнопками удаления.
    Для каждого адреса: [🗑️ Удалить]
    + кнопка [➕ Добавить адрес]
    """
    builder = InlineKeyboardBuilder()
    for addr in addresses:
        label = addr.label or f"Адрес #{addr.id}"
        text = addr.address_text or '📍 Геолокация'
        builder.row(InlineKeyboardButton(
            text=f"{label} — {text}",
            callback_data=f"noop_{addr.id}"  # просто информация, без действия
        ))
        builder.add(InlineKeyboardButton(
            text=t(BTN_DELETE, lang),
            callback_data=f"del_addr_{addr.id}"
        ))
    builder.row(InlineKeyboardButton(
        text=t(BTN_ADD_ADDRESS, lang),
        callback_data="add_addr"
    ))
    return builder.as_markup()


def get_confirm_delete_keyboard(address_id: int, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Подтверждение удаления адреса."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t(BTN_YES, lang),
        callback_data=f"confirm_del_{address_id}"
    ))
    builder.add(InlineKeyboardButton(
        text=t(BTN_NO, lang),
        callback_data="cancel_del"
    ))
    builder.adjust(2)
    return builder.as_markup()
