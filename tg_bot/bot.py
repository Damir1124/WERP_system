"""
Инициализация бота и диспетчера.
Подключает middleware, routers и настраивает логику обработки сообщений.
"""
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from tg_bot.config import BOT_TOKEN, LOG_LEVEL
from tg_bot.middlewares.auth import AuthMiddleware
from tg_bot.routers import courier, client, admin

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

# Подключаем routers
dp.include_router(courier.router)
dp.include_router(client.router)
dp.include_router(admin.router)

logger.info("Бот инициализирован, routers подключены.")