"""
Инициализация бота и диспетчера.
Подключает middleware, routers и настраивает логику обработки сообщений.
"""
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.config import BOT_TOKEN, LOG_LEVEL, MINI_APP_URL
from tg_bot.middlewares.auth import AuthMiddleware
from tg_bot.routers import courier, client, admin
from tg_bot.routers import courier_create_order

# Настройка логирования
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Инициализация бота с default properties
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Хранилище состояний (пока используем MemoryStorage, для продакшена нужно RedisStorage)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключаем middleware
dp.update.middleware(AuthMiddleware())

# ─── Роутер для незарегистрированных пользователей ───────────────────────────

unknown_router = Router(name="unknown")


@unknown_router.message(Command("start"))
async def unknown_start(message: Message, user: dict = None):
    """
    Обработка /start для незарегистрированного пользователя.
    По умолчанию предлагаем зарегистрироваться как клиент.
    """
    tg_user = message.from_user
    logger.info(f"Новый пользователь tg_id={tg_user.id} — предлагаем регистрацию как клиент")

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📝 Зарегистрироваться и заказать воду",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/client/")
    ))

    await message.answer(
        f"👋 Привет, {tg_user.first_name}!\n\n"
        f"💧 <b>Osnova 2.0</b> — доставка питьевой воды в Самарканде\n\n"
        f"Вы ещё не зарегистрированы в системе.\n"
        f"Нажмите кнопку ниже, чтобы зарегистрироваться и сделать первый заказ:",
        reply_markup=builder.as_markup()
    )


@unknown_router.message()
async def unknown_any_message(message: Message):
    """Любое другое сообщение от незарегистрированного пользователя."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📝 Зарегистрироваться",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}/client/")
    ))
    await message.answer(
        "❓ Вы не зарегистрированы в системе.\n"
        "Нажмите кнопку ниже для регистрации:",
        reply_markup=builder.as_markup()
    )


# ─── Подключаем роутеры в правильном порядке ─────────────────────────────────
# Важно: роутеры проверяются по порядку. Middleware уже определил роль.
# Каждый роутер фильтрует только своих пользователей через фильтр user['role'].

# Фильтры по роли (применяются к роутерам через middleware data['user'])
# Используем lambda с правильной сигнатурой: (message, **kwargs)
# ВАЖНО: Админ имеет доступ ко всем роутерам (admin, courier, client)
courier.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') in ['courier', 'admin'])
courier.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') in ['courier', 'admin'])

courier_create_order.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') in ['courier', 'admin'])
courier_create_order.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') in ['courier', 'admin'])

client.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'client')
client.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'client')

admin.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'admin')
admin.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'admin')

unknown_router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'unknown')
unknown_router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'unknown')

dp.include_router(admin.router)
dp.include_router(courier.router)
dp.include_router(courier_create_order.router)
dp.include_router(client.router)
dp.include_router(unknown_router)

logger.info("Бот инициализирован, routers подключены.")
