"""
Роутер для обработки команд администратора.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tg_bot.keyboards.admin import (
    get_admin_main_keyboard,
    get_stats_keyboard,
    get_shifts_keyboard,
    get_stock_alerts_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="admin")


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start для администратора."""
    user_data = message.from_user
    logger.info(f"Администратор {user_data.id} запустил бота")
    
    await message.answer(
        f"👋 Добро пожаловать, {user_data.first_name}!\n"
        "Вы авторизованы как администратор.\n"
        "Используйте команды для мониторинга системы.",
        reply_markup=get_admin_main_keyboard()
    )


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика сегодня")
async def cmd_stats(message: Message):
    """Статистика за сегодня."""
    # TODO: запрос к API /api/bot/admin/stats/today/
    await message.answer(
        "📊 **Сводка за 07.05.2026**\n"
        "━━━━━━━━━━━━━━━━\n"
        "💰 Доход: 1 250 000 сум\n"
        "📉 Расход: 180 000 сум\n"
        "✅ Прибыль: 1 070 000 сум\n"
        "💳 Безнал: 320 000 сум\n"
        "━━━━━━━━━━━━━━━━\n"
        "🚚 Активных смен: 3\n"
        "📦 Заказов выполнено: 47",
        reply_markup=get_stats_keyboard()
    )


@router.message(Command("shifts"))
@router.message(F.text == "🚚 Активные смены")
async def cmd_shifts(message: Message):
    """Список активных смен сегодня."""
    # TODO: запрос к API /api/bot/admin/shifts/
    await message.answer(
        "🚚 **Активные смены сегодня:**\n"
        "1. Иван Иванов — наличные: 200 000, безнал: 100 000, заказов: 15\n"
        "2. Петр Петров — наличные: 150 000, безнал: 80 000, заказов: 10\n"
        "3. Сергей Сергеев — наличные: 120 000, безнал: 60 000, заказов: 8",
        reply_markup=get_shifts_keyboard()
    )


@router.message(Command("stock"))
@router.message(F.text == "📦 Склад (алерты)")
async def cmd_stock(message: Message):
    """Алерты по складу (остатки < 10)."""
    # TODO: запрос к API /api/bot/admin/stock/alerts/
    await message.answer(
        "⚠️ **Критические остатки на складе:**\n"
        "• Тара 20л — остаток: 5 шт.\n"
        "• Помпа для бутыли — остаток: 3 шт.\n"
        "• Крышки — остаток: 8 шт.",
        reply_markup=get_stock_alerts_keyboard()
    )


@router.message(Command("orders"))
@router.message(F.text == "📋 Последние заказы")
async def cmd_orders(message: Message):
    """Последние 10 заказов."""
    # TODO: запрос к API /api/bot/admin/orders/recent/
    await message.answer(
        "📋 **Последние 10 заказов:**\n"
        "1. #105 — Клиент: Алиев, Вода 20л × 2, 50 000 сум, 🚚 В пути\n"
        "2. #104 — Клиент: Петров, Кулер × 1, 1 200 000 сум, ✅ Доставлен\n"
        "3. #103 — Клиент: Сидоров, Вода 20л × 1, 25 000 сум, ✅ Доставлен"
    )


@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показать справку для администратора."""
    await message.answer(
        "📖 **Помощь по командам администратора:**\n"
        "• /stats или «Статистика сегодня» — финансовая сводка\n"
        "• /shifts или «Активные смены» — список смен курьеров\n"
        "• /stock или «Склад (алерты)» — критические остатки\n"
        "• /orders или «Последние заказы» — последние заказы\n"
        "• «Помощь» — это сообщение"
    )


# Callback-хэндлеры
@router.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    """Обновить статистику."""
    await callback.answer("Обновляю статистику...")
    await cmd_stats(callback.message)


@router.callback_query(F.data == "refresh_shifts")
async def refresh_shifts(callback: CallbackQuery):
    """Обновить список смен."""
    await callback.answer("Обновляю список смен...")
    await cmd_shifts(callback.message)


@router.callback_query(F.data == "refresh_stock")
async def refresh_stock(callback: CallbackQuery):
    """Обновить алерты склада."""
    await callback.answer("Обновляю остатки...")
    await cmd_stock(callback.message)