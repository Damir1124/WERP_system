"""
Роутер для обработки команд администратора (owner).

Админ может:
- 📊 Смотреть сводную статистику (сегодня + за всё время)
- 📦 Просматривать пул заказов и редактировать/удалять их
- ➕ Создавать заказы
"""
import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.keyboards.owner import get_owner_main_keyboard
from tg_bot.api_client import api_client
from tg_bot.states.owner import OwnerCreateOrder, OwnerEditOrder

logger = logging.getLogger(__name__)
router = Router(name="owner")


def auth_headers(tg_id: int) -> dict:
    return {'X-Telegram-ID': str(tg_id)}


def fmt_money(value) -> str:
    try:
        return f"{int(value):,}".replace(',', ' ')
    except (TypeError, ValueError):
        return "0"


# ─── Старт ────────────────────────────────────────────────────────────────────
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start для администратора."""
    kb = get_owner_main_keyboard()
    await message.answer("👑 <b>Главное меню админа</b>", reply_markup=kb)


# ─── Статистика ───────────────────────────────────────────────────────────────
@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    """Сводная статистика за сегодня и за всё время."""
    tg_id = message.from_user.id
    data = await api_client.get('/owner/stats/', headers=auth_headers(tg_id))
    if 'error' in data:
        await message.answer(f"❌ Ошибка загрузки статистики:\n{data['error']}")
        return

    t = data.get('today', {})
    a = data.get('all_time', {})

    text = (
        "📊 <b>Сводная статистика</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>Сегодня:</b>\n"
        f"💰 Доход: {fmt_money(t.get('income', 0))} сум\n"
        f"🚚 Доставлено заказов: {t.get('delivered_orders', 0)}\n"
        f"💧 Воды доставлено: {t.get('water_delivered', 0)} шт\n"
        f"⏳ В ожидании: {t.get('pending_orders', 0)} заказов / {t.get('pending_water', 0)} шт\n"
        f"🛣 Активных рейсов: {t.get('active_trips', 0)}\n"
        f"🚛 В развозе воды: {t.get('in_transit_water', 0)} шт\n"
        f"💵 Наличные: {fmt_money(t.get('cash', 0))} сум\n"
        f"💳 Карта: {fmt_money(t.get('card', 0))} сум\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>За всё время:</b>\n"
        f"📦 Всего создано заказов: {fmt_money(a.get('total_orders', 0))}\n"
        f"💧 Всего продано воды: {fmt_money(a.get('total_water_sold', 0))} шт"
    )

    if a.get('historical_included'):
        text += "\n\n<i>*Включая данные до запуска WERP</i>"

    await message.answer(text)


# ─── Пул заказов ──────────────────────────────────────────────────────────────
async def _load_pool(tg_id: int):
    """Загрузить пул и коллег параллельно."""
    import asyncio
    pool_data, colleagues_data = await asyncio.gather(
        api_client.get('/courier/pool/', headers=auth_headers(tg_id)),
        api_client.get('/courier/colleagues/', headers=auth_headers(tg_id)),
    )
    orders = pool_data if isinstance(pool_data, list) else []
    colleagues = colleagues_data if isinstance(colleagues_data, list) else []
    return orders, colleagues


def build_pool_keyboard(orders: list) -> InlineKeyboardBuilder:
    """Кнопки пула с уникальным префиксом own_detail_ + обновить."""
    from tg_bot.keyboards.courier import get_order_water_qty, get_order_freshness_icon
    builder = InlineKeyboardBuilder()
    for order in orders[:30]:
        water_qty = get_order_water_qty(order)
        from tg_bot.keyboards.courier import get_order_address
        address = get_order_address(order)
        address_short = address[:28] + ('…' if len(address) > 28 else '')
        label = order.get('human_number', f"#{order['id']}")
        freshness = get_order_freshness_icon(order)
        builder.row(InlineKeyboardButton(
            text=f"{freshness} {label} | {water_qty} | {address_short}",
            callback_data=f"own_detail_{order['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_pool"))
    return builder


async def show_pool_for(tg_id: int, target):
    """Показать пул заказов для заданного tg_id."""
    orders, colleagues = await _load_pool(tg_id)

    from tg_bot.routers.courier import build_pool_text
    text = build_pool_text(orders, colleagues)
    kb = build_pool_keyboard(orders)
    await target.answer(text, reply_markup=kb.as_markup())


@router.message(F.text == "📦 Заказы")
async def show_pool(message: Message):
    """Показать пул заказов."""
    await show_pool_for(message.from_user.id, message)


@router.callback_query(F.data.startswith("own_detail_"))
async def show_order_detail(callback: CallbackQuery):
    """Показать детали заказа."""
    from tg_bot.routers.courier import build_pool_order_detail_text as build_detail

    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return

    text = build_detail(order_data)
    builder = InlineKeyboardBuilder()
    if order_data.get('status') == 'PD':
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"own_edit_{order_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"own_delete_{order_id}"),
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="own_back_pool"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "own_back_pool")
async def back_to_pool(callback: CallbackQuery):
    tg_id = callback.from_user.id
    await callback.message.delete()
    await show_pool_for(tg_id, callback.message)


@router.callback_query(F.data == "refresh_pool")
async def refresh_pool(callback: CallbackQuery):
    """Обновить пул заказов (перезагрузить данные и отредактировать сообщение)."""
    tg_id = callback.from_user.id
    orders, colleagues = await _load_pool(tg_id)
    from tg_bot.routers.courier import build_pool_text
    text = build_pool_text(orders, colleagues)
    kb = build_pool_keyboard(orders)
    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer("🔄 Пул обновлён")
    except TelegramBadRequest as e:
        # Сообщение не изменилось (пул тот же) — просто подтверждаем нажатие
        if 'message is not modified' in str(e):
            await callback.answer("🔄 Пул актуален")
        else:
            await callback.answer("❌ Не удалось обновить пул", show_alert=True)


# ─── Редактирование заказа (FSM: адрес → товары) ─────────────────────────────
async def get_saved_addresses(phone: str) -> list:
    data = await api_client.get(f'/clients/addresses/{phone}/')
    if isinstance(data, dict) and 'addresses' in data:
        return data['addresses']
    return []


def build_address_selection_keyboard(addresses: list):
    builder = InlineKeyboardBuilder()
    for addr in addresses:
        label = addr.get('address_text') or f"📍 {addr.get('latitude', '?')}, {addr.get('longitude', '?')}"
        builder.row(InlineKeyboardButton(
            text=label[:40],
            callback_data=f"own_addr_sel_{addr['id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Новый адрес", callback_data="own_addr_new"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data="own_addr_cancel"))
    return builder.as_markup()


@router.callback_query(F.data.startswith("own_edit_"))
async def edit_order_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование заказа — шаг 1: выбор адреса."""
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id

    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return

    await state.update_data(
        order_id=order_id,
        order_data=order_data,
        client_phone=order_data.get('client_phone', ''),
        address_text=order_data.get('delivery_address_text', ''),
        latitude=order_data.get('delivery_latitude'),
        longitude=order_data.get('delivery_longitude'),
        items=order_data.get('items', []),
    )

    client_phone = order_data.get('client_phone', '')
    saved_addresses = await get_saved_addresses(client_phone) if client_phone else []
    await state.update_data(saved_addresses=saved_addresses)

    if saved_addresses:
        text = "📍 <b>Выберите адрес доставки</b>\n\nИли добавьте новый:"
        kb = build_address_selection_keyboard(saved_addresses)
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data="own_addr_cancel"))
        await callback.message.edit_text(
            "📍 <b>Введите новый адрес доставки</b>\n\nНапишите текстом или отправьте геолокацию:",
            reply_markup=builder.as_markup()
        )
    await state.set_state(OwnerEditOrder.waiting_for_address_choice)
    await callback.answer()


@router.callback_query(F.data.startswith("own_addr_sel_"), OwnerEditOrder.waiting_for_address_choice)
async def select_saved_address(callback: CallbackQuery, state: FSMContext):
    address_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    saved = data.get('saved_addresses', [])
    addr = next((a for a in saved if a.get('id') == address_id), None)
    if not addr:
        await callback.answer("Адрес не найден", show_alert=True)
        return

    await state.update_data(
        address_text=addr.get('address_text', ''),
        latitude=addr.get('latitude'),
        longitude=addr.get('longitude'),
    )
    label = addr.get('address_text') or f"📍 {addr.get('latitude')}, {addr.get('longitude')}"
    await callback.message.edit_text(f"✅ Адрес выбран:\n{label}")
    await callback.answer()
    await edit_products_step(callback.message, state)


@router.callback_query(F.data == "own_addr_new", OwnerEditOrder.waiting_for_address_choice)
async def enter_new_address(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data="own_addr_cancel"))
    await callback.message.edit_text(
        "📍 <b>Введите новый адрес</b>\n\nНапишите текстом или отправьте геолокацию:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(OwnerEditOrder.waiting_for_address_text)
    await callback.answer()


@router.message(OwnerEditOrder.waiting_for_address_text, F.text)
async def process_address_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("❌ Пожалуйста, введите адрес.")
        return
    await state.update_data(address_text=text, latitude=None, longitude=None)
    await message.answer("✅ Адрес сохранён!")
    await edit_products_step(message, state)


@router.callback_query(F.data == "own_addr_cancel", OwnerEditOrder.waiting_for_address_choice)
async def cancel_edit_address(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')
    await state.clear()
    if order_id:
        await callback.message.delete()
        from tg_bot.routers.courier import build_pool_order_detail_text as build_detail
        tg_id = callback.from_user.id
        order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
        if 'error' not in order_data:
            text = build_detail(order_data)
            builder = InlineKeyboardBuilder()
            if order_data.get('status') == 'PD':
                builder.row(
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"own_edit_{order_id}"),
                    InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"own_delete_{order_id}"),
                )
            builder.row(InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="own_back_pool"))
            await callback.message.answer(text, reply_markup=builder.as_markup())
        else:
            await callback.message.answer("❌ Редактирование отменено.")
    else:
        await callback.message.edit_text("❌ Редактирование отменено.")
    await callback.answer()


async def edit_products_step(target, state: FSMContext):
    """Шаг 2: редактирование товаров."""
    data = await state.get_data()
    items = data.get('items', [])

    if items:
        text = "🛒 <b>Текущие товары в заказе:</b>\n\n"
        for idx, item in enumerate(items):
            text += f"{idx + 1}. {item.get('product_name', 'Товар')} × {item.get('quantity', 0)} шт.\n"
        text += "\nВыберите товар для изменения количества или добавьте новый:"
        builder = InlineKeyboardBuilder()
        for idx, item in enumerate(items):
            name = item.get('product_name', f'Товар #{idx + 1}')
            builder.row(InlineKeyboardButton(
                text=f"{name} ({item.get('quantity', 0)} шт.)",
                callback_data=f"own_item_qty_{idx}"
            ))
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="own_add_product"))
        builder.row(InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="own_save_edit"))
        builder.row(InlineKeyboardButton(text="⬅️ Назад к адресу", callback_data="own_back_to_addr"))
    else:
        text = "🛒 <b>Нет товаров в заказе</b>"
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="own_add_product"))
        builder.row(InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="own_save_edit"))

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await target.answer(text, reply_markup=builder.as_markup())
    await state.set_state(OwnerEditOrder.waiting_for_product_choice)


@router.callback_query(F.data.startswith("own_item_qty_"), OwnerEditOrder.waiting_for_product_choice)
async def change_item_quantity(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[3])
    data = await state.get_data()
    items = list(data.get('items', []))
    if idx >= len(items):
        await callback.answer("Товар не найден", show_alert=True)
        return

    item = items[idx]
    await state.update_data(edit_item_idx=idx, edit_item=item)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"own_qty_dec_{idx}"),
        InlineKeyboardButton(text=f"{item.get('quantity', 0)}", callback_data="own_qty_show"),
        InlineKeyboardButton(text="➕", callback_data=f"own_qty_inc_{idx}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="own_qty_done"))
    await callback.message.edit_text(
        f"🛒 <b>{item.get('product_name', 'Товар')}</b>\n\nИзмените количество:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(OwnerEditOrder.waiting_for_product_quantity)
    await callback.answer()


@router.callback_query(F.data.startswith("own_qty_"), OwnerEditOrder.waiting_for_product_quantity)
async def adjust_quantity(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]
    data = await state.get_data()
    idx = data.get('edit_item_idx')
    items = list(data.get('items', []))

    if idx is None or idx >= len(items):
        await callback.answer("Ошибка", show_alert=True)
        return

    qty = items[idx].get('quantity', 1)
    if action == 'inc':
        items[idx]['quantity'] = qty + 1
    elif action == 'dec':
        items[idx]['quantity'] = max(1, qty - 1)
    elif action == 'done':
        await state.update_data(items=items)
        await callback.answer("✅ Количество обновлено!")
        await edit_products_step(callback.message, state)
        return

    await state.update_data(items=items)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"own_qty_dec_{idx}"),
        InlineKeyboardButton(text=f"{items[idx]['quantity']}", callback_data="own_qty_show"),
        InlineKeyboardButton(text="➕", callback_data=f"own_qty_inc_{idx}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="own_qty_done"))
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "own_add_product", OwnerEditOrder.waiting_for_product_choice)
async def add_product_list(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    data = await state.get_data()
    items = data.get('items', [])

    existing_ids = set()
    for item in items:
        pid = item.get('product') or item.get('product_id')
        if pid:
            existing_ids.add(int(pid))

    products_data = await api_client.get('/products/', headers=auth_headers(tg_id))
    all_products = products_data if isinstance(products_data, list) else []
    available = [p for p in all_products if p.get('id') not in existing_ids]

    if not available:
        await callback.answer("Нет доступных товаров для добавления", show_alert=True)
        return

    await state.update_data(available_products=available)

    builder = InlineKeyboardBuilder()
    for p in available:
        name = p.get('name', 'Товар')
        price = p.get('price', 0)
        builder.row(InlineKeyboardButton(
            text=f"{name} — {price:,} сум".replace(',', ' '),
            callback_data=f"own_sel_prod_{p['id']}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="own_back_to_products"))
    await callback.message.edit_text("➕ <b>Выберите товар для добавления:</b>", reply_markup=builder.as_markup())
    await state.set_state(OwnerEditOrder.waiting_for_product_add)
    await callback.answer()


@router.callback_query(F.data == "own_back_to_products", OwnerEditOrder.waiting_for_product_add)
async def back_to_products(callback: CallbackQuery, state: FSMContext):
    await edit_products_step(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("own_sel_prod_"), OwnerEditOrder.waiting_for_product_add)
async def add_product_selected(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    items = list(data.get('items', []))
    available = data.get('available_products', [])

    product = next((p for p in available if p.get('id') == product_id), None)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    items.append({
        'product': product['id'],
        'product_id': product['id'],
        'product_name': product['name'],
        'quantity': 1,
    })
    await state.update_data(items=items)
    await callback.answer(f"✅ {product['name']} добавлен!")
    await edit_products_step(callback, state)


@router.callback_query(F.data == "own_back_to_addr", OwnerEditOrder.waiting_for_product_choice)
async def back_to_address(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    saved_addresses = data.get('saved_addresses', [])
    if saved_addresses:
        text = "📍 <b>Выберите адрес доставки</b>"
        kb = build_address_selection_keyboard(saved_addresses)
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data="own_addr_cancel"))
        await callback.message.edit_text("📍 <b>Введите адрес доставки</b>", reply_markup=builder.as_markup())
    await state.set_state(OwnerEditOrder.waiting_for_address_choice)
    await callback.answer()


@router.callback_query(F.data == "own_save_edit")
async def save_edit(callback: CallbackQuery, state: FSMContext):
    """Сохранить изменения заказа."""
    tg_id = callback.from_user.id
    data = await state.get_data()
    order_id = data.get('order_id')
    address_text = data.get('address_text', '')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    items = data.get('items', [])

    update_data = {
        'client_address': address_text or None,
        'client_lat': float(latitude) if latitude else None,
        'client_lon': float(longitude) if longitude else None,
        'items': [
            {
                'product_id': item.get('product') or item.get('product_id'),
                'quantity': item.get('quantity', 1),
            }
            for item in items
        ],
    }

    result = await api_client.patch(
        f'/operator/orders/{order_id}/update/',
        data=update_data,
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return

    await state.clear()
    await callback.answer("✅ Заказ обновлён!")
    from tg_bot.routers.courier import build_pool_order_detail_text as build_detail
    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' not in order_data:
        text = build_detail(order_data)
        builder = InlineKeyboardBuilder()
        if order_data.get('status') == 'PD':
            builder.row(
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"own_edit_{order_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"own_delete_{order_id}"),
            )
        builder.row(InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="own_back_pool"))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text("✅ Заказ обновлён!")


# ─── Удаление заказа ──────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("own_delete_"))
async def delete_order_confirm(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"own_confirm_del_{order_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"own_detail_{order_id}"),
    )
    await callback.message.edit_text(
        f"🗑️ <b>Удалить заказ #{order_id}?</b>\n\nЭто действие необратимо.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("own_confirm_del_"))
async def confirm_delete_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[3])
    tg_id = callback.from_user.id

    result = await api_client.delete(
        f'/operator/orders/{order_id}/delete/',
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return

    await callback.answer("✅ Заказ удалён!")
    tg_id = callback.from_user.id
    await callback.message.delete()
    await show_pool_for(tg_id, callback.message)


# ─── Создание заказа ──────────────────────────────────────────────────────────
@router.message(F.text == "➕ Создать заказ")
async def create_order(message: Message, state: FSMContext):
    """Начать создание заказа."""
    await state.update_data(is_owner=True)
    await message.answer("Введите номер телефона клиента:\n(формат: +998901234567)")
    await state.set_state(OwnerCreateOrder.waiting_for_phone)


@router.message(OwnerCreateOrder.waiting_for_phone)
async def create_order_phone(message: Message, state: FSMContext):
    """Обработка телефона."""
    from apps.bot_bridge.phone_validator import validate_uzbek_phone
    try:
        validated_phone = validate_uzbek_phone(message.text)
    except ValueError as e:
        await message.answer(f"Ошибка: {str(e)}\n\nПопробуйте ещё раз:")
        return

    await state.update_data(phone=validated_phone)

    client_data = await api_client.get(f'/clients/search/?q={validated_phone}')
    if 'error' not in client_data and client_data:
        await state.update_data(client_exists=True, client_data=client_data)
        addresses_data = await api_client.get(f'/clients/addresses/{validated_phone}/')
        saved_addresses = addresses_data.get('addresses', []) if isinstance(addresses_data, dict) else []
        await state.update_data(saved_addresses=saved_addresses)

        builder = InlineKeyboardBuilder()
        for addr in saved_addresses:
            label = addr.get('address_text', '').strip()
            if not label and addr.get('latitude') and addr.get('longitude'):
                label = f"📍 {float(addr['latitude']):.4f}, {float(addr['longitude']):.4f}"
            if not label:
                label = f"Адрес #{addr['id']}"
            if len(label) > 35:
                label = label[:32] + '...'
            builder.row(InlineKeyboardButton(
                text=f"📍 {label}",
                callback_data=f"own_addr_sel_{addr['id']}"
            ))
        builder.row(InlineKeyboardButton(text="✍️ Ввести новый адрес", callback_data="own_enter_new_addr"))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="own_cancel_create"))

        await message.answer(
            f"✅ Клиент найден: {client_data.get('name', 'Нет')}\n\nВыберите адрес доставки:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(OwnerCreateOrder.waiting_for_address_choice)
    else:
        await state.update_data(client_exists=False, saved_addresses=[])
        await message.answer(
            f"📝 Новый клиент!\nИмя будет создано автоматически: \"{validated_phone[-4:]}\"\n\n"
            f"Введите адрес доставки:\n(или отправьте геолокацию)"
        )
        await state.set_state(OwnerCreateOrder.waiting_for_address_text)


@router.callback_query(F.data == "own_enter_new_addr", OwnerCreateOrder.waiting_for_address_choice)
async def create_enter_new_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📍 <b>Введите адрес доставки</b>\n\nНапишите текстом или отправьте геолокацию:"
    )
    await state.set_state(OwnerCreateOrder.waiting_for_address_text)
    await callback.answer()


@router.message(OwnerCreateOrder.waiting_for_address_text, F.text)
async def create_address_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("❌ Пожалуйста, введите адрес.")
        return
    await state.update_data(address=text, latitude=None, longitude=None)
    await message.answer("✅ Адрес сохранён!")
    await create_products_step(message, state)


@router.message(OwnerCreateOrder.waiting_for_address_text, F.location)
async def create_address_location(message: Message, state: FSMContext):
    loc = message.location
    await state.update_data(
        address=f"{loc.latitude:.4f}, {loc.longitude:.4f}",
        latitude=loc.latitude,
        longitude=loc.longitude,
    )
    await message.answer("✅ Геолокация получена!")
    await create_products_step(message, state)


async def create_products_step(target, state: FSMContext):
    """Шаг выбора товаров при создании заказа."""
    data = await state.get_data()
    items = data.get('items', [])
    tg_id = target.from_user.id if isinstance(target, CallbackQuery) else target.chat.id

    builder = InlineKeyboardBuilder()
    if items:
        text = "🛒 <b>Товары в заказе:</b>\n\n"
        for idx, item in enumerate(items):
            text += f"{idx + 1}. {item.get('product_name', 'Товар')} × {item.get('quantity', 0)} шт.\n"
        text += "\nДобавьте ещё товар или перейдите к оплате:"
        for idx, item in enumerate(items):
            name = item.get('product_name', f'Товар #{idx + 1}')
            builder.row(InlineKeyboardButton(
                text=f"{name} ({item.get('quantity', 0)} шт.)",
                callback_data=f"own_cqty_{idx}"
            ))
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="own_cadd_product"))
        builder.row(InlineKeyboardButton(text="💳 Выбрать оплату", callback_data="own_cpayment"))
    else:
        text = "🛒 <b>Выберите товар для заказа:</b>"
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="own_cadd_product"))

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="own_cancel_create"))
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await target.answer(text, reply_markup=builder.as_markup())
    await state.set_state(OwnerCreateOrder.waiting_for_product_choice)


@router.callback_query(F.data == "own_cadd_product", OwnerCreateOrder.waiting_for_product_choice)
async def create_add_product_list(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    data = await state.get_data()
    items = data.get('items', [])

    existing_ids = set()
    for item in items:
        pid = item.get('product_id')
        if pid:
            existing_ids.add(int(pid))

    products_data = await api_client.get('/products/', headers=auth_headers(tg_id))
    all_products = products_data if isinstance(products_data, list) else []
    available = [p for p in all_products if p.get('id') not in existing_ids]

    if not available:
        await callback.answer("Нет доступных товаров", show_alert=True)
        return

    await state.update_data(cavailable_products=available)
    builder = InlineKeyboardBuilder()
    for p in available:
        name = p.get('name', 'Товар')
        price = p.get('price', 0)
        builder.row(InlineKeyboardButton(
            text=f"{name} — {price:,} сум".replace(',', ' '),
            callback_data=f"own_csel_prod_{p['id']}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="own_cback_products"))
    await callback.message.edit_text("➕ <b>Выберите товар:</b>", reply_markup=builder.as_markup())
    await state.set_state(OwnerCreateOrder.waiting_for_product_add)
    await callback.answer()


@router.callback_query(F.data == "own_cback_products", OwnerCreateOrder.waiting_for_product_add)
async def create_back_products(callback: CallbackQuery, state: FSMContext):
    await create_products_step(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("own_csel_prod_"), OwnerCreateOrder.waiting_for_product_add)
async def create_add_product_selected(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    items = list(data.get('items', []))
    available = data.get('cavailable_products', [])

    product = next((p for p in available if p.get('id') == product_id), None)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    items.append({
        'product_id': product['id'],
        'product_name': product['name'],
        'quantity': 1,
    })
    await state.update_data(items=items)
    await callback.answer(f"✅ {product['name']} добавлен!")
    await create_products_step(callback, state)


@router.callback_query(F.data.startswith("own_cqty_"), OwnerCreateOrder.waiting_for_product_choice)
async def create_change_qty(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[2])
    data = await state.get_data()
    items = list(data.get('items', []))
    if idx >= len(items):
        await callback.answer("Товар не найден", show_alert=True)
        return

    item = items[idx]
    await state.update_data(cedit_item_idx=idx)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"own_cqty_dec_{idx}"),
        InlineKeyboardButton(text=f"{item.get('quantity', 1)}", callback_data="own_cqty_show"),
        InlineKeyboardButton(text="➕", callback_data=f"own_cqty_inc_{idx}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="own_cqty_done"))
    await callback.message.edit_text(
        f"🛒 <b>{item.get('product_name', 'Товар')}</b>\n\nИзмените количество:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(OwnerCreateOrder.waiting_for_product_quantity)
    await callback.answer()


@router.callback_query(F.data.startswith("own_cqty_"), OwnerCreateOrder.waiting_for_product_quantity)
async def create_adjust_qty(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[3]
    data = await state.get_data()
    idx = data.get('cedit_item_idx')
    items = list(data.get('items', []))

    if idx is None or idx >= len(items):
        await callback.answer("Ошибка", show_alert=True)
        return

    qty = items[idx].get('quantity', 1)
    if action == 'inc':
        items[idx]['quantity'] = qty + 1
    elif action == 'dec':
        items[idx]['quantity'] = max(1, qty - 1)
    elif action == 'done':
        await state.update_data(items=items)
        await callback.answer("✅ Количество обновлено!")
        await create_products_step(callback.message, state)
        return

    await state.update_data(items=items)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"own_cqty_dec_{idx}"),
        InlineKeyboardButton(text=f"{items[idx]['quantity']}", callback_data="own_cqty_show"),
        InlineKeyboardButton(text="➕", callback_data=f"own_cqty_inc_{idx}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="own_cqty_done"))
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "own_cpayment", OwnerCreateOrder.waiting_for_product_choice)
async def create_payment(callback: CallbackQuery, state: FSMContext):
    """Выбор типа оплаты."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💵 Наличные", callback_data="own_pay_CASH"))
    builder.row(InlineKeyboardButton(text="💳 Карта", callback_data="own_pay_CARD"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="own_cback_payment"))
    await callback.message.edit_text("💳 <b>Выберите тип оплаты:</b>", reply_markup=builder.as_markup())
    await state.set_state(OwnerCreateOrder.waiting_for_payment)
    await callback.answer()


@router.callback_query(F.data == "own_cback_payment", OwnerCreateOrder.waiting_for_payment)
async def create_back_payment(callback: CallbackQuery, state: FSMContext):
    await create_products_step(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("own_pay_"), OwnerCreateOrder.waiting_for_payment)
async def create_payment_selected(callback: CallbackQuery, state: FSMContext):
    payment_type = callback.data.split("_")[2]
    await state.update_data(payment_type=payment_type)
    await show_order_confirmation(callback.message, state)
    await callback.answer()


async def show_order_confirmation(target, state: FSMContext):
    """Показать подтверждение заказа."""
    data = await state.get_data()
    phone = data.get('phone')
    address = data.get('address')
    items = data.get('items', [])
    payment_type = data.get('payment_type')

    items_text = "\n".join([f"• {item['product_name']} x {item['quantity']} шт." for item in items])

    payment_display = {'CASH': 'Наличные', 'CARD': 'Карта', 'BONUS': 'Бонусы'}.get(payment_type, payment_type)

    if data.get('client_exists') and data.get('client_data'):
        client_label = data['client_data'].get('name', phone)
    else:
        client_label = f"{phone[-4:]} (новый)"

    text = (
        f"✅ <b>Подтверждение заказа:</b>\n\n"
        f"👤 Клиент: {client_label}\n"
        f"📞 Телефон: {phone}\n"
        f"📍 Адрес: {address}\n\n"
        f"🛒 Товары:\n{items_text}\n\n"
        f"💳 Оплата: {payment_display}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Создать заказ", callback_data="own_confirm_create"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="own_cancel_create"))
    await target.answer(text, reply_markup=builder.as_markup())
    await state.set_state(OwnerCreateOrder.waiting_for_confirmation)


@router.callback_query(F.data == "own_confirm_create", OwnerCreateOrder.waiting_for_confirmation)
async def confirm_create_order(callback: CallbackQuery, state: FSMContext):
    """Создать заказ."""
    data = await state.get_data()
    tg_id = callback.from_user.id

    items_payload = [
        {"product_id": it["product_id"], "quantity": it["quantity"]}
        for it in data.get('items', [])
    ]
    payment_map = {'CASH': 'CH', 'CARD': 'CD', 'BONUS': 'BS'}
    order_data = {
        "client_phone": data.get('phone'),
        "client_address": data.get('address'),
        "client_lat": data.get('latitude'),
        "client_lon": data.get('longitude'),
        "items": items_payload,
        "payment_type": payment_map.get(data.get('payment_type', 'CASH'), 'CH')
    }

    result = await api_client.post(
        '/courier/orders/create-new/',
        data=order_data,
        headers=auth_headers(tg_id)
    )

    if 'error' in result:
        await callback.message.edit_text(
            f"❌ Ошибка создания заказа:\n{result.get('error')}\n\nПопробуйте ещё раз."
        )
    else:
        order_id = result.get('order_id', 'N/A')
        display = result.get('display_number', order_id)
        await state.clear()
        await callback.message.edit_text(f"✅ <b>Заказ {display} создан!</b>")
    await callback.answer()


@router.callback_query(F.data == "own_cancel_create")
async def cancel_create_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    kb = get_owner_main_keyboard()
    await callback.message.answer("❌ Создание заказа отменено.", reply_markup=kb)
    await callback.answer()


# ─── Помощь ────────────────────────────────────────────────────────────────────
@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    await message.answer(
        "🆘 <b>Помощь админа</b>\n\n"
        "• 📊 Статистика — сводка за сегодня и за всё время\n"
        "• 📦 Заказы — пул заказов, просмотр и редактирование\n"
        "• ➕ Создать заказ — новый заказ для клиента\n"
        "• 🆘 Помощь — эта подсказка"
    )
