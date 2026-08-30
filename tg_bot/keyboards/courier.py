"""
Клавиатуры для курьера (reply и inline).
Стратегия «гибрид»:
- Основное меню (reply) дублирует все действия кнопками — курьер может работать
  вообще без Mini App.
- В меню всегда есть кнопка «🌐 Открыть приложение» (WebApp), ведущая на Launcher.
  Launcher сам определит роль и перенаправит в нужный Mini App.
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from tg_bot.config import LAUNCHER_URL


def get_courier_main_keyboard(has_shift: bool = False, has_trip: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню курьера (адаптивное).
    Состав кнопок зависит от состояния: нет смены -> открыть смену,
    смена без рейса -> начать рейс, рейс активен -> рабочие действия.
    Кнопка «🌐 Открыть приложение» доступна всегда и ведёт на Launcher.
    """
    builder = ReplyKeyboardBuilder()
    app_btn = KeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=LAUNCHER_URL))
    if has_trip:
        builder.add(KeyboardButton(text="➕ Создать заказ"))
        builder.add(KeyboardButton(text="📦 Заказы"))
        builder.add(KeyboardButton(text="🚚 Мой рейс"))
        builder.add(KeyboardButton(text="📋 В процессе"))
        builder.add(KeyboardButton(text="🆘 Помощь"))
        builder.add(KeyboardButton(text="📋 Смены и рейсы"))
        builder.add(app_btn)
        row_sizes = [1, 2, 2, 1, 1]
    elif has_shift:
        builder.add(KeyboardButton(text="➕ Создать заказ"))
        builder.add(KeyboardButton(text="📦 Заказы"))
        builder.add(KeyboardButton(text="🚀 Начать рейс"))
        builder.add(KeyboardButton(text="📋 В процессе"))
        builder.add(KeyboardButton(text="🆘 Помощь"))
        builder.add(KeyboardButton(text="📋 Смены и рейсы"))
        builder.add(app_btn)
        row_sizes = [1, 2, 2, 1, 1]
    else:
        builder.add(KeyboardButton(text="➕ Создать заказ"))
        builder.add(KeyboardButton(text="🟢 Открыть смену"))
        builder.add(KeyboardButton(text="📦 Заказы"))
        builder.add(KeyboardButton(text="📋 В процессе"))
        builder.add(KeyboardButton(text="📋 Смены и рейсы"))
        builder.add(KeyboardButton(text="🆘 Помощь"))
        builder.add(app_btn)
        row_sizes = [1, 1, 2, 2, 1, 1]
    builder.adjust(*row_sizes)
    return builder.as_markup(resize_keyboard=True)
# Типы продуктов, считающиеся «водой 19л» (для подсчёта в пуле заказов)
WATER_PRODUCT_TYPES = {'19W'}

# Пороги свежести заказа (как в mini app: frontend/courier/src/config/orderFreshness.js)
YELLOW_AFTER_MINUTES = 180   # 3 часа — жёлтый
RED_AFTER_MINUTES = 360      # 6 часов — красный


def get_order_address(order: dict) -> str:
    """Человекочитаемый адрес заказа (как display_address в модели Order).

    Формат:
    1. Только координаты — 'Location';
    2. И текст, и координаты — 'Location | <текст>';
    3. Только текст — '<текст>';
    4. Ничего — 'Адрес не указан'.

    Если текстовый адрес — заглушка 'Location', она не дублируется.
    """
    text = (order.get('delivery_address_text') or order.get('client_address') or '').strip()
    has_coords = bool(order.get('delivery_latitude') and order.get('delivery_longitude'))

    # Заглушка 'Location' / '📍 Location' в тексте не считается реальным адресом
    if text.lower() in ('location', '📍 location'):
        text = ''

    if text and has_coords:
        return f'Location | {text}'
    if has_coords:
        return 'Location'
    if text:
        return text
    return 'Адрес не указан'


def get_order_freshness_icon(order: dict) -> str:
    """Цветной круг свежести заказа: 🟢 свежий, 🟡 3–6ч, 🔴 более 6ч.

    Использует minutes_ago из API (OrderSerializer), при отсутствии —
    считает по created_at.
    """
    minutes = order.get('minutes_ago')
    if minutes is None:
        created_at = order.get('created_at')
        if created_at:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                minutes = int((datetime.now(dt.tzinfo) - dt).total_seconds() / 60)
            except (ValueError, TypeError):
                minutes = 0
        else:
            minutes = 0
    if minutes >= RED_AFTER_MINUTES:
        return '🔴'
    if minutes >= YELLOW_AFTER_MINUTES:
        return '🟡'
    return '🟢'


def get_order_water_qty(order: dict) -> int:
    """Суммарное количество воды 19л (продукт WATER) в заказе."""
    return sum(
        item.get('quantity', 0)
        for item in order.get('items', [])
        if item.get('product_type') in WATER_PRODUCT_TYPES
    )


def get_pool_inline_keyboard(orders: list) -> InlineKeyboardMarkup:
    """Пул заказов: кнопка на каждый заказ (#id | вода 19 | адрес) + обновить."""
    builder = InlineKeyboardBuilder()
    for order in orders[:30]:
        water_qty = get_order_water_qty(order)
        address = get_order_address(order)
        address_short = address[:28] + ('…' if len(address) > 28 else '')
        label = order.get('human_number', f"#{order['id']}")
        freshness = get_order_freshness_icon(order)
        text = f"{freshness} {label} | {water_qty} | {address_short}"
        builder.add(InlineKeyboardButton(text=text, callback_data=f"order_details_{order['id']}"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_pool"))
    builder.adjust(1)
    return builder.as_markup()


def get_couriers_list_keyboard(couriers: list) -> InlineKeyboardMarkup:
    """Список курьеров (для просмотра их заказов)."""
    builder = InlineKeyboardBuilder()
    for c in couriers:
        name = c.get('full_name') or c.get('name') or f"Курьер #{c['id']}"
        label = f"{name}"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"courier_orders_{c['id']}"
        ))
    return builder.as_markup()


def get_courier_orders_keyboard(orders: list, courier_id: int) -> InlineKeyboardMarkup:
    """Список PENDING заказов конкретного курьера."""
    builder = InlineKeyboardBuilder()
    for order in orders[:20]:
        water_qty = get_order_water_qty(order)
        address = get_order_address(order)
        address_short = address[:24] + ('…' if len(address) > 24 else '')
        display = order.get('human_number', f"#{order['id']}")
        freshness = get_order_freshness_icon(order)
        label = f"{freshness} {display} | {water_qty} | {address_short}"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"courier_order_detail_{courier_id}_{order['id']}"
        ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад к курьерам",
        callback_data="back_to_couriers"
    ))
    return builder.as_markup()


# ═════════════════════════════════════════════════════════════════════════════
# Клавиатуры для «Смены и рейсы» (3 уровня: список смен → детали смены → детали рейса)
# ═════════════════════════════════════════════════════════════════════════════

def get_shifts_list_keyboard(shifts: list, has_active_shift: bool = False) -> InlineKeyboardMarkup:
    """
    Уровень 1: список смен (до 10).
    Каждая смена — кнопка с датой, статусом и суммой.
    """
    builder = InlineKeyboardBuilder()
    for shift in shifts[:10]:
        date = shift.get('date', 'N/A')
        is_open = shift.get('status') == 'OP'
        status_icon = '🟢' if is_open else '🔴'
        total = (shift.get('cash_total') or 0) + (shift.get('card_total') or 0)
        label = f"{status_icon} {date} | {total:,.0f} сум".replace(',', ' ')
        if len(label) > 40:
            label = label[:37] + '...'
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"shift_detail_{shift['id']}"
        ))
    if has_active_shift:
        builder.row(InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="close_shift"))
    return builder.as_markup()


def get_shift_detail_keyboard(trips: list, shift_id: int) -> InlineKeyboardMarkup:
    """
    Уровень 2: список рейсов внутри смены.
    """
    builder = InlineKeyboardBuilder()
    for trip in trips:
        trip_id = trip.get('id')
        status = trip.get('status')
        is_active = status == 'AC'
        icon = '🟢' if is_active else '🔵'
        summary = trip.get('summary', {})
        delivered = summary.get('delivered', 0)
        label = f"{icon} Рейс #{trip_id} | {delivered} шт доставлено"
        if len(label) > 40:
            label = label[:37] + '...'
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"trip_detail_{trip_id}"
        ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад к списку смен",
        callback_data="back_to_shifts"
    ))
    return builder.as_markup()


def get_trip_detail_keyboard(orders: list, shift_id: int) -> InlineKeyboardMarkup:
    """
    Уровень 3: список заказов внутри рейса (только для просмотра, без действий).
    Сортировка: невыполненные сначала (от взятых недавно к раньше),
    доставленные/отменённые — в конце.
    """
    builder = InlineKeyboardBuilder()
    sorted_orders = sorted(
        orders,
        key=lambda o: (
            o.get('status') in ('DL', 'CN'),          # выполненные/отменённые в конец
            -o.get('minutes_ago', 0) if o.get('minutes_ago') is not None else 0,
        ),
    )
    for order in sorted_orders:
        status = order.get('status')
        if status == 'DL':
            icon = '🟢'
        elif status == 'CN':
            icon = '🔴'
        else:
            icon = '🟡'
        client = order.get('client_name') or 'Клиент'
        items = order.get('items', [])
        qty = sum(it.get('quantity', 0) for it in items)
        label = f"{icon} {client} | {qty} шт"
        if len(label) > 40:
            label = label[:37] + '...'
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"order_info_{order['id']}"
        ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад к смене",
        callback_data=f"back_to_shift_{shift_id}"
    ))
    return builder.as_markup()


def get_order_details_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_pool"),
        InlineKeyboardButton(text="✅ Взять заказ", callback_data=f"take_order_{order_id}"),
    )
    return builder.as_markup()


def get_deliver_orders_inline_keyboard(orders: list) -> InlineKeyboardMarkup:
    """Список не доставленных заказов рейса для подтверждения доставки."""
    builder = InlineKeyboardBuilder()
    for order in orders[:25]:
        if order.get('status') != 'PD':
            continue
        items = order.get('items', [])
        total_qty = sum(item.get('quantity', 0) for item in items)
        address = get_order_address(order)
        address_short = address[:24] + ('…' if len(address) > 24 else '')
        display = order.get('human_number', f"#{order['id']}")
        freshness = get_order_freshness_icon(order)
        text = f"{freshness} {display} | {total_qty} шт. | {address_short}"
        builder.add(InlineKeyboardButton(text=text, callback_data=f"deliver_order_{order['id']}"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_trip"))
    builder.adjust(1)
    return builder.as_markup()
