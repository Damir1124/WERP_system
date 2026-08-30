"""
Роутер для обработки команд курьера.
Реализует ПОЛНЫЙ интерфейс через кнопки Telegram (гибрид с Mini App):
курьер может выполнить весь цикл (смена → рейс → пул → взять → доставить)
через кнопки, не открывая Mini App. Кнопка «🌐 Mini App» в главном меню
оставляет привычный Web App рабочим.
"""
import asyncio
import logging
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from tg_bot.keyboards.courier import (
    get_courier_main_keyboard,
    get_pool_inline_keyboard,
    get_order_details_keyboard,
    get_deliver_orders_inline_keyboard,
    get_order_water_qty,
    get_shifts_list_keyboard,
    get_shift_detail_keyboard,
    get_trip_detail_keyboard,
    get_couriers_list_keyboard,
    get_courier_orders_keyboard,
)
from tg_bot.api_client import api_client
from tg_bot.messages import MSG_POOL_LEGEND
from tg_bot.states.courier import CourierTripStart, CourierDeliverOrder, CourierCreateOrder
logger = logging.getLogger(__name__)
router = Router(name="courier")

# ─── Кэш данных «Смены и рейсы» ───────────────────────────────────────────────
# При открытии истории загружаем данные один раз и храним по tg_id,
# чтобы при навигации (смена → рейс → заказ) не делать лишние API-запросы.
_shifts_cache: dict[int, list] = {}
# ─── Кэш данных «Курьеры» ─────────────────────────────────────────────────────
# Для навигации курьеры → заказы курьера → детали заказа.
_couriers_cache: dict[int, list] = {}

# ─── Вспомогательные функции ──────────────────────────────────────────────────


def auth_headers(tg_id: int) -> dict:
    return {'X-Telegram-ID': str(tg_id)}


async def get_trip_state(tg_id: int) -> dict:
    """Текущее состояние смены/рейса курьера."""
    return await api_client.get('/courier/trip/current/', headers=auth_headers(tg_id))


async def show_main_menu(message: Message, tg_id: int):
    """Показать адаптивное главное меню в зависимости от состояния."""
    data = await get_trip_state(tg_id)
    has_shift = data.get('active_shift', False)
    has_trip = data.get('active_trip', False)
    kb = get_courier_main_keyboard(has_shift=has_shift, has_trip=has_trip)
    await message.answer("📋 <b>Главное меню курьера</b>", reply_markup=kb)


def fmt_money(value) -> str:
    try:
        return f"{int(value):,}".replace(',', ' ')
    except (TypeError, ValueError):
        return "0"

# ─── Старт ────────────────────────────────────────────────────────────────────
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start для курьера."""
    tg_id = message.from_user.id
    await show_main_menu(message, tg_id)

# ─── Создать заказ ─────────────────────────────────────────────────────────────
@router.message(F.text == "➕ Создать заказ")
async def create_order_from_main_menu(message: Message, state: FSMContext):
    """Начать создание заказа из главного меню."""
    from tg_bot.routers.courier_create_order import create_order_start
    # Создаём фиктивный callback, чтобы переиспользовать существующий обработчик
    await message.answer("Введите номер телефона клиента:\n(формат: +998901234567)")
    await state.set_state(CourierCreateOrder.waiting_for_phone)


# ─── Открыть смену ─────────────────────────────────────────────────────────────
@router.message(F.text == "🟢 Открыть смену")
async def open_shift(message: Message):
    tg_id = message.from_user.id
    result = await api_client.post('/shifts/', headers=auth_headers(tg_id))
    if 'error' in result:
        await message.answer(f"❌ Ошибка: {result.get('error')}")
        return
    shift = result.get('shift', {})
    await message.answer(
        f"✅ Смена #{shift.get('id')} открыта!\n"
        f"📅 Дата: {shift.get('date')}\n\n"
        f"Теперь загрузите машину и нажмите «🚀 Начать рейс»."
    )
    await show_main_menu(message, tg_id)

# ─── Начать рейс (FSM: ввод количества баклажек) ───────────────────────────────
@router.message(F.text == "🚀 Начать рейс")
async def start_trip(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🚚 <b>Начало рейса</b>\n\n"
        "Сколько полных баклажек загружено в машину?\n"
        "Отправьте число (например: 50):"
    )
    await state.set_state(CourierTripStart.waiting_for_full_loaded)
@router.message(CourierTripStart.waiting_for_full_loaded, F.text.regexp(r'^\d+$'))
async def trip_full_loaded(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    full_loaded = int(message.text)
    result = await api_client.post(
        '/trips/',
        data={'full_loaded': full_loaded},
        headers=auth_headers(tg_id)
    )
    await state.clear()
    if 'error' in result:
        await message.answer(f"❌ Ошибка: {result.get('error')}")
        return
    trip = result.get('trip', {})
    transferred = result.get('transferred_orders', 0)
    text = (
        f"🚚 Рейс #{trip.get('id')} начат!\n"
        f"Загружено: {full_loaded} шт."
    )
    if transferred:
        text += f"\n🔄 Перенесено незавершённых заказов: {transferred}"
    await message.answer(text)
    await show_main_menu(message, tg_id)
@router.message(CourierTripStart.waiting_for_full_loaded, F.text.in_({"Отмена", "🚀 Начать рейс"}))
async def trip_full_loaded_cancel(message: Message, state: FSMContext):
    """Отмена начала рейса (по «❌ Отмена» или повторному нажатию «🚀 Начать рейс»)."""
    await state.clear()
    await message.answer("❌ Начало рейса отменено.")
    await show_main_menu(message, message.from_user.id)


@router.message(CourierTripStart.waiting_for_full_loaded)
async def trip_full_loaded_invalid(message: Message, state: FSMContext):
    await message.answer(
        "❌ Введите число (количество полных баклажек). Например: 50\n"
        "Или отправьте «❌ Отмена» для выхода."
    )

# ─── Пул заказов ───────────────────────────────────────────────────────────────
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
    text = build_pool_text(orders, colleagues)
    kb = get_pool_inline_keyboard(orders)
    await target.answer(text, reply_markup=kb)


@router.message(F.text.in_({"📦 Заказы", "📦 Пул заказов"}))
async def show_pool(message: Message):
    await send_pool(message.from_user.id, message)


# ─── В процессе — курьеры → их заказы (всегда доступно) ────────────────────────
@router.message(F.text == "📋 В процессе")
async def show_in_progress(message: Message):
    """Показать список курьеров для просмотра их заказов."""
    tg_id = message.from_user.id
    colleagues_data = await api_client.get('/courier/colleagues/', headers=auth_headers(tg_id))
    couriers = colleagues_data if isinstance(colleagues_data, list) else []
    if not couriers:
        await message.answer("📋 Нет активных курьеров.")
        return
    _couriers_cache[tg_id] = couriers
    text = "👥 <b>Курьеры на смене:</b>\n\nВыберите курьера, чтобы увидеть его заказы:"
    kb = get_couriers_list_keyboard(couriers)
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("courier_orders_"))
async def show_courier_orders(callback: CallbackQuery):
    """Показать PENDING заказы выбранного курьера."""
    tg_id = callback.from_user.id
    courier_id = int(callback.data.split("_")[2])
    couriers = _couriers_cache.get(tg_id, [])
    courier = next((c for c in couriers if c['id'] == courier_id), None)
    name = courier.get('full_name', f"Курьер #{courier_id}") if courier else f"Курьер #{courier_id}"
    
    orders_data = await api_client.get(f'/courier/pool/?courier_id={courier_id}', headers=auth_headers(tg_id))
    orders = orders_data if isinstance(orders_data, list) else []
    if not orders:
        await callback.message.edit_text(f"👤 <b>{name}</b>\n\nНет заказов в работе.")
        await callback.answer()
        return
    
    text = f"👤 <b>{name}</b>\n📦 Заказов в работе: {len(orders)}\n\nВыберите заказ:"
    kb = get_courier_orders_keyboard(orders, courier_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("courier_order_detail_"))
async def show_courier_order_detail(callback: CallbackQuery):
    """Показать детали заказа из списка заказов курьера."""
    # callback_data = "courier_order_detail_{courier_id}_{order_id}"
    parts = callback.data.split("_")
    courier_id = int(parts[3])
    order_id = int(parts[4])
    tg_id = callback.from_user.id
    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return
    text = build_pool_order_detail_text(order_data)
    # Кнопка «⬅️ Назад к заказам» — возвращает к списку заказов этого курьера
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к заказам", callback_data=f"courier_orders_{courier_id}")
    ]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "back_to_couriers")
async def back_to_couriers(callback: CallbackQuery):
    """Назад к списку курьеров."""
    tg_id = callback.from_user.id
    couriers = _couriers_cache.get(tg_id, [])
    if not couriers:
        await callback.answer("Данные устарели.", show_alert=True)
        return
    text = "👥 <b>Курьеры на смене:</b>\n\nВыберите курьера, чтобы увидеть его заказы:"
    kb = get_couriers_list_keyboard(couriers)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


def build_pool_text(orders: list, colleagues: list) -> str:
    """Текст сообщения «Пул заказов»: итоги + список курьеров на смене."""
    total_orders = len(orders)
    total_water = sum(get_order_water_qty(o) for o in orders)
    lines = [
        f"Всего заказов - {total_orders}",
        f"Всего воды - {total_water}",
        "",
        MSG_POOL_LEGEND,
    ]
    for c in colleagues:
        lines.append(format_courier_line(c))
    return "\n".join(lines)


def format_courier_line(c: dict) -> str:
    """Строка курьера в пуле: [вода в машине] | [нужно воды] [выполнено] [в ожидании] Имя телефон."""
    water_in_car = c.get('water_in_car', 0)
    water_needed = c.get('water_needed', 0)
    completed = c.get('orders_completed', 0)
    pending = c.get('orders_pending', 0)
    name = c.get('full_name', '—')
    phone = c.get('phone', '')
    return (
        f"{water_in_car} | {water_needed:>2}  {completed:>2}  {pending:>2}  "
        f"{name} {phone}".rstrip()
    )
@router.callback_query(F.data.startswith("order_details_"))
async def show_order_details(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    order_data = await api_client.get(f'/courier/pool/{order_id}/', headers=auth_headers(tg_id))
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return
    text = build_pool_order_detail_text(order_data)
    await callback.message.edit_text(text, reply_markup=get_order_details_keyboard(order_id))


def build_pool_order_detail_text(order: dict) -> str:
    """Карточка заказа из пула (как раскрытая OrderCard в Mini App)."""
    from datetime import datetime
    items = order.get('items', [])
    items_text = "\n".join(
        f"   • {it.get('product_name', 'N/A')} × {it.get('quantity', 0)} шт."
        for it in items
    ) or "   —"
    from tg_bot.keyboards.courier import get_order_address
    addr = get_order_address(order)
    lat = order.get('delivery_latitude')
    lon = order.get('delivery_longitude')
    # Кликабельная ссылка на Яндекс.Карты (pt = долгота,широта)
    loc_link = (
        f'\n      📍 <a href="https://yandex.ru/maps/?pt={lon},{lat}&z=17&l=map">Открыть на Яндекс.Картах</a>'
        if lat and lon else ''
    )
    phone = order.get('client_phone') or ''
    # Нормализуем: если номер без +, добавляем (в БД может храниться в разных форматах)
    if phone and not phone.startswith('+'):
        phone = '+' + phone
    # Кликабельный номер телефона
    phone_text = f'\n      📞 {phone}' if phone else ''
    # Вместо «X мин. назад» — день месяца и время (ЧЧ:ММ)
    created_at_raw = order.get('created_at')
    if created_at_raw:
        try:
            dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
            time_text = dt.strftime('%d.%m %H:%M')
        except (ValueError, TypeError):
            time_text = str(created_at_raw)[:16]
    else:
        time_text = '—'
    created_by = order.get('created_by') or '—'
    _hn = order.get('human_number') or '#' + str(order.get('id', ''))
    note = order.get('note')
    note_text = f"\n📝 <b>Примечание:</b>\n   {note}\n" if note else ''
    sep = "─" * 15
    return (
        f"📦 <b>Заказ {_hn}</b>\n"
        f"👤 <b>Клиент:</b> {order.get('client_name', 'N/A')}{phone_text}\n"
        f"📍 <b>Адрес:</b> {addr}{loc_link}\n"
        f"{sep}\n"
        f"🚰 <b>Товары:</b>\n{items_text}\n"
        f"{sep}\n"
        f"💰 <b>Сумма:</b> {fmt_money(order.get('total_price'))} сум\n"
        f"💳 <b>Оплата:</b> {order.get('payment_type_display', 'N/A')}\n"
        f"{note_text}"
        f"{sep}\n"
        f"⏰ <b>Создан:</b> {time_text}\n"
        f"👤 <b>Создал:</b> {created_by}"
    )
@router.callback_query(F.data.startswith("take_order_"))
async def take_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    result = await api_client.post(
        f'/courier/pool/{order_id}/assign/',
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="back_to_pool")
    ]])
    await callback.message.edit_text(
        f"✅ Заказ взят в работу!\nОткройте «🚚 Мой рейс» для просмотра.",
        reply_markup=kb
    )
    await callback.answer("Готово!")
@router.callback_query(F.data == "back_to_pool")
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

# ─── Мой рейс ──────────────────────────────────────────────────────────────────
async def send_current_trip(tg_id: int, target: Message):
    """Показать текущий рейс в target.

    tg_id передаётся явно, т.к. при callback-запросах target.from_user —
    это бот, а не пользователь.
    """
    trip_data = await get_trip_state(tg_id)
    if not trip_data.get('active_shift'):
        await target.answer("🌅 Смена не открыта. Начните с «🟢 Открыть смену».")
        return
    if not trip_data.get('active_trip'):
        return
    trip = trip_data.get('trip', {})
    summary = trip_data.get('summary', {})
    text = (
        f"🚚 <b>Рейс #{trip.get('id')}</b> (в пути)\n"
        f"{'=' * 32}\n"
        f"Загружено: {summary.get('full_loaded', 0)} шт.\n"
        f"Доставлено: {summary.get('delivered', 0)} шт.\n"
        f"Остаток в машине: {summary.get('full_remain', 0)} шт.\n"
        f"Пустых в машине: {summary.get('empty_expected', 0)} шт.\n"
        f"Брак: {summary.get('defective_received', 0)} шт.\n"
        f"{'=' * 32}\n"
        f"💵 Наличными: {fmt_money(summary.get('cash_expected'))} сум\n"
        f"💳 Картой: {fmt_money(summary.get('card_expected'))} сум"
    )
    # Показываем только заказы в статусе 'в пути' (PD), доставленные (DL) скрываем
    orders = [o for o in trip.get('orders', []) if o.get('status') != 'DL']
    buttons = []
    for order in orders:
        label = build_trip_order_label(order)
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"trip_order_{order['id']}")])
    buttons.append([InlineKeyboardButton(text="🏁 Закрыть рейс", callback_data="close_trip")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await target.answer(text, reply_markup=kb)


@router.message(F.text == "🚚 Мой рейс")
async def show_current_trip(message: Message):
    await send_current_trip(message.from_user.id, message)


def build_trip_order_label(order: dict) -> str:
    """Метка кнопки заказа в рейсе: номер | кол-во | адрес/локация."""
    order_id = order.get('id')
    items = order.get('items', [])
    total_qty = sum(it.get('quantity', 0) for it in items)
    from tg_bot.keyboards.courier import get_order_address
    addr = get_order_address(order)
    addr_short = (addr[:24] + '…') if len(addr) > 24 else addr
    status_icon = '✅' if order.get('status') == 'DL' else '⏳'
    label = order.get('human_number', f'#{order_id}')
    from tg_bot.keyboards.courier import get_order_freshness_icon
    freshness = get_order_freshness_icon(order)
    return f"{status_icon} {freshness} {label} | {total_qty} | {addr_short}"


def build_order_detail_text(order: dict) -> str:
    """Подробная карточка заказа (как в Mini App)."""
    items = order.get('items', [])
    items_text = "\n".join([
        f"   • {it.get('product_name', 'N/A')} × {it.get('quantity', 0)} шт."
        for it in items
    ]) or "   —"
    from datetime import datetime
    created_at_raw = order.get('created_at')
    if created_at_raw:
        try:
            dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
            time_text = dt.strftime('%d.%m %H:%M')
        except (ValueError, TypeError):
            time_text = str(created_at_raw)[:16]
    else:
        time_text = 'неизвестно'
    _hn = order.get('human_number') or '#' + str(order.get('id', ''))
    from tg_bot.keyboards.courier import get_order_address
    _addr = get_order_address(order)
    lat = order.get('delivery_latitude')
    lon = order.get('delivery_longitude')
    # Кликабельная ссылка на Яндекс.Карты (pt = долгота,широта)
    loc_link = (
        f'\n      📍 <a href="https://yandex.ru/maps/?pt={lon},{lat}&z=17&l=map">Открыть на Яндекс.Картах</a>'
        if lat and lon else ''
    )
    phone = order.get('client_phone') or ''
    if phone and not phone.startswith('+'):
        phone = '+' + phone
    phone_text = f'\n      📞 {phone}' if phone else ''
    note = order.get('note')
    note_text = f"\n📝 <b>Примечание:</b>\n   {note}\n" if note else ''
    created_by = order.get('created_by') or '—'
    sep = "─" * 15
    return (
        f"📦 <b>Заказ {_hn}</b>\n"
        f"👤 <b>Клиент:</b> {order.get('client_name', 'N/A')}{phone_text}\n"
        f"📍 <b>Адрес:</b> {_addr}{loc_link}\n"
        f"{sep}\n"
        f"🚰 <b>Товары:</b>\n{items_text}\n"
        f"{sep}\n"
        f"💰 <b>Сумма:</b> {fmt_money(order.get('total_price'))} сум\n"
        f"💳 <b>Оплата:</b> {order.get('payment_type_display', 'N/A')}\n"
        f"{note_text}"
        f"{sep}\n"
        f"⏰ <b>Создан:</b> {time_text}\n"
        f"👤 <b>Создал:</b> {created_by}"
    )
@router.callback_query(F.data.startswith("trip_order_"))
async def trip_order_detail(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    trip_data = await get_trip_state(tg_id)
    order = next(
        (o for o in trip_data.get('trip', {}).get('orders', []) if o.get('id') == order_id),
        None
    )
    if not order:
        await callback.answer("Заказ не найден в рейсе", show_alert=True)
        return
    buttons = [
        [InlineKeyboardButton(text="✅ Доставить", callback_data=f"deliver_order_{order_id}")],
        [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"trip_cancel_{order_id}")],
        [InlineKeyboardButton(text="↩️ Вернуть в пул", callback_data=f"return_order_{order_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_trip")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(build_order_detail_text(order), reply_markup=kb)
@router.callback_query(F.data.startswith("trip_cancel_"))
async def trip_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    result = await api_client.post(
        '/courier/orders/confirm/',
        data={'order_id': order_id, 'confirmed': False},
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return
    await callback.answer("❌ Заказ отменён")
    await send_current_trip(tg_id, callback.message)
@router.callback_query(F.data.startswith("return_order_"))
async def return_order_to_pool(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    result = await api_client.post(
        f'/courier/pool/{order_id}/return/',
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return
    await callback.answer("✅ Возвращено в пул")
    await send_current_trip(tg_id, callback.message)
@router.callback_query(F.data == "close_trip")
async def close_trip(callback: CallbackQuery):
    """Показать подтверждение закрытия рейса со статистикой."""
    tg_id = callback.from_user.id
    trip_data = await get_trip_state(tg_id)
    if not trip_data.get('active_trip'):
        await callback.answer("Нет активного рейса", show_alert=True)
        return
    trip = trip_data.get('trip', {})
    summary = trip_data.get('summary', {})
    
    cash_expected = summary.get('cash_expected', 0)
    card_expected = summary.get('card_expected', 0)
    total_expected = cash_expected + card_expected
    full_loaded = summary.get('full_loaded', 0)
    delivered = summary.get('delivered', 0)
    full_remain = summary.get('full_remain', 0)
    empty_received = summary.get('empty_received', 0) or summary.get('empty_expected', 0)
    
    text = (
        f"🏁 <b>Закрытие рейса #{trip.get('id')}</b>\n"
        f"{'=' * 28}\n"
        f"📦 <b>Баклажки</b>\n"
        f"   Загружено: {full_loaded} бак\n"
        f"   Доставлено: {delivered} бак\n"
        f"   Остаток: {full_remain} бак\n"
        f"\n📭 <b>Тара</b>\n"
        f"   Пустых собрано: {empty_received} шт\n"
        f"\n💰 <b>Финансы</b>\n"
        f"   💵 Наличные: {fmt_money(cash_expected)} сум\n"
        f"   💳 Карта: {fmt_money(card_expected)} сум\n"
        f"   {'=' * 20}\n"
        f"   <b>Итого: {fmt_money(total_expected)} сум</b>\n"
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Подтвердите закрытие рейса:"
    )
    buttons = [
        [InlineKeyboardButton(text="✅ Закрыть рейс", callback_data="confirm_close_trip")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_close_trip")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "confirm_close_trip")
async def confirm_close_trip(callback: CallbackQuery):
    """Подтвердить и выполнить закрытие рейса."""
    tg_id = callback.from_user.id
    trip_data = await get_trip_state(tg_id)
    if not trip_data.get('active_trip'):
        await callback.answer("Рейс уже закрыт", show_alert=True)
        return
    trip = trip_data.get('trip', {})
    result = await api_client.post(
        f'/courier/trips/{trip.get("id")}/close/',
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return
    msg = result.get('message', f"Рейс #{trip.get('id')} закрыт.")
    pending = result.get('pending_transferred', 0)
    if pending > 0:
        msg += f"\n\n📦 {pending} заказов будут автоматически перенесены, когда вы откроете следующий рейс."
    await callback.message.edit_text(f"🏁 {msg}")
    # Возвращаемся в главное меню — курьер сам решит, открывать ли новый рейс
    await show_main_menu(callback.message, tg_id)
    await callback.answer()


@router.callback_query(F.data == "cancel_close_trip")
async def cancel_close_trip(callback: CallbackQuery):
    """Отмена закрытия рейса — возврат к текущему рейсу."""
    tg_id = callback.from_user.id
    await send_current_trip(tg_id, callback.message)
    await callback.answer()
@router.callback_query(F.data == "back_to_trip")
async def back_to_trip(callback: CallbackQuery):
    tg_id = callback.from_user.id
    await callback.message.delete()
    await send_current_trip(tg_id, callback.message)

# ─── Подтверждение доставки (FSM) ──────────────────────────────────────────────
@router.message(F.text == "✅ Подтвердить доставку")
async def show_deliver_menu(message: Message):
    tg_id = message.from_user.id
    trip_data = await get_trip_state(tg_id)
    if not trip_data.get('active_trip'):
        await message.answer("🚚 Нет активного рейса. Начните рейс, чтобы подтверждать доставку.")
        return
    orders = trip_data.get('trip', {}).get('orders', [])
    pending = [o for o in orders if o.get('status') == 'PD']
    if not pending:
        await message.answer("✅ В текущем рейсе нет заказов, ожидающих доставки.")
        return
    kb = get_deliver_orders_inline_keyboard(pending)
    await message.answer(
        f"✅ Выберите заказ для подтверждения доставки ({len(pending)}):",
        reply_markup=kb
    )
@router.callback_query(F.data.startswith("deliver_order_"))
async def deliver_order_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    trip_data = await get_trip_state(tg_id)
    if not trip_data.get('active_trip'):
        await callback.answer("Нет активного рейса", show_alert=True)
        return
    order = next((o for o in trip_data.get('trip', {}).get('orders', []) if o.get('id') == order_id), None)
    if not order:
        await callback.answer("Заказ не найден в рейсе", show_alert=True)
        return
    edit = init_deliver_edit(order)
    # Загружаем список продуктов для возможности добавления новых позиций
    products_data = await api_client.get('/products/', headers=auth_headers(tg_id))
    all_products = products_data if isinstance(products_data, list) else []
    await state.update_data(
        order_id=order_id,
        order=order,
        edit=edit,
        extra_items=[],       # [{product_id, product_name, price, quantity}]
        all_products=all_products,
    )
    await state.set_state(CourierDeliverOrder.waiting_for_edit)
    await show_deliver_edit(callback.message, order, edit, extra_items=[])
    await callback.answer()
WATER_TYPES = ('19W', 'B19W')


def is_water_item(item: dict) -> bool:
    return item.get('product_type') in WATER_TYPES


def init_deliver_edit(order: dict) -> dict:
    """Структура редактирования: {item_id: {quantity, exchange_qty, sell_with_qty, defective_qty}}."""
    edit = {}
    for it in order.get('items', []):
        qty = it.get('quantity', 0)
        if is_water_item(it):
            edit[it['id']] = {
                'quantity': qty,
                'exchange_qty': qty,   # по умолчанию = заказано (бэкенд требует != 0)
                'sell_with_qty': 0,
                'defective_qty': 0,
            }
        else:
            edit[it['id']] = {
                'quantity': qty,
                'exchange_qty': 0,
                'sell_with_qty': 0,
                'defective_qty': 0,
            }
    return edit


def build_deliver_edit_text(order: dict, edit: dict, extra_items: list = None) -> str:
    _hn = order.get('human_number') or '#' + str(order.get('id', ''))
    lines = [f"📦 <b>Редактирование доставки — Заказ {_hn}</b>\n"]
    note = order.get('note')
    if note:
        lines.append(f"<b>Примечание:</b> {note}\n")
    for it in order.get('items', []):
        iid = it['id']
        st = edit.get(iid, {})
        if is_water_item(it):
            lines.append(
                f"💧 {it.get('product_name')} (заказано {st.get('quantity', 0)})\n"
                f"   🔄 обмен: {st.get('exchange_qty', 0)} | "
                f"💰 с тарой: {st.get('sell_with_qty', 0)} | "
                f"⚠️ брак: {st.get('defective_qty', 0)}"
            )
        else:
            lines.append(f"🛒 {it.get('product_name')}: {st.get('quantity', 0)} шт.")
    # Добавленные товары
    extra = extra_items or []
    if extra:
        lines.append("")
        for idx, ei in enumerate(extra):
            lines.append(f"➕ {ei.get('product_name')}: {ei.get('quantity', 0)} шт. × {fmt_money(ei.get('price', 0))}")
    lines.append("\n✏️ Измените количество и операции с тарой, затем подтвердите.")
    return "\n".join(lines)


def get_deliver_edit_keyboard(order: dict, edit: dict, extra_items: list = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for it in order.get('items', []):
        iid = it['id']
        if is_water_item(it):
            builder.row(
                InlineKeyboardButton(text="➖ обмен", callback_data=f"d_ex_{iid}_m"),
                InlineKeyboardButton(text="➕ обмен", callback_data=f"d_ex_{iid}_p"),
            )
            builder.row(
                InlineKeyboardButton(text="➖ с тарой", callback_data=f"d_sw_{iid}_m"),
                InlineKeyboardButton(text="➕ с тарой", callback_data=f"d_sw_{iid}_p"),
            )
            builder.row(
                InlineKeyboardButton(text="➖ брак", callback_data=f"d_df_{iid}_m"),
                InlineKeyboardButton(text="➕ брак", callback_data=f"d_df_{iid}_p"),
            )
        else:
            builder.row(
                InlineKeyboardButton(text="➖ кол-во", callback_data=f"d_qty_{iid}_m"),
                InlineKeyboardButton(text="➕ кол-во", callback_data=f"d_qty_{iid}_p"),
            )
    # Кнопки для добавленных товаров
    extra = extra_items or []
    for idx, ei in enumerate(extra):
        builder.row(
            InlineKeyboardButton(text=f"➖ {ei.get('product_name', '')[:12]}", callback_data=f"d_extra_{idx}_m"),
            InlineKeyboardButton(text=f"➕ {ei.get('product_name', '')[:12]}", callback_data=f"d_extra_{idx}_p"),
        )
    # Кнопка "Добавить товар"
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="d_add_product"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить доставку", callback_data="d_confirm"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="d_cancel"),
    )
    return builder.as_markup()


async def show_deliver_edit(target, order: dict, edit: dict, extra_items: list = None):
    extra = extra_items or []
    text = build_deliver_edit_text(order, edit, extra_items=extra)
    kb = get_deliver_edit_keyboard(order, edit, extra_items=extra)
    if hasattr(target, 'edit_text'):
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


def adjust_edit(edit: dict, item_id: int, field: str, delta: int) -> str:
    """Изменяет поле позиции с валидацией. Возвращает '' или текст ошибки."""
    st = edit.get(item_id)
    if not st:
        return "Позиция не найдена"
    val = st.get(field, 0) + delta
    if field == 'quantity':
        if val < 1:
            return "Количество не может быть меньше 1"
        if val > 999:
            return "Слишком большое количество"
    elif field == 'exchange_qty':
        if val < 1:
            return "Обмен тары не может быть меньше 1"
        if val > 999:
            return "Слишком большой обмен"
    elif field == 'sell_with_qty':
        if val < 0:
            return "Продажа с тарой не может быть отрицательной"
        if val > st.get('exchange_qty', 0):
            return "Продажа с тарой не может превышать обмен"
    elif field == 'defective_qty':
        if val < 0:
            return "Брак не может быть отрицательным"
        if val > 999:
            return "Слишком большой брак"
    st[field] = val
    return ""
@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data.startswith("d_qty_"))
async def deliver_edit_qty(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    delta = 1 if callback.data.endswith("_p") else -1
    data = await state.get_data()
    err = adjust_edit(data['edit'], item_id, 'quantity', delta)
    if err:
        await callback.answer(err, show_alert=True)
        return
    await state.update_data(edit=data['edit'])
    await show_deliver_edit(callback.message, data['order'], data['edit'], extra_items=data.get('extra_items'))
    await callback.answer()
@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data.startswith("d_ex_"))
async def deliver_edit_ex(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    delta = 1 if callback.data.endswith("_p") else -1
    data = await state.get_data()
    err = adjust_edit(data['edit'], item_id, 'exchange_qty', delta)
    if err:
        await callback.answer(err, show_alert=True)
        return
    await state.update_data(edit=data['edit'])
    await show_deliver_edit(callback.message, data['order'], data['edit'], extra_items=data.get('extra_items'))
    await callback.answer()
@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data.startswith("d_sw_"))
async def deliver_edit_sw(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    delta = 1 if callback.data.endswith("_p") else -1
    data = await state.get_data()
    err = adjust_edit(data['edit'], item_id, 'sell_with_qty', delta)
    if err:
        await callback.answer(err, show_alert=True)
        return
    await state.update_data(edit=data['edit'])
    await show_deliver_edit(callback.message, data['order'], data['edit'], extra_items=data.get('extra_items'))
    await callback.answer()
@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data.startswith("d_df_"))
async def deliver_edit_df(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    delta = 1 if callback.data.endswith("_p") else -1
    data = await state.get_data()
    err = adjust_edit(data['edit'], item_id, 'defective_qty', delta)
    if err:
        await callback.answer(err, show_alert=True)
        return
    await state.update_data(edit=data['edit'])
    await show_deliver_edit(callback.message, data['order'], data['edit'], extra_items=data.get('extra_items'))
    await callback.answer()
@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data == "d_add_product")
async def deliver_add_product_list(callback: CallbackQuery, state: FSMContext):
    """Показать список доступных продуктов для добавления."""
    data = await state.get_data()
    all_products = data.get('all_products', [])
    order = data.get('order', {})
    extra_items = data.get('extra_items', [])
    
    # ID продуктов уже в заказе или добавленных
    existing_ids = set()
    for it in order.get('items', []):
        existing_ids.add(it.get('product_id') or it.get('product'))
    for ei in extra_items:
        existing_ids.add(ei.get('product_id'))
    
    # Фильтруем: только те, что ещё не в заказе
    available = [p for p in all_products if p.get('id') not in existing_ids]
    
    if not available:
        await callback.answer("Нет доступных товаров для добавления", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for p in available:
        name = p.get('name', 'Товар')
        price = p.get('price', 0)
        btn_text = f"{name} — {fmt_money(price)} сум"
        builder.add(InlineKeyboardButton(text=btn_text, callback_data=f"d_sel_product_{p['id']}"))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="d_back_to_edit"))
    
    await callback.message.edit_text(
        "➕ <b>Выберите товар для добавления:</b>",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data == "d_back_to_edit")
async def deliver_back_to_edit(callback: CallbackQuery, state: FSMContext):
    """Вернуться к редактированию доставки."""
    data = await state.get_data()
    await show_deliver_edit(
        callback.message, data['order'], data['edit'],
        extra_items=data.get('extra_items')
    )
    await callback.answer()


@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data.startswith("d_sel_product_"))
async def deliver_add_product_select(callback: CallbackQuery, state: FSMContext):
    """Добавить выбранный продукт в extra_items."""
    product_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    all_products = data.get('all_products', [])
    extra_items = list(data.get('extra_items', []))
    
    product = next((p for p in all_products if p.get('id') == product_id), None)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    
    # Добавляем с количеством 1
    extra_items.append({
        'product_id': product['id'],
        'product_name': product['name'],
        'price': product['price'],
        'quantity': 1,
    })
    await state.update_data(extra_items=extra_items)
    await show_deliver_edit(callback.message, data['order'], data['edit'], extra_items=extra_items)
    await callback.answer()


@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data.startswith("d_extra_"))
async def deliver_edit_extra(callback: CallbackQuery, state: FSMContext):
    """Изменить количество добавленного товара."""
    parts = callback.data.split("_")
    idx = int(parts[2])
    delta = 1 if parts[3] == 'p' else -1
    data = await state.get_data()
    extra_items = list(data.get('extra_items', []))
    
    if idx < 0 or idx >= len(extra_items):
        await callback.answer("Позиция не найдена", show_alert=True)
        return
    
    new_qty = extra_items[idx]['quantity'] + delta
    if new_qty < 1:
        # Удаляем позицию если количество стало 0
        extra_items.pop(idx)
    else:
        extra_items[idx]['quantity'] = new_qty
    
    await state.update_data(extra_items=extra_items)
    await show_deliver_edit(callback.message, data['order'], data['edit'], extra_items=extra_items)
    await callback.answer()


@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data == "d_confirm")
async def deliver_edit_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = data['order']
    edit = data['edit']
    extra_items = data.get('extra_items', [])
    tg_id = callback.from_user.id
    items = []
    for it in order.get('items', []):
        iid = it['id']
        st = edit.get(iid, {})
        payload = {
            'item_id': iid,
            'exchange_qty': st.get('exchange_qty', 0),
            'sell_with_qty': st.get('sell_with_qty', 0),
            'defective_qty': st.get('defective_qty', 0),
        }
        if not is_water_item(it):
            payload['quantity'] = st.get('quantity', it.get('quantity', 0))
        items.append(payload)
    
    # Формируем new_items из добавленных товаров
    new_items = [
        {'product_id': ei['product_id'], 'quantity': ei['quantity']}
        for ei in extra_items
    ]
    
    payload = {'order_id': data['order_id'], 'confirmed': True, 'note': '', 'items': items}
    if new_items:
        payload['new_items'] = new_items
    
    result = await api_client.post(
        '/courier/orders/confirm/',
        data=payload,
        headers=auth_headers(tg_id)
    )
    await state.clear()
    if 'error' in result:
        await callback.message.edit_text(f"❌ Ошибка подтверждения: {result.get('error')}")
        await callback.answer()
        return
    await callback.message.edit_text(f"✅ Заказ доставлен!")
    await callback.answer("Готово!")
@router.callback_query(CourierDeliverOrder.waiting_for_edit, F.data == "d_cancel")
async def deliver_edit_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = data['order']
    await state.clear()
    # Возврат к карточке заказа (без отмены самого заказа)
    buttons = [
        [InlineKeyboardButton(text="✅ Доставить", callback_data=f"deliver_order_{order['id']}")],
        [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"trip_cancel_{order['id']}")],
        [InlineKeyboardButton(text="↩️ Вернуть в пул", callback_data=f"return_order_{order['id']}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_trip")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(build_order_detail_text(order), reply_markup=kb)
    await callback.answer()

# ═════════════════════════════════════════════════════════════════════════════
# Смены и рейсы — 3 уровня навигации (смена → рейс → заказ)
# ═════════════════════════════════════════════════════════════════════════════

# ─── Форматирование текста ────────────────────────────────────────────────────

def _build_shift_list_text(shifts: list) -> str:
    """Сводка по всем сменам (стартовый экран)."""
    total_cash = sum(s.get('cash_total') or 0 for s in shifts)
    total_card = sum(s.get('card_total') or 0 for s in shifts)
    total_orders = sum((s.get('stats') or {}).get('orders_count', 0) for s in shifts)
    total_water = sum((s.get('stats') or {}).get('water_delivered', 0) for s in shifts)
    lines = [
        "📋 <b>Смены и рейсы</b>",
        "=" * 28,
        f"📅 Всего смен: {len(shifts)}",
        f"📦 Доставлено: {total_orders} заказов, {total_water} шт воды",
        f"💵 Наличные: {fmt_money(total_cash)} сум",
        f"💳 Карта: {fmt_money(total_card)} сум",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "Выберите смену для просмотра:",
    ]
    return "\n".join(lines)


def _build_shift_detail_text(shift: dict) -> str:
    """Детали одной смены + список рейсов."""
    date = shift.get('date', 'N/A')
    is_open = shift.get('status') == 'OP'
    status = '🟢 ОТКРЫТА' if is_open else '🔴 ЗАКРЫТА'
    cash = shift.get('cash_total') or 0
    card = shift.get('card_total') or 0
    stats = shift.get('stats') or {}
    orders_count = stats.get('orders_count', 0)
    water = stats.get('water_delivered', 0)
    trips = shift.get('trips', [])
    total_trip_delivered = sum(
        (t.get('summary') or {}).get('delivered', 0) for t in trips
    )
    lines = [
        f"📋 <b>Смена {date}</b> ({status})",
        "=" * 28,
        f"💵 Наличные: {fmt_money(cash)} сум",
        f"💳 Карта: {fmt_money(card)} сум",
        f"📦 Воды доставлено: {water} шт",
        f"📋 Заказов выполнено: {orders_count}",
        f"🚚 Рейсов: {len(trips)} (доставлено {total_trip_delivered} шт)",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "Рейсы:",
    ]
    return "\n".join(lines)


def _build_trip_detail_text(trip: dict) -> str:
    """Детали одного рейса + список заказов."""
    trip_id = trip.get('id')
    is_active = trip.get('status') == 'AC'
    status = '🟢 ACTIVE' if is_active else '🔵 DONE'
    summary = trip.get('summary', {})
    full_loaded = summary.get('full_loaded', trip.get('full_loaded', 0))
    delivered = summary.get('delivered', 0)
    full_remain = summary.get('full_remain', 0)
    empty_in_car = summary.get('empty_in_car', 0)
    defect_qty = summary.get('defect_qty', 0)
    orders = trip.get('orders', [])
    lines = [
        f"🚚 <b>Рейс #{trip_id}</b> ({status})",
        "=" * 28,
        f"📦 Загружено: {full_loaded} шт",
        f"✅ Доставлено: {delivered} шт",
        f"📦 Остаток: {full_remain} шт",
        f"🔄 Пустых: {empty_in_car} шт",
        f"⚠️ Брак: {defect_qty} шт",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Заказы ({len(orders)}):" if orders else "Заказов нет",
    ]
    return "\n".join(lines)


# ─── Уровень 0: Список смен (стартовый экран) ────────────────────────────────

@router.message(F.text == "📋 Смены и рейсы")
async def show_shifts_history(message: Message):
    tg_id = message.from_user.id
    shifts_data = await api_client.get('/shifts/history/', headers=auth_headers(tg_id))
    current = await get_trip_state(tg_id)
    if 'error' in shifts_data or not isinstance(shifts_data, list) or not shifts_data:
        await message.answer("📋 История смен пуста.")
        return
    # Показываем только последние 10 смен
    shifts_data = shifts_data[:10]
    # Кэшируем данные для последующей навигации
    _shifts_cache[tg_id] = shifts_data
    text = _build_shift_list_text(shifts_data)
    has_active = current.get('active_shift', False)
    kb = get_shifts_list_keyboard(shifts_data, has_active_shift=has_active)
    await message.answer(text, reply_markup=kb)


# ─── Уровень 1: Детали смены ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("shift_detail_"))
async def show_shift_detail(callback: CallbackQuery):
    tg_id = callback.from_user.id
    shift_id = int(callback.data.split("_")[2])
    shifts = _shifts_cache.get(tg_id, [])
    shift = next((s for s in shifts if s['id'] == shift_id), None)
    if not shift:
        await callback.answer("Данные устарели. Откройте «Смены и рейсы» заново.", show_alert=True)
        return
    text = _build_shift_detail_text(shift)
    trips = shift.get('trips', [])
    kb = get_shift_detail_keyboard(trips, shift_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ─── Уровень 2: Детали рейса ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("trip_detail_"))
async def show_trip_detail(callback: CallbackQuery):
    tg_id = callback.from_user.id
    trip_id = int(callback.data.split("_")[2])
    shifts = _shifts_cache.get(tg_id, [])
    # Ищем рейс во всех сменах
    trip = None
    shift_id = None
    for s in shifts:
        for t in s.get('trips', []):
            if t['id'] == trip_id:
                trip = t
                shift_id = s['id']
                break
        if trip:
            break
    if not trip:
        await callback.answer("Данные устарели. Откройте «Смены и рейсы» заново.", show_alert=True)
        return
    text = _build_trip_detail_text(trip)
    orders = trip.get('orders', [])
    kb = get_trip_detail_keyboard(orders, shift_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ─── Уровень 3: Детали заказа (из рейса) ─────────────────────────────────────

@router.callback_query(F.data.startswith("order_info_"))
async def show_order_info(callback: CallbackQuery):
    """Показать детали заказа из рейса (только для просмотра)."""
    tg_id = callback.from_user.id
    order_id = int(callback.data.split("_")[2])
    shifts = _shifts_cache.get(tg_id, [])
    # Ищем заказ во всех сменах/рейсах
    order = None
    shift_id = None
    for s in shifts:
        for t in s.get('trips', []):
            for o in t.get('orders', []):
                if o['id'] == order_id:
                    order = o
                    shift_id = s['id']
                    break
            if order:
                break
        if order:
            break
    if not order:
        await callback.answer("Данные устарели. Откройте «Смены и рейсы» заново.", show_alert=True)
        return

    status = order.get('status')
    icon = '🟢' if status == 'DL' else ('🔴' if status == 'CN' else '🟡')
    status_label = {'DL': 'Доставлен', 'CN': 'Отменён'}.get(status, 'В работе')
    items = order.get('items', [])
    items_text = "\n".join(
        f"   • {it.get('product_name', 'N/A')} × {it.get('quantity', 0)}"
        for it in items
    ) or "   Нет позиций"
    pay_icon = {'CD': '💳', 'BS': '🎁'}.get(order.get('payment_type'), '💵')
    _hn = order.get('human_number') or '#' + str(order.get('id', ''))
    lines = [
        f"📦 <b>Заказ {_hn}</b> {icon}",
        "=" * 28,
        f"👤 Клиент: {order.get('client_name') or 'Клиент не указан'}",
        f"🚰 Товары:\n{items_text}",
        f"💰 Сумма: {fmt_money(order.get('total_price'))} сум",
        f"{pay_icon} Оплата: {order.get('payment_type')}",
        f"📊 Статус: {status_label}",
    ]
    note = order.get('note')
    if note:
        lines.append(f"Примечание: {note}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к рейсу", callback_data=f"back_to_shift_{shift_id}")
    ]])
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


# ─── Навигация: назад ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_shifts")
async def back_to_shifts_list(callback: CallbackQuery):
    """Назад к списку смен."""
    tg_id = callback.from_user.id
    shifts = _shifts_cache.get(tg_id, [])
    if not shifts:
        await callback.answer("Данные устарели. Откройте заново.", show_alert=True)
        return
    text = _build_shift_list_text(shifts)
    current = await get_trip_state(tg_id)
    has_active = current.get('active_shift', False)
    kb = get_shifts_list_keyboard(shifts, has_active_shift=has_active)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_shift_"))
async def back_to_shift(callback: CallbackQuery):
    """Назад к деталям смены."""
    tg_id = callback.from_user.id
    # callback_data = "back_to_shift_5" → split = ['back','to','shift','5'] → берём последний элемент
    shift_id = int(callback.data.rsplit("_", 1)[1])
    shifts = _shifts_cache.get(tg_id, [])
    shift = next((s for s in shifts if s['id'] == shift_id), None)
    if not shift:
        await callback.answer("Данные устарели. Откройте заново.", show_alert=True)
        return
    text = _build_shift_detail_text(shift)
    trips = shift.get('trips', [])
    kb = get_shift_detail_keyboard(trips, shift_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
@router.callback_query(F.data == "close_shift")
async def close_shift(callback: CallbackQuery):
    """Показать подтверждение закрытия смены со статистикой (как ShiftClose.jsx)."""
    tg_id = callback.from_user.id
    current = await get_trip_state(tg_id)
    if not current.get('active_shift'):
        await callback.answer("Смена уже закрыта", show_alert=True)
        return
    if current.get('active_trip'):
        await callback.answer("❌ Сначала закройте активный рейс", show_alert=True)
        return
    shift_id = current.get('shift_id')
    # Загружаем статистику смены
    shift_data = await api_client.get('/shifts/current/', headers=auth_headers(tg_id))
    shift_info = shift_data.get('shift', {}) if isinstance(shift_data, dict) else {}
    shift_stats = shift_data.get('shift_stats', {}) if isinstance(shift_data, dict) else {}

    cash_total = shift_info.get('cash_total', 0)
    card_total = shift_info.get('card_total', 0)
    total_amount = cash_total + card_total
    water_delivered = shift_stats.get('water_delivered', 0)
    orders_count = shift_stats.get('orders_count', 0)
    date = shift_info.get('date', 'N/A')

    reminder = "\n💵 Не забудьте сдать наличные!\n" if cash_total > 0 else "\n"
    text = (
        f"📋 <b>Закрытие смены #{shift_id}</b>\n"
        f"{'=' * 28}\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"\n📦 <b>Статистика доставки</b>\n"
        f"   Воды доставлено: {water_delivered} бак\n"
        f"   Заказов выполнено: {orders_count} шт\n"
        f"\n💰 <b>Финансы</b>\n"
        f"   💵 Наличные: {fmt_money(cash_total)} сум\n"
        f"   💳 Карта: {fmt_money(card_total)} сум\n"
        f"   {'=' * 20}\n"
        f"   <b>Итого: {fmt_money(total_amount)} сум</b>\n"
        f"{reminder}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Подтвердите закрытие:"
    )
    buttons = [
        [InlineKeyboardButton(text="✅ Закрыть смену", callback_data="confirm_close_shift")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_close_shift")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "confirm_close_shift")
async def confirm_close_shift(callback: CallbackQuery):
    """Подтвердить и выполнить закрытие смены."""
    tg_id = callback.from_user.id
    current = await get_trip_state(tg_id)
    if not current.get('active_shift'):
        await callback.answer("Смена уже закрыта", show_alert=True)
        return
    shift_id = current.get('shift_id')
    result = await api_client.post(
        f'/courier/shifts/{shift_id}/close/',
        headers=auth_headers(tg_id)
    )
    if 'error' in result:
        await callback.answer(f"❌ {result.get('error')}", show_alert=True)
        return
    await callback.message.edit_text(f"🔒 Смена #{shift_id} закрыта.")
    await show_main_menu(callback.message, tg_id)
    await callback.answer()


@router.callback_query(F.data == "cancel_close_shift")
async def cancel_close_shift(callback: CallbackQuery):
    """Отмена закрытия смены."""
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()

# ─── Коллеги ───────────────────────────────────────────────────────────────────
@router.message(F.text == "👥 Коллеги")
async def show_colleagues(message: Message):
    tg_id = message.from_user.id
    colleagues_data = await api_client.get('/courier/colleagues/', headers=auth_headers(tg_id))
    if 'error' in colleagues_data or not colleagues_data:
        await message.answer("👥 Коллег на смене нет.")
        return
    online = [c for c in colleagues_data if c.get('is_online')]
    text = f"👥 <b>Коллеги на смене ({len(online)}):</b>\n\n"
    for c in colleagues_data:
        status = "🟢" if c.get('is_online') else "⚪️"
        text += (
            f"{status} {c.get('full_name', 'N/A')}\n"
            f"   💧 В машине: {c.get('water_in_car', 0)} | Нужно: {c.get('water_needed', 0)}\n"
            f"   ✅ Доставлено: {c.get('orders_completed', 0)} | ⏳ В работе: {c.get('orders_pending', 0)}\n"
            f"   📞 {c.get('phone', 'N/A')}\n\n"
        )
    await message.answer(text)

# ─── Скрытая команда: сводка по адресам (агрегация) ───────────────────────────
# Команда НЕ выводится в меню и доступна только курьеру (фильтр role в bot.py).
# Курьер вводит её вручную, чтобы увидеть агрегацию своих взятых заказов
# по адресу общежития (блок → этаж, общее кол-во воды на этаж).
@router.message(Command("сводка"))
@router.message(Command("agg"))
async def cmd_address_summary(message: Message):
    tg_id = message.from_user.id
    data = await api_client.get('/courier/orders/aggregate/', headers=auth_headers(tg_id))
    if 'error' in data:
        await message.answer(f"❌ Ошибка: {data.get('error')}")
        return

    groups = data.get('groups', [])
    unparsed = data.get('unparsed', [])

    if not groups and not unparsed:
        await message.answer("📦 Сводка по адресам\n\nНет взятых заказов в активном рейсе.")
        return

    lines = ["📦 <b>Сводка по адресам</b>", ""]
    for g in groups:
        lines.append(f"🏢 <b>Блок {g['block']}</b>")
        lines.append(f"   {g['floor']} этаж — {g['water_qty']} шт")
        for room in g.get('rooms', []):
            lines.append(f"      комната {room['room']} — {room['water_qty']} шт")
        lines.append("")

    text = "\n".join(lines).rstrip()

    if unparsed:
        text += (
            "\n\n⚠️ <b>Без адреса (не агрегированы):</b> "
            f"{len(unparsed)} зак.\nНажмите на заказ, чтобы посмотреть адрес:"
        )
        kb = get_pool_inline_keyboard(unparsed)
        await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text)


# ─── Помощь ────────────────────────────────────────────────────────────────────
@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    await message.answer(
        "🆘 <b>Помощь курьера</b>\n\n"
        "• 🟢 Открыть смену — начать рабочий день\n"
        "• 🚀 Начать рейс — загрузить машину и начать развоз\n"
        "• 📦 Заказы — пул свободных заказов, взять в работу\n"
        "• 📋 В процессе — курьеры и их взятые заказы\n"
        "• ➕ Создать заказ — создать новый заказ для клиента\n"
        "• 🚚 Мой рейс — статистика рейса, список заказов, закрытие\n"
        "• ✅ Подтвердить доставку — отметить заказ доставленным\n"
        "• 📋 Смены и рейсы — история смен, рейсов, заказов\n"
        "• 🆘 Помощь — эта подсказка"
    )
