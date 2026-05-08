"""
Роутер для обработки команд курьера.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_bot.keyboards.courier import (
    get_courier_main_keyboard,
    get_shift_actions_keyboard,
    get_trip_actions_keyboard,
    get_order_confirmation_keyboard,
    get_pool_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="courier")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start для курьера."""
    user_data = message.from_user
    logger.info(f"Курьер {user_data.id} запустил бота")
    
    # Проверяем роль через middleware (должна быть в data['user'])
    # Но middleware ещё не отработал? Он отработает перед хэндлером.
    # Просто приветствуем
    await message.answer(
        f"👋 Привет, {user_data.first_name}!\n"
        "Вы авторизованы как курьер.\n"
        "Используйте меню ниже для работы.",
        reply_markup=get_courier_main_keyboard()
    )


@router.message(F.text == "📦 Пул заказов")
async def show_pool(message: Message):
    """Показать пул заказов."""
    # TODO: запрос к API для получения пула заказов
    await message.answer(
        "🔄 Загружаю пул заказов...\n"
        "Пока что здесь будет список заказов, ожидающих назначения.",
        reply_markup=get_pool_keyboard()
    )


@router.message(F.text == "🚚 Мой рейс")
async def show_current_trip(message: Message):
    """Показать текущий активный рейс."""
    # TODO: запрос к API /api/bot/courier/trip/current/
    await message.answer(
        "📊 Информация о текущем рейсе:\n"
        "• Загружено полных: 20\n"
        "• Доставлено: 12\n"
        "• Остаток в машине: 8\n"
        "• Пустых в машине: 5\n"
        "• Брак: 1\n"
        "• Наличных должно быть: 150 000 сум\n"
        "• По карте должно быть: 80 000 сум",
        reply_markup=get_trip_actions_keyboard()
    )


@router.message(F.text == "📋 Смены и рейсы")
async def show_shifts_history(message: Message):
    """История смен и рейсов."""
    await message.answer(
        "📅 История ваших смен:\n"
        "• 05.05.2026 — OPEN — наличные: 200 000, безнал: 100 000\n"
        "• 04.05.2026 — CLOSED — наличные: 180 000, безнал: 90 000\n"
        "Нажмите на смену для деталей."
    )


@router.message(F.text == "👥 Коллеги")
async def show_colleagues(message: Message):
    """Показать список коллег с открытыми сменами."""
    # TODO: запрос к API /api/bot/courier/colleagues/
    await message.answer(
        "👥 Ваши коллеги на смене сегодня:\n"
        "• Иван Иванов — 15 доставок, тел. +998901234567\n"
        "• Петр Петров — 10 доставок, тел. +998902345678\n"
        "• Сергей Сергеев — 8 доставок, тел. +998903456789"
    )


@router.message(F.text == "🆘 Помощь")
async def show_help(message: Message):
    """Показать справку для курьера."""
    await message.answer(
        "📖 **Помощь по командам курьера:**\n"
        "• *Пул заказов* — список заказов, которые можно взять\n"
        "• *Мой рейс* — детали текущего рейса и счётчики\n"
        "• *Смены и рейсы* — история ваших смен\n"
        "• *Коллеги* — кто сегодня на смене\n"
        "• *Помощь* — это сообщение\n\n"
        "Для открытия Mini App нажмите кнопку «Открыть рабочий стол» в меню бота."
    )


# Callback-хэндлеры для инлайн-кнопок
@router.callback_query(F.data.startswith("order_assign_"))
async def assign_order(callback: CallbackQuery):
    """Взять заказ из пула."""
    order_id = callback.data.split("_")[-1]
    # TODO: POST /api/bot/courier/order/{order_id}/assign/
    await callback.answer(f"Заказ #{order_id} взят в работу")
    await callback.message.edit_text(f"✅ Вы взяли заказ #{order_id}")


@router.callback_query(F.data.startswith("order_confirm_"))
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтвердить доставку заказа."""
    order_id = callback.data.split("_")[-1]
    # Переходим в состояние выбора container_op
    await state.set_state("wait_container_op")
    await state.update_data(order_id=order_id)
    await callback.message.edit_text(
        f"Выберите тип операции с тарой для заказа #{order_id}:",
        reply_markup=get_order_confirmation_keyboard(order_id)
    )


@router.callback_query(F.data.startswith("container_op_"))
async def set_container_op(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора container_op."""
    data = await state.get_data()
    order_id = data.get("order_id")
    op = callback.data.split("_")[-1]
    # TODO: отправить подтверждение доставки с container_op
    await callback.answer(f"Тип операции: {op}")
    await callback.message.edit_text(
        f"✅ Заказ #{order_id} подтверждён с операцией {op}.\n"
        "Склад и финансы обновлены автоматически."
    )
    await state.clear()