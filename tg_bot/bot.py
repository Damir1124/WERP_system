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
from aiogram.types import Message

from tg_bot.config import BOT_TOKEN, LOG_LEVEL
from tg_bot.middlewares.auth import AuthMiddleware
from tg_bot.routers import courier, client, admin
from tg_bot.routers import courier_create_order
from tg_bot.routers import operator as operator_router
from tg_bot.routers import owner as owner_router

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

# ─── Роутер для незарегистрированных пользователей (fallback) ─────────────────
# IdentifyView теперь авто-регистрирует новых пользователей как клиентов,
# поэтому этот роутер срабатывает только при недоступности API.

unknown_router = Router(name="unknown")


@unknown_router.message(Command("start"))
async def unknown_start(message: Message, user: dict = None):
    """
    Обработка /start если API недоступен.
    """
    tg_user = message.from_user
    logger.warning(f"Пользователь tg_id={tg_user.id} — не удалось определить роль (API недоступен?)")

    await message.answer(
        f"👋 Здравствуйте, {tg_user.first_name}!\n\n"
        f"💧 <b>Osnova 2.0</b> — доставка питьевой воды в Самарканде\n\n"
        f"❌ Не удалось подключиться к серверу.\n"
        f"Пожалуйста, попробуйте позже или отправьте /start снова."
    )


@unknown_router.message()
async def unknown_any_message(message: Message):
    """Любое другое сообщение при недоступности API."""
    await message.answer(
        "❓ Не удалось подключиться к серверу.\n"
        "Пожалуйста, попробуйте позже или отправьте /start."
    )


# ─── Подключаем роутеры в правильном порядке ─────────────────────────────────
# Важно: роутеры проверяются по порядку. Middleware уже определил роль.
# Каждый роутер фильтрует только своих пользователей через фильтр user['role'].

# Фильтры по роли (применяются к роутерам через middleware data['user'])
# Строго одна роль = один роутер. Никаких пересечений.
# bot_role: courier / operator / owner / client / unknown
courier.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'courier')
courier.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'courier')

courier_create_order.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'courier')
courier_create_order.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'courier')

operator_router.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'operator')
operator_router.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'operator')

owner_router.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'owner')
owner_router.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'owner')

admin.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'admin')
admin.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'admin')

# Клиентский роутер обрабатывает client и unknown
client.router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') in ['client', 'unknown'])
client.router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') in ['client', 'unknown'])

unknown_router.message.filter(lambda message, user=None, **kwargs: user and user.get('role') == 'unknown')
unknown_router.callback_query.filter(lambda callback, user=None, **kwargs: user and user.get('role') == 'unknown')

dp.include_router(owner_router.router)
dp.include_router(admin.router)
dp.include_router(operator_router.router)
dp.include_router(courier.router)
dp.include_router(courier_create_order.router)
dp.include_router(client.router)
dp.include_router(unknown_router)

logger.info("Бот инициализирован, routers подключены.")
