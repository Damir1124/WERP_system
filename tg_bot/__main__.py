#!/usr/bin/env python3
"""
Точка входа для запуска Telegram-бота.
Поддерживает два режима: polling (для разработки) и webhook (для продакшена).
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для импорта модулей Django
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настройка Django (для прямого ORM-доступа из бота)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
import django
django.setup()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tg_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Основная асинхронная функция запуска бота."""
    from tg_bot.bot import bot, dp
    from tg_bot.config import BOT_TOKEN, USE_WEBHOOK, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен. Проверьте переменные окружения.")
        sys.exit(1)

    # Режим webhook
    if USE_WEBHOOK:
        logger.info("Запуск бота в режиме webhook...")
        # Устанавливаем webhook
        await bot.set_webhook(
            url=WEBHOOK_URL + WEBHOOK_PATH,
            drop_pending_updates=True
        )
        # Запускаем aiohttp сервер для обработки вебхуков
        from aiohttp import web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=WEBAPP_HOST, port=WEBAPP_PORT)
        await site.start()

        logger.info(f"Webhook установлен на {WEBHOOK_URL + WEBHOOK_PATH}")
        logger.info(f"Сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")

        # Бесконечный цикл
        await asyncio.Event().wait()
    else:
        # Режим polling
        logger.info("Запуск бота в режиме polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)