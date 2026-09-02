"""
Роутер для обработки команд оператора.
Оператор может:
- Просматривать пул заказов (как курьер, но без кнопки взять)
- Создавать заказы
- Просматривать коллег
- Редактировать заказы (адрес и товары) через FSM
"""
import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.keyboards.operator import get_operator_main_keyboard
from tg_bot.keyboards.courier import get_pool_inline_keyboard
from tg_bot.api_client import api_client
from tg_bot.states.operator import OperatorEditOrder

logger = logging.getLogger(__name__)
router = Router(name="operator")


def auth_headers(tg_id: int) -> dict:
    return {'X-Telegram-ID': str(tg_id)}


async def get_saved_addresses(phone: str) -> list:
    """Получить сохранённые адреса клиента по номеру телефона."""
    data = await api_client.get(f'/clients/addresses/{phone}/')
    if isinstance(data, dict) and 'addresses' in data:
        return data['addresses']
    return []


def build_address_selection_keyboard(addresses: list):
    """Клавиатура выбора адреса из сохранённых."""
    builder = InlineKeyboardBuilder()
    for addr in addresses:
        label = addr.get('address_text') or f"📍 {addr.get('latitude', '?')}, {addr.get('longitude', '?')}"
        builder.row(InlineKeyboardButton(
            text=label[:40],
            callback_data=f"op_addr_sel_{addr['id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Новый адрес", callback_data="op_addr_new"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data="op_addr_cancel"))
    return builder.as_markup()


# ─── Старт ────────────────────────────────────────────────────────────────────
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start для оператора."""
    tg_id = message.from_user.id
    kb = get_operator_main_keyboard()
    await message.answer("📋 <b>Главное меню оператора</b>", reply_markup=kb)


# ─── Пул заказов (как у курьера, но без кнопки взять) ─────────────────────────
async def send_pool(tg_id: int, target: Message):
    """Загрузить пул заказов и коллег и отправить сообщение в target.

    tg_id передаётся явно, т.к. при callback-запросах target.from_user —
    это бот, а не пользователь.
    """
    pool_data, colleagues_data = await asyncio.gather(
        api_client.get('/courier/pool/', headers=auth_headers(tg_id)),
        api_client.get('/courier/colleagues/', headers=auth_headers(tg_id)),
    )
    if 'error' in pool_data:
        await target.answer("❌ Ошибка загрузки пула заказов.")
        return
    orders = pool_data if isinstance(pool_data, list) else []
    colleagues = colleagues_data if isinstance(colleagues_data, list) else []
    from tg_bot.routers.courier import build_pool_text
    text = build_pool_text(orders, colleagues)
    kb = get_pool_inline_keyboard(orders)
    await target.answer(text, reply_markup=kb)


@router.message(F.text.in_({"📦 Заказы", "📦 Пул заказов"}))
async def show_pool(message: Message):
    await send_pool(message.from_user.id, message)


@router.callback_query(F.data.startswith("order_details_"))
async def show_order_detail(callback: CallbackQuery):
    """Показать детали заказа с кнопками редактирования/удаления для PENDING."""
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
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"op_edit_{order_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"op_delete_{order_id}"),
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="op_back_to_pool"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "op_back_to_pool")
async def back_to_pool(callback: CallbackQuery):
    tg_id = callback.from_user.id
    await callback.message.delete()
    await send_pool(tg_id, callback.message)


@router.callback_query(F.data == "refresh_pool")
async def refresh_pool(callback: CallbackQuery):
    """Обновить пул заказов (перезагрузить данные и отредактировать сообщение)."""
    tg_id = callback.from_user.id
    pool_data, colleagues_data = await asyncio.gather(
        api_client.get('/courier/pool/', headers=auth_headers(tg_id)),
        api_client.get('/courier/colleagues/', headers=auth_headers(tg_id)),
    )
    if 'error' in pool_data:
        await callback.answer("❌ Ошибка загрузки пула заказов.", show_alert=True)
        return
    orders = pool_data if isinstance(pool_data, list) else []
    colleagues = colleagues_data if isinstance(colleagues_data, list) else []
    from tg_bot.routers.courier import build_pool_text
    text = build_pool_text(orders, colleagues)
    kb = get_pool_inline_keyboard(orders)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer("🔄 Пул обновлён")
    except TelegramBadRequest as e:
        # Сообщение не изменилось (пул тот же) — просто подтверждаем нажатие
        if 'message is not modified' in str(e):
            await callback.answer("🔄 Пул актуален")
        else:
            await callback.answer("❌ Не удалось обновить пул", show_alert=True)


# ─── Редактирование заказа (FSM: адрес → товары) ─────────────────────────────
@router.callback_query(F.data.startswith("op_edit_"))
async def edit_order_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование заказа — шаг 1: выбор адреса."""
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id

    # Загружаем данные заказа
    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return

    # Сохраняем в state
    await state.update_data(
        order_id=order_id,
        order_data=order_data,
        client_phone=order_data.get('client_phone', ''),
        address_text=order_data.get('delivery_address_text', ''),
        latitude=order_data.get('delivery_latitude'),
        longitude=order_data.get('delivery_longitude'),
        items=order_data.get('items', []),
    )

    # Пытаемся загрузить сохранённые адреса клиента
    client_phone = order_data.get('client_phone', '')
    saved_addresses = []
    if client_phone:
        saved_addresses = await get_saved_addresses(client_phone)
    await state.update_data(saved_addresses=saved_addresses)

    if saved_addresses:
        text = "📍 <b>Выберите адрес доставки</b>\n\nИли добавьте новый:"
        kb = build_address_selection_keyboard(saved_addresses)
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        text = "📍 <b>Введите новый адрес доставки</b>\n\nНапишите текстом или отправьте геолокацию:"
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data=f"op_addr_cancel"))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(OperatorEditOrder.waiting_for_address_choice)
    await callback.answer()


@router.callback_query(F.data.startswith("op_addr_sel_"), OperatorEditOrder.waiting_for_address_choice)
async def select_saved_address(callback: CallbackQuery, state: FSMContext):
    """Выбрать сохранённый адрес."""
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
    # Переходим к товарам
    await edit_products_step(callback.message, state)


@router.callback_query(F.data == "op_addr_new", OperatorEditOrder.waiting_for_address_choice)
async def enter_new_address(callback: CallbackQuery, state: FSMContext):
    """Ввести новый адрес."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data=f"op_addr_cancel"))
    await callback.message.edit_text(
        "📍 <b>Введите новый адрес</b>\n\nНапишите текстом или отправьте геолокацию:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(OperatorEditOrder.waiting_for_address_text)
    await callback.answer()


@router.message(OperatorEditOrder.waiting_for_address_text, F.text)
async def process_address_text(message: Message, state: FSMContext):
    """Обработка текстового адреса."""
    text = message.text.strip()
    if not text:
        await message.answer("❌ Пожалуйста, введите адрес.")
        return
    await state.update_data(address_text=text, latitude=None, longitude=None)
    await message.answer("✅ Адрес сохранён!")
    await edit_products_step(message, state)


@router.callback_query(F.data == "op_addr_cancel", OperatorEditOrder.waiting_for_address_choice)
async def cancel_edit_address(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования — возврат к деталям заказа."""
    data = await state.get_data()
    order_id = data.get('order_id')
    await state.clear()
    if order_id:
        await callback.message.delete()
        # Создаём новый callback и вызываем обработчик вручную
        # Сначала показываем пул, потом детали
        from tg_bot.keyboards.courier import get_pool_inline_keyboard
        from tg_bot.routers.courier import build_pool_order_detail_text as build_detail
        tg_id = callback.from_user.id
        order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
        if 'error' not in order_data:
            text = build_detail(order_data)
            builder = InlineKeyboardBuilder()
            if order_data.get('status') == 'PD':
                builder.row(
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"op_edit_{order_id}"),
                    InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"op_delete_{order_id}"),
                )
            builder.row(InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="op_back_to_pool"))
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
                callback_data=f"op_item_qty_{idx}"
            ))
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="op_add_product"))
        builder.row(InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="op_save_edit"))
        builder.row(InlineKeyboardButton(text="⬅️ Назад к адресу", callback_data="op_back_to_addr"))
    else:
        text = "🛒 <b>Нет товаров в заказе</b>"
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="op_add_product"))
        builder.row(InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="op_save_edit"))

    from aiogram.types import CallbackQuery
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await target.answer(text, reply_markup=builder.as_markup())
    await state.set_state(OperatorEditOrder.waiting_for_product_choice)


@router.callback_query(F.data.startswith("op_item_qty_"), OperatorEditOrder.waiting_for_product_choice)
async def change_item_quantity(callback: CallbackQuery, state: FSMContext):
    """Изменить количество выбранного товара."""
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
        InlineKeyboardButton(text="➖", callback_data=f"op_qty_dec_{idx}"),
        InlineKeyboardButton(text=f"{item.get('quantity', 0)}", callback_data="op_qty_show"),
        InlineKeyboardButton(text="➕", callback_data=f"op_qty_inc_{idx}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="op_qty_done"))
    await callback.message.edit_text(
        f"🛒 <b>{item.get('product_name', 'Товар')}</b>\n\n"
        f"Измените количество:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(OperatorEditOrder.waiting_for_product_quantity)
    await callback.answer()


@router.callback_query(F.data.startswith("op_qty_"), OperatorEditOrder.waiting_for_product_quantity)
async def adjust_quantity(callback: CallbackQuery, state: FSMContext):
    """Изменить количество товара +/-."""
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
    # Обновляем кнопки
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"op_qty_dec_{idx}"),
        InlineKeyboardButton(text=f"{items[idx]['quantity']}", callback_data="op_qty_show"),
        InlineKeyboardButton(text="➕", callback_data=f"op_qty_inc_{idx}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="op_qty_done"))
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "op_add_product", OperatorEditOrder.waiting_for_product_choice)
async def add_product_list(callback: CallbackQuery, state: FSMContext):
    """Показать список продуктов для добавления."""
    tg_id = callback.from_user.id
    data = await state.get_data()
    items = data.get('items', [])

    # ID продуктов, уже в заказе
    existing_ids = set()
    for item in items:
        pid = item.get('product') or item.get('product_id')
        if pid:
            existing_ids.add(int(pid))

    # Загружаем все продукты
    products_data = await api_client.get('/products/', headers=auth_headers(tg_id))
    all_products = products_data if isinstance(products_data, list) else []

    # Фильтруем: только те, что ещё не в заказе
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
            callback_data=f"op_sel_prod_{p['id']}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="op_back_to_products"))
    await callback.message.edit_text("➕ <b>Выберите товар для добавления:</b>", reply_markup=builder.as_markup())
    await state.set_state(OperatorEditOrder.waiting_for_product_add)
    await callback.answer()


@router.callback_query(F.data == "op_back_to_products", OperatorEditOrder.waiting_for_product_add)
async def back_to_products(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку товаров."""
    await edit_products_step(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("op_sel_prod_"), OperatorEditOrder.waiting_for_product_add)
async def add_product_selected(callback: CallbackQuery, state: FSMContext):
    """Добавить выбранный продукт в заказ."""
    product_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    items = list(data.get('items', []))
    available = data.get('available_products', [])

    product = next((p for p in available if p.get('id') == product_id), None)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Добавляем с количеством 1
    items.append({
        'product': product['id'],
        'product_id': product['id'],
        'product_name': product['name'],
        'quantity': 1,
    })
    await state.update_data(items=items)
    await callback.answer(f"✅ {product['name']} добавлен!")
    await edit_products_step(callback, state)


@router.callback_query(F.data == "op_back_to_addr", OperatorEditOrder.waiting_for_product_choice)
async def back_to_address(callback: CallbackQuery, state: FSMContext):
    """Вернуться к шагу выбора адреса."""
    data = await state.get_data()
    saved_addresses = data.get('saved_addresses', [])
    if saved_addresses:
        text = "📍 <b>Выберите адрес доставки</b>"
        kb = build_address_selection_keyboard(saved_addresses)
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад к заказу", callback_data="op_addr_cancel"))
        await callback.message.edit_text(
            "📍 <b>Введите адрес доставки</b>",
            reply_markup=builder.as_markup()
        )
    await state.set_state(OperatorEditOrder.waiting_for_address_choice)
    await callback.answer()


@router.callback_query(F.data == "op_save_edit")
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
    # Возвращаемся к деталям заказа — через повторную загрузку
    from tg_bot.routers.courier import build_pool_order_detail_text as build_detail
    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' not in order_data:
        text = build_detail(order_data)
        builder = InlineKeyboardBuilder()
        if order_data.get('status') == 'PD':
            builder.row(
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"op_edit_{order_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"op_delete_{order_id}"),
            )
        builder.row(InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="op_back_to_pool"))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text("✅ Заказ обновлён!")


# ─── Удаление заказа ──────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("op_delete_"))
async def delete_order_confirm(callback: CallbackQuery):
    """Подтверждение удаления заказа."""
    order_id = int(callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"op_confirm_del_{order_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"order_details_{order_id}"),
    )
    await callback.message.edit_text(
        f"🗑️ <b>Удалить заказ #{order_id}?</b>\n\nЭто действие необратимо.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("op_confirm_del_"))
async def confirm_delete_order(callback: CallbackQuery):
    """Подтверждённое удаление заказа."""
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
    await callback.message.delete()
    await send_pool(tg_id, callback.message)


# ─── В процессе (PENDING заказы, взятые курьерами) ────────────────────────────
@router.message(F.text == "📋 В процессе")
async def show_in_progress(message: Message):
    """Показать список PENDING заказов (взятые курьерами)."""
    tg_id = message.from_user.id
    orders_data = await api_client.get('/operator/orders/?status=PD', headers=auth_headers(tg_id))
    orders = orders_data if isinstance(orders_data, list) else []

    # Фильтруем только те, у которых есть назначенный курьер
    assigned = [o for o in orders if o.get('assigned_courier_name')]

    if not assigned:
        await message.answer("📋 Нет заказов в работе.")
        return

    builder = InlineKeyboardBuilder()
    for order in assigned[:30]:
        hn = order.get('human_number') or f"#{order.get('id')}"
        courier = order.get('assigned_courier_name', '—')
        from tg_bot.keyboards.courier import get_order_address, get_order_freshness_icon
        addr = get_order_address(order)
        addr_short = addr[:20] + ('…' if len(addr) > 20 else '')
        freshness = get_order_freshness_icon(order)
        builder.row(InlineKeyboardButton(
            text=f"{freshness} {hn} | {courier} | {addr_short}",
            callback_data=f"op_progress_{order['id']}"
        ))
    await message.answer(
        f"📋 <b>Заказы в работе:</b> {len(assigned)}\n\nВыберите заказ для просмотра:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("op_progress_"))
async def show_progress_order_detail(callback: CallbackQuery):
    """Показать детали заказа в работе (с курьером)."""
    from tg_bot.routers.courier import build_pool_order_detail_text as build_detail

    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    order_data = await api_client.get(f'/operator/orders/{order_id}/', headers=auth_headers(tg_id))
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return

    # Строим текст: стандартная карточка + курьер
    text = build_detail(order_data)
    courier = order_data.get('assigned_courier_name')
    if courier:
        text += f"\n\n🚚 <b>Курьер:</b> {courier}"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="op_back_to_progress"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "op_back_to_progress")
async def back_to_progress(callback: CallbackQuery):
    await callback.message.delete()
    # Создаём фиктивное сообщение для вызова show_in_progress
    await show_in_progress(callback.message)


# ─── Помощь ────────────────────────────────────────────────────────────────────
@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    await message.answer(
        "🆘 <b>Помощь оператора</b>\n\n"
        "• 📦 Заказы — пул свободных заказов\n"
        "• ➕ Создать заказ — создать новый заказ для клиента\n"
        "• 📋 В процессе — заказы, взятые курьерами\n"
        "• 🆘 Помощь — эта подсказка"
    )


# ─── Создание заказа ──────────────────────────────────────────────────────────
@router.message(F.text == "➕ Создать заказ")
async def create_order(message: Message, state: FSMContext):
    """Начать создание заказа (оператор — без выбора оплаты)."""
    from tg_bot.states.courier import CourierCreateOrder
    await state.update_data(is_operator=True)
    await message.answer("Введите номер телефона клиента:\n(формат: +998901234567)")
    await state.set_state(CourierCreateOrder.waiting_for_phone)