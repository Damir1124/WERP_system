"""
Роутер для обработки команд клиента.
Все взаимодействия — через кнопки Telegram, без Mini App.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from tg_bot.api_client import api_client
from tg_bot.keyboards.client import get_client_main_keyboard

logger = logging.getLogger(__name__)

router = Router(name="client")


# ─── Команда /start ────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, user: dict = None):
    """Обработка команды /start для клиента."""
    tg_user = message.from_user
    name = (user or {}).get('name') or tg_user.first_name

    await message.answer(
        f"👋 Здравствуйте, {name}!\n\n"
        f"💧 <b>Osnova 2.0</b> — доставка питьевой воды\n\n"
        f"Нажмите «🛒 Заказать воду», чтобы сделать заказ:",
        reply_markup=get_client_main_keyboard(),
        parse_mode='HTML'
    )


# ─── Мои заказы ────────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мои заказы")
async def show_my_orders(message: Message, user: dict = None):
    """Показать историю заказов клиента (текстом, без Mini App)."""
    tg_id = (user or {}).get('tg_id') or message.from_user.id
    await message.answer("⏳ Загружаю ваши заказы...")

    orders = await api_client.get('/client/orders/', params={'tg_id': tg_id})

    if 'error' in orders:
        await message.answer("❌ Не удалось загрузить заказы. Попробуйте позже.")
        return

    if not orders or not isinstance(orders, list) or len(orders) == 0:
        await message.answer(
            "📦 <b>У вас пока нет заказов.</b>\n\n"
            "Нажмите «🛒 Заказать воду», чтобы сделать первый заказ!",
            parse_mode='HTML'
        )
        return

    # Показываем последние 5 заказов
    for order in orders[:5]:
        status_icon = {
            'PD': '⏳',
            'DL': '✅',
            'CN': '❌',
        }.get(order.get('status', ''), '❓')

        status_text = order.get('status_display', 'Неизвестно')

        # Позиции заказа
        items_text = ''
        for item in order.get('items', []):
            items_text += f"  • {item.get('product_name', 'Товар')} × {item.get('quantity', 0)} — {item.get('price', 0):,} сум\n"

        address = order.get('delivery_address_text') or 'не указан'

        await message.answer(
            f"{status_icon} <b>Заказ #{order['id']}</b>\n"
            f"📌 Статус: {status_text}\n"
            f"📍 Адрес: {address}\n"
            f"🚰 Позиции:\n{items_text}"
            f"💰 Итого: {order.get('total_price', 0):,} сум\n"
            f"💳 Оплата: {order.get('payment_type_display', '')}\n"
            f"⏰ Создан: {order.get('created_at', '')[:10]}",
            parse_mode='HTML'
        )

    if len(orders) > 5:
        await message.answer(f"📄 Показано 5 последних заказов из {len(orders)}.")


# ─── Мой адрес ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📍 Мой адрес")
async def show_my_address(message: Message, user: dict = None):
    """Показать профиль клиента."""
    tg_id = (user or {}).get('tg_id') or message.from_user.id

    profile = await api_client.get('/client/profile/', params={'tg_id': tg_id})

    if 'error' in profile:
        await message.answer("❌ Не удалось загрузить профиль. Попробуйте позже.")
        return

    name = profile.get('name', 'Не указано')
    phone = profile.get('phone') or 'не указан'
    address = profile.get('address') or 'не указан'

    # Пытаемся получить сохранённые адреса
    saved_addresses = []
    if phone and phone != 'не указан':
        addr_data = await api_client.get(f'/clients/addresses/{phone}/')
        if isinstance(addr_data, dict) and 'addresses' in addr_data:
            saved_addresses = addr_data['addresses']

    msg = (
        f"🏠 <b>Ваш профиль:</b>\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📍 Адрес: {address}\n"
    )

    if saved_addresses:
        msg += "\n📋 <b>Сохранённые адреса:</b>\n"
        for i, addr in enumerate(saved_addresses[:3], 1):
            addr_text = addr.get('address_text') or f"📍 {addr.get('latitude')}, {addr.get('longitude')}"
            msg += f"  {i}. {addr_text}\n"

    await message.answer(msg, parse_mode='HTML')


# ─── Помощь ────────────────────────────────────────────────────────────────────

@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показать справку для клиента."""
    await message.answer(
        "📖 <b>Помощь:</b>\n\n"
        "🛒 <b>Заказать воду</b> — пошаговое оформление заказа\n"
        "📋 <b>Мои заказы</b> — история и статусы заказов\n"
        "📍 <b>Мой адрес</b> — ваш профиль и адреса\n\n"
        "По вопросам обращайтесь к оператору.",
        parse_mode='HTML'
    )
