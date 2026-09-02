"""
FSM-хэндлеры для создания заказа курьером.
Реализует пошаговый процесс согласно спецификации.
"""
import logging

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Location
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from tg_bot.states.courier import CourierCreateOrder
from apps.bot_bridge.phone_validator import validate_uzbek_phone
from tg_bot.api_client import api_client
from tg_bot.keyboards.courier import get_courier_main_keyboard

logger = logging.getLogger(__name__)

router = Router(name="courier_create_order")


# ─── Шаг 1: Начало создания заказа ───────────────────────────────────────────

@router.callback_query(F.data == "create_order_start")
async def create_order_start(callback: CallbackQuery, state: FSMContext):
    """Начать создание заказа."""
    await callback.message.edit_text(
        "Введите номер телефона клиента:\n"
        "(формат: +998901234567)"
    )
    await state.set_state(CourierCreateOrder.waiting_for_phone)
    await callback.answer()


# ─── Шаг 2: Ввод телефона ────────────────────────────────────────────────────

@router.message(CourierCreateOrder.waiting_for_phone)
async def create_order_phone(message: Message, state: FSMContext):
    """Обработка телефона с валидацией."""
    try:
        validated_phone = validate_uzbek_phone(message.text)
    except ValueError as e:
        await message.answer(f"Ошибка: {str(e)}\n\nПопробуйте ещё раз:")
        return

    await state.update_data(phone=validated_phone)

    # Проверяем, есть ли клиент в БД
    # Используем ?q= (как в frontend OrderCreate.jsx), а не ?phone=
    client_data = await api_client.get(f'/clients/search/?q={validated_phone}')

    if 'error' not in client_data and client_data:
        # Клиент найден — загружаем сохранённые адреса (как в Mini App OrderCreate.jsx)
        await state.update_data(client_exists=True, client_data=client_data)

        addresses_data = await api_client.get(f'/clients/addresses/{validated_phone}/')
        saved_addresses = addresses_data.get('addresses', []) if isinstance(addresses_data, dict) else []

        await state.update_data(saved_addresses=saved_addresses)

        # Строим кнопки: до 3-х сохранённых адресов + "Новый адрес" + "Отмена"
        builder = InlineKeyboardBuilder()
        for addr in saved_addresses:
            label = addr.get('address_text', '').strip()
            if not label and addr.get('latitude') and addr.get('longitude'):
                label = f"📍 {float(addr['latitude']):.4f}, {float(addr['longitude']):.4f}"
            if not label:
                label = f"Адрес #{addr['id']}"
            # Обрезаем до 35 символов, чтобы кнопка не была слишком широкой
            if len(label) > 35:
                label = label[:32] + '...'
            builder.row(InlineKeyboardButton(
                text=f"📍 {label}",
                callback_data=f"select_address_{addr['id']}"
            ))
        builder.row(InlineKeyboardButton(
            text="✍️ Ввести новый адрес",
            callback_data="enter_new_address"
        ))
        builder.row(InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_order_creation"
        ))

        await message.answer(
            f"✅ Клиент найден: {client_data.get('name', 'Нет')}\n\n"
            f"Выберите адрес доставки:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(CourierCreateOrder.waiting_for_address_choice)
    else:
        # Новый клиент
        await state.update_data(client_exists=False, saved_addresses=[])

        # Клавиатура с кнопкой геолокации
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"📝 Новый клиент!\n"
            f"Имя будет создано автоматически: \"{validated_phone[-4:]}\"\n\n"
            f"Введите адрес доставки:\n"
            f"(или отправьте геолокацию)",
            reply_markup=keyboard
        )
        await state.set_state(CourierCreateOrder.waiting_for_address_text)


# ─── Шаг 3: Выбор адреса (для существующего клиента) ─────────────────────────

@router.callback_query(F.data.startswith("select_address_"), CourierCreateOrder.waiting_for_address_choice)
async def select_saved_address(callback: CallbackQuery, state: FSMContext):
    """Выбрать один из сохранённых адресов клиента (ClientAddress)."""
    address_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    saved_addresses = data.get('saved_addresses', [])

    addr = next((a for a in saved_addresses if a.get('id') == address_id), None)
    if not addr:
        await callback.answer("Адрес не найден. Попробуйте ещё раз.", show_alert=True)
        return

    await state.update_data(
        address=addr.get('address_text'),
        latitude=addr.get('latitude'),
        longitude=addr.get('longitude')
    )

    label = addr.get('address_text') or f"📍 {addr.get('latitude')}, {addr.get('longitude')}"
    await callback.message.edit_text(f"✅ Адрес выбран:\n{label}")
    await ask_for_product_quantity(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "enter_new_address", CourierCreateOrder.waiting_for_address_choice)
async def enter_new_address(callback: CallbackQuery, state: FSMContext):
    """Ввести новый адрес."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.edit_text(
        "Введите новый адрес доставки:\n"
        "(или отправьте геолокацию)"
    )
    await callback.message.answer("Жду адрес...", reply_markup=keyboard)
    await state.set_state(CourierCreateOrder.waiting_for_address_text)
    await callback.answer()


# ─── Шаг 4: Ввод адреса (текст или геолокация) ───────────────────────────────

@router.message(CourierCreateOrder.waiting_for_address_text, F.location)
async def create_order_location(message: Message, state: FSMContext):
    """Обработка геолокации."""
    location: Location = message.location

    await state.update_data(
        address="Геолокация",
        latitude=location.latitude,
        longitude=location.longitude
    )

    await message.answer(
        f"✅ Геолокация сохранена!\n"
        f"Координаты: {location.latitude}, {location.longitude}",
        reply_markup=ReplyKeyboardRemove()
    )

    await ask_for_product_quantity(message, state)


@router.message(CourierCreateOrder.waiting_for_address_text, F.text)
async def create_order_address_text(message: Message, state: FSMContext):
    """Обработка текстового адреса."""
    await state.update_data(
        address=message.text,
        latitude=None,
        longitude=None
    )

    await message.answer(
        "✅ Адрес сохранён!",
        reply_markup=ReplyKeyboardRemove()
    )

    await ask_for_product_quantity(message, state)


# ─── Шаг 5: Ввод количества товара ───────────────────────────────────────────

async def ask_for_product_quantity(message: Message, state: FSMContext):
    """Спросить количество воды 19л (по умолчанию)."""
    await message.answer(
        "Сколько баклажек воды 19л?\n"
        "(введите число)"
    )
    await state.set_state(CourierCreateOrder.waiting_for_product_quantity)


@router.message(CourierCreateOrder.waiting_for_product_quantity, F.text.regexp(r'^\d+$'))
async def create_order_quantity(message: Message, state: FSMContext):
    """Обработка количества."""
    quantity = int(message.text)

    if quantity <= 0 or quantity > 100:
        await message.answer("Введите корректное количество (1-100):")
        return

    # Определяем реальный id продукта "Вода 19л" (без хардкода)
    tg_id = message.from_user.id
    products = await api_client.get('/products/', headers={'X-Telegram-ID': str(tg_id)})
    water = None
    if isinstance(products, list):
        water = next((p for p in products if p.get('type_product') == '19W'), None)
        if not water:
            water = next((p for p in products if '19' in p.get('name', '')), None)
    if not water:
        await message.answer("Не удалось найти продукт Вода 19л. Добавьте товар вручную.")
        await show_add_more_keyboard(message, state)
        return

    # Сохраняем первый товар (Вода 19л)
    await state.update_data(items=[{'product_id': water['id'], 'product_name': water['name'], 'quantity': quantity}])

    await show_add_more_keyboard(message, state)


# ─── Шаг 5.5: Добавление дополнительных товаров ─────────────────────────────

async def show_add_more_keyboard(target, state: FSMContext):
    """Показать список товаров в заказе + кнопки «Добавить товар» / «К оплате»."""
    data = await state.get_data()
    items = data.get('items', [])
    items_text = "\n".join([f"• {it['product_name']} x {it['quantity']} шт." for it in items])
    text = (
        f"📦 Товары в заказе:\n{items_text}\n\n"
        f"Добавить ещё товары или перейти к оплате?"
    )
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_more_products")],
        [InlineKeyboardButton(text="➡️ Перейти к оплате", callback_data="proceed_to_payment")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(CourierCreateOrder.waiting_for_add_more_products)


@router.callback_query(F.data == "add_more_products", CourierCreateOrder.waiting_for_add_more_products)
async def add_more_products(callback: CallbackQuery, state: FSMContext):
    """Показать список товаров для добавления."""
    tg_id = callback.from_user.id
    products = await api_client.get('/products/', headers={'X-Telegram-ID': str(tg_id)})
    if 'error' in products or not isinstance(products, list) or not products:
        await callback.answer("Ошибка загрузки товаров", show_alert=True)
        return

    await state.update_data(products=products)
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.row(InlineKeyboardButton(text=p['name'], callback_data=f"select_product_{p['id']}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_add_more"))

    await callback.message.edit_text("Выберите товар:", reply_markup=builder.as_markup())
    await state.set_state(CourierCreateOrder.waiting_for_product_selection)
    await callback.answer()


@router.callback_query(F.data == "back_to_add_more", CourierCreateOrder.waiting_for_product_selection)
async def back_to_add_more(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку товаров заказа."""
    await show_add_more_keyboard(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("select_product_"), CourierCreateOrder.waiting_for_product_selection)
async def select_product(callback: CallbackQuery, state: FSMContext):
    """Выбран товар — запрашиваем количество."""
    product_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    products = data.get('products', [])
    product = next((p for p in products if p['id'] == product_id), None)
    name = product['name'] if product else f"Товар #{product_id}"

    await state.update_data(pending_product={"product_id": product_id, "product_name": name})
    await callback.message.edit_text(f"Введите количество для «{name}»:")
    await state.set_state(CourierCreateOrder.waiting_for_additional_quantity)
    await callback.answer()


@router.message(CourierCreateOrder.waiting_for_additional_quantity, F.text.regexp(r'^\d+$'))
async def add_additional_quantity(message: Message, state: FSMContext):
    """Добавить выбранный товар в заказ (с объединением дубликатов)."""
    quantity = int(message.text)
    if quantity <= 0 or quantity > 100:
        await message.answer("Введите корректное количество (1-100):")
        return

    data = await state.get_data()
    pending = data.get('pending_product')
    items = data.get('items', [])
    if pending:
        for it in items:
            if it['product_id'] == pending['product_id']:
                it['quantity'] += quantity
                break
        else:
            items.append({
                "product_id": pending['product_id'],
                "product_name": pending['product_name'],
                "quantity": quantity
            })
        await state.update_data(items=items)

    await show_add_more_keyboard(message, state)


# ─── Шаг 6: Выбор типа оплаты ─────────────────────────────────────────────────

@router.callback_query(F.data == "proceed_to_payment", CourierCreateOrder.waiting_for_add_more_products)
async def proceed_to_payment(callback: CallbackQuery, state: FSMContext):
    """Перейти к выбору типа оплаты или сразу к подтверждению (для оператора)."""
    data = await state.get_data()
    # Если оператор (флаг is_operator=true) — пропускаем выбор оплаты, ставим Наличные
    if data.get('is_operator'):
        await state.update_data(payment_type='CASH')
        await show_order_confirmation(callback.message, state)
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(text="💵 Наличные", callback_data="payment_CASH")],
        [InlineKeyboardButton(text="💳 Карта", callback_data="payment_CARD")],
        [InlineKeyboardButton(text="🎁 Бонусы", callback_data="payment_BONUS")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        "Способ оплаты?",
        reply_markup=keyboard
    )
    await state.set_state(CourierCreateOrder.waiting_for_payment_type)
    await callback.answer()


@router.callback_query(F.data.startswith("payment_"), CourierCreateOrder.waiting_for_payment_type)
async def select_payment_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа оплаты."""
    payment_type = callback.data.split("_")[1]
    await state.update_data(payment_type=payment_type)

    # Показываем подтверждение
    await show_order_confirmation(callback.message, state)
    await callback.answer()


# ─── Шаг 7: Подтверждение и создание заказа ──────────────────────────────────

async def show_order_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение заказа."""
    data = await state.get_data()

    phone = data.get('phone')
    address = data.get('address')
    items = data.get('items', [])
    payment_type = data.get('payment_type')

    # Формируем текст товаров
    items_text = "\n".join([f"• {item['product_name']} x {item['quantity']} шт." for item in items])

    payment_display = {
        'CASH': 'Наличные',
        'CARD': 'Карта',
        'BONUS': 'Бонусы'
    }.get(payment_type, payment_type)

    if data.get('client_exists') and data.get('client_data'):
        client_label = data['client_data'].get('name', phone)
    else:
        client_label = f"{phone[-4:]} (новый)"

    text = (
        f"Подтверждение заказа:\n\n"
        f"Клиент: {client_label}\n"
        f"Телефон: {phone}\n"
        f"Адрес: {address}\n\n"
        f"Товары:\n{items_text}\n\n"
        f"Оплата: {payment_display}"
    )

    buttons = [
        [InlineKeyboardButton(text="✅ Создать заказ", callback_data="confirm_create_order")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order_creation")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(CourierCreateOrder.waiting_for_confirmation)


@router.callback_query(F.data == "confirm_create_order", CourierCreateOrder.waiting_for_confirmation)
async def confirm_create_order(callback: CallbackQuery, state: FSMContext):
    """Создать заказ."""
    data = await state.get_data()
    tg_id = callback.from_user.id

    # Отправляем запрос на создание заказа (product_name не нужен бэкенду)
    items_payload = [
        {"product_id": it["product_id"], "quantity": it["quantity"]}
        for it in data.get('items', [])
    ]
    # Маппинг в формат, ожидаемый бэкендом (CourierCreateOrderView)
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
        headers={'X-Telegram-ID': str(tg_id)}
    )

    if 'error' in result:
        await callback.message.edit_text(
            f"❌ Ошибка создания заказа:\n{result.get('error')}\n\n"
            f"Попробуйте ещё раз."
        )
    else:
        order_id = result.get('order_id', 'N/A')

        # ─── Сохраняем адрес в историю клиента (как в OrderCreate.jsx) ────────
        # Для существующего клиента используем client_data.id,
        # для нового — id из ответа бэкенда: result['client']['id']
        client_id_for_address = (
            (data.get('client_data') or {}).get('id')
            or (result.get('client') or {}).get('id')
        )
        address = data.get('address')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if client_id_for_address and (address or latitude or longitude):
            try:
                await api_client.post('/clients/addresses/save/', data={
                    'client_id': client_id_for_address,
                    'address_text': address or '',
                    'latitude': latitude or None,
                    'longitude': longitude or None
                })
            except Exception as e:
                logger.warning(f"Не удалось сохранить адрес клиента #{client_id_for_address}: {e}")

        # Редактируем inline-сообщение (без кнопок, т.к. FSM завершён)
        display_num = result.get('display_number')
        display_text = f"{display_num:03d}" if display_num is not None else f'#{order_id}'
        await callback.message.edit_text(
            f"✅ Заказ {display_text} создан!"
        )

    # Показываем адаптивное главное меню в зависимости от роли
    is_operator = (data or {}).get('is_operator')
    if is_operator:
        from tg_bot.keyboards.operator import get_operator_main_keyboard
        kb = get_operator_main_keyboard()
        await callback.message.answer("📋 <b>Главное меню оператора</b>", reply_markup=kb)
    else:
        trip_data = await api_client.get('/courier/trip/current/', headers={'X-Telegram-ID': str(tg_id)})
        has_shift = trip_data.get('active_shift', False)
        has_trip = trip_data.get('active_trip', False)
        kb = get_courier_main_keyboard(has_shift=has_shift, has_trip=has_trip)
        await callback.message.answer("📋 <b>Главное меню курьера</b>", reply_markup=kb)

    await state.clear()
    await callback.answer("Готово!")


@router.callback_query(F.data == "cancel_order_creation")
async def cancel_order_creation(callback: CallbackQuery, state: FSMContext):
    """Отменить создание заказа."""
    # Проверяем, был ли это оператор
    state_data = await state.get_data()
    was_operator = state_data.get('is_operator')
    await state.clear()
    await callback.message.edit_text("❌ Создание заказа отменено.")
    if was_operator:
        from tg_bot.keyboards.operator import get_operator_main_keyboard
        kb = get_operator_main_keyboard()
        await callback.message.answer("📋 <b>Главное меню оператора</b>", reply_markup=kb)
    else:
        tg_id = callback.from_user.id
        data = await api_client.get('/courier/trip/current/', headers={'X-Telegram-ID': str(tg_id)})
        has_shift = data.get('active_shift', False)
        has_trip = data.get('active_trip', False)
        kb = get_courier_main_keyboard(has_shift=has_shift, has_trip=has_trip)
        await callback.message.answer("📋 <b>Главное меню курьера</b>", reply_markup=kb)
    await callback.answer()
