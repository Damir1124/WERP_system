"""
Роутер для обработки команд курьера.
Реализует интерфейс через кнопки Telegram согласно спецификации.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from tg_bot.keyboards.courier import get_courier_main_keyboard
from tg_bot.api_client import api_client

logger = logging.getLogger(__name__)

router = Router(name="courier")


@router.message(Command("start"))
async def cmd_start(message: Message, user: dict = None):
    """Обработка команды /start для курьера."""
    user_data = message.from_user
    logger.info(f"Курьер {user_data.id} запустил бота")
    
    role = user.get('role', 'unknown') if user else 'unknown'
    name = user.get('name', user_data.first_name) if user else user_data.first_name
    
    await message.answer(
        f"Привет, {name}!\n"
        f"Вы авторизованы как {'администратор' if role == 'admin' else 'курьер'}.\n\n"
        f"Используйте меню ниже для работы:",
        reply_markup=get_courier_main_keyboard()
    )


@router.message(F.text == "📦 Пул заказов")
async def show_pool(message: Message):
    """Показать пул заказов со статистикой коллег."""
    tg_id = message.from_user.id
    
    # Получаем статистику коллег
    colleagues_data = await api_client.get(
        '/courier/colleagues/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    # Получаем список заказов из пула
    pool_data = await api_client.get(
        '/courier/pool/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    if 'error' in colleagues_data or 'error' in pool_data:
        await message.answer(
            "Ошибка загрузки данных. Попробуйте позже.",
            reply_markup=get_courier_main_keyboard()
        )
        return
    
    # Формируем шапку со статистикой коллег
    header = "📊 Курьеры на смене:\n\n"
    header += "💧 💧 ✅ ⏳\n"
    header += "Остаток | Нужно  Вып  Проц  Имя Телефон\n"
    header += "=" * 50 + "\n"
    
    colleagues = colleagues_data if isinstance(colleagues_data, list) else []
    for colleague in colleagues:
        trip = colleague.get('current_trip', {})
        header += (
            f"{trip.get('full_remain', 0):2d}      | "
            f"{trip.get('total_needed', 0):2d}      "
            f"{trip.get('delivered_count', 0):2d}   "
            f"{trip.get('pending_count', 0):2d}    "
            f"{colleague.get('courier_name', 'N/A')} "
            f"{colleague.get('phone', '')}\n"
        )
    
    header += "\n💧 - Остаток в машине | Всего нужно\n"
    header += "✅ - Выполнено\n"
    header += "⏳ - В процессе\n\n"
    header += "=" * 50 + "\n\n"
    
    # Формируем кнопки заказов
    orders = pool_data if isinstance(pool_data, list) else []
    buttons = []
    
    for order in orders[:20]:  # Максимум 20 заказов
        # API возвращает client_address, а не client.address
        address = order.get('client_address', 'N/A')
        address_short = address[:30] if len(address) > 30 else address
        
        # Считаем общее количество товаров
        items = order.get('items', [])
        total_qty = sum(item.get('quantity', 0) for item in items)
        
        button_text = f"#{order['id']} | {total_qty} | {address_short}"
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"order_details_{order['id']}"
        )])
    
    # Кнопка создания заказа
    buttons.append([InlineKeyboardButton(
        text="➕ Создать новый заказ",
        callback_data="create_order_start"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if orders:
        await message.answer(
            header + f"📦 Доступные заказы ({len(orders)}):",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            header + "Пул заказов пуст.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➕ Создать новый заказ", callback_data="create_order_start")
            ]])
        )


@router.callback_query(F.data.startswith("order_details_"))
async def show_order_details(callback: CallbackQuery):
    """Показать детали заказа из пула."""
    order_id = int(callback.data.split("_")[2])
    
    # Получаем детали заказа
    order_data = await api_client.get(f'/courier/pool/{order_id}/')
    
    if 'error' in order_data:
        await callback.answer("❌ Ошибка загрузки заказа", show_alert=True)
        return
    
    items = order_data.get('items', [])
    
    # Формируем список товаров
    items_text = "\n".join([
        f"• {item.get('product_name', 'N/A')} x {item.get('quantity', 0)} sht."
        for item in items
    ])
    
    # Вычисляем время с создания
    minutes_ago = order_data.get('minutes_ago', 0)
    time_text = f"{minutes_ago} минут назад" if minutes_ago < 60 else f"{minutes_ago // 60} часов назад"
    
    text = (
        f"📦 Заказ #{order_id}\n\n"
        f"👤 Клиент: {order_data.get('client_name', 'N/A')}\n"
        f"📞 Телефон: {order_data.get('client_phone', 'N/A')}\n"
        f"📍 Адрес: {order_data.get('client_address', 'N/A')}\n\n"
        f"🚰 Товары:\n{items_text}\n\n"
        f"💰 Сумма: {order_data.get('total_price', 0):,} сум\n"
        f"💳 Оплата: {order_data.get('payment_type_display', 'N/A')}\n\n"
        f"⏰ Создан: {time_text}"
    )
    
    buttons = [
        [InlineKeyboardButton(text="✅ Взять заказ", callback_data=f"take_order_{order_id}")],
        [InlineKeyboardButton(text="⬅️ Назад в пул", callback_data="back_to_pool")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("take_order_"))
async def take_order(callback: CallbackQuery):
    """Взять заказ в свой рейс."""
    order_id = int(callback.data.split("_")[2])
    tg_id = callback.from_user.id
    
    # Назначаем заказ курьеру
    result = await api_client.post(
        f'/courier/pool/{order_id}/assign/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    if 'error' in result:
        await callback.answer(f"Oshibka: {result.get('error')}", show_alert=True)
    else:
        await callback.message.edit_text(
            f"Zakaz #{order_id} dobavlen v vash reys!\n\n"
            f"Ispolzuyte 'Moy reys' dlya prosmotra."
        )
        await callback.answer("Uspeshno!")


@router.callback_query(F.data == "back_to_pool")
async def back_to_pool(callback: CallbackQuery):
    """Вернуться к списку заказов пула."""
    # Просто вызываем show_pool через сообщение
    await callback.message.delete()
    await show_pool(callback.message)


@router.message(F.text == "🚚 Мой рейс")
async def show_current_trip(message: Message):
    """Показать текущий активный рейс."""
    tg_id = message.from_user.id
    
    trip_data = await api_client.get(
        '/courier/trip/current/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    if 'error' in trip_data:
        await message.answer(
            "U vas net aktivnogo reysa.\n"
            "Otkroyte smenu i nachните reys.",
            reply_markup=get_courier_main_keyboard()
        )
        return
    
    text = (
        f"Reys #{trip_data.get('id', 'N/A')} (aktivnyy)\n"
        f"{'=' * 40}\n"
        f"Zagruzheno: {trip_data.get('full_loaded', 0)} sht.\n"
        f"Dostavleno: {trip_data.get('delivered_count', 0)} zakazov ({trip_data.get('delivered_qty', 0)} sht.)\n"
        f"Ostatok v mashine: {trip_data.get('full_remain', 0)} sht.\n"
        f"Pustykh v mashine: {trip_data.get('empty_in_car', 0)} sht.\n"
        f"Brak: {trip_data.get('defect_qty', 0)} sht.\n"
        f"{'=' * 40}\n"
        f"Nalichnykh dolzhno byt: {trip_data.get('cash_expected', 0):,} sum\n"
        f"Po karte: {trip_data.get('card_expected', 0):,} sum\n"
        f"{'=' * 40}\n"
    )
    
    buttons = [
        [InlineKeyboardButton(text="Spisok zakazov reysa", callback_data="trip_orders")],
        [InlineKeyboardButton(text="Zakryt reys", callback_data="close_trip")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "📋 Смены и рейсы")
async def show_shifts_history(message: Message):
    """История смен и рейсов."""
    tg_id = message.from_user.id
    
    shifts_data = await api_client.get(
        '/shifts/history/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    if 'error' in shifts_data or not shifts_data:
        await message.answer("Net istorii smen.")
        return
    
    text = "Istoriya vashikh smen (poslednie 5):\n\n"
    
    shifts = shifts_data if isinstance(shifts_data, list) else []
    for shift in shifts[:5]:
        status = "OTKRYTA" if shift.get('status') == 'OPEN' else "ZAKRYTA"
        text += (
            f"{shift.get('date', 'N/A')} | {status}\n"
            f"Nalichnye: {shift.get('cash_total', 0):,} | "
            f"Karta: {shift.get('card_total', 0):,}\n\n"
        )
    
    await message.answer(text)


@router.message(F.text == "👥 Коллеги")
async def show_colleagues(message: Message):
    """Показать список коллег с открытыми сменами."""
    tg_id = message.from_user.id
    
    colleagues_data = await api_client.get(
        '/courier/colleagues/',
        headers={'X-Telegram-ID': str(tg_id)}
    )
    
    if 'error' in colleagues_data or not colleagues_data:
        await message.answer("Net kolleg na smene.")
        return
    
    text = "Vashi kollegi na smene segodnya:\n\n"
    
    colleagues = colleagues_data if isinstance(colleagues_data, list) else []
    for colleague in colleagues:
        trip = colleague.get('current_trip', {})
        text += (
            f"{colleague.get('courier_name', 'N/A')}\n"
            f"Dostavok: {trip.get('delivered_count', 0)}\n"
            f"Tel: {colleague.get('phone', 'N/A')}\n\n"
        )
    
    await message.answer(text)


@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показать справку для курьера."""
    await message.answer(
        "Pomoshch po komandam kuryera:\n\n"
        "• Pul zakazov - spisok zakazov, kotorye mozhno vzyat\n"
        "• Moy reys - detali tekushchego reysa i schetchiki\n"
        "• Smeny i reysy - istoriya vashikh smen\n"
        "• Kollegi - kto segodnya na smene\n\n"
        "Dlya sozdaniya zakaza ispolzuyte knopku v pule zakazov."
    )
