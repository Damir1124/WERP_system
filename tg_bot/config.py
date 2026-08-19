"""
Конфигурация Telegram-бота.
Все настройки берутся из переменных окружения или .env файла.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (расположенного в корне проекта)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Токен бота (обязательный)
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен. Добавьте BOT_TOKEN в .env файл.")

# Режим работы: webhook или polling
USE_WEBHOOK = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'

# Настройки webhook (требуются только если USE_WEBHOOK=True)
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'https://yourdomain.com')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Хост и порт для aiohttp сервера (только для webhook режима)
WEBAPP_HOST = os.getenv('WEBAPP_HOST', '0.0.0.0')
WEBAPP_PORT = int(os.getenv('WEBAPP_PORT', 3001))

# URL Django API (для идентификации пользователей и получения данных)
DJANGO_API_URL = os.getenv('DJANGO_API_URL', 'http://localhost:8000/api/bot')

# URL Mini App (Telegram Web App)
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://yourdomain.com/static/miniapp')

# URL Launcher — единая точка входа для всех пользователей
LAUNCHER_URL = f"{MINI_APP_URL}/launcher/index.html"

# Список администраторов (Telegram ID через запятую)
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

# Логирование
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Проверка конфигурации
if USE_WEBHOOK and WEBHOOK_HOST == 'https://yourdomain.com':
    print("⚠️  ВНИМАНИЕ: WEBHOOK_HOST установлен на значение по умолчанию. Замените на реальный домен.")