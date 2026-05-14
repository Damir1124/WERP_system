# Руководство по запуску WERP системы с ngrok и BotFather
# WEb АДРЕС У ГРОК ВСЕГДА РАЗНЫЦ КОГДА ЗАПУСКАЕМ ЗАНОВО В ENV И В BOTFATER НАДО МЕНЯТЬ

## Цель
Запустить Django сервер, пробросить его через ngrok, настроить Telegram Bot (вебхук) и получить рабочее приложение с авторизацией по данным Telegram.

## Предварительные требования
1. Установленный Python 3.10+ (путь: `C:\Users\Damir\AppData\Local\Python\bin\python.exe`)
2. Установленный ngrok (добавлен в PATH)
3. Установленные зависимости Django: `pip install -r requirements.txt`
4. Установленные зависимости бота: `pip install -r requirements_bot.txt`
5. База данных PostgreSQL запущена (настройки в .env)

## Шаг 1: Настройка окружения
Убедитесь, что файл `.env` содержит корректные значения:
```
DB_NAME=werp_system
DB_USER=werp_admin
DB_PASSWORD=123
DB_HOST=localhost
DB_PORT=5454

DJANGO_SECRET_KEY=ваш_ключ

BOT_TOKEN=8614741494:AAGVzBf3iUCg-mVQ38am6hGiX_eZtQyKJnE
USE_WEBHOOK=false          # измените на true для вебхука
WEBHOOK_HOST=https://yourdomain.com
WEBHOOK_PATH=/webhook
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=3001

MINI_APP_URL=https://yourdomain.com/static/miniapp
```

## Шаг 2: Запуск Django сервера
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
Сервер будет доступен на `http://localhost:8000`

## Шаг 3: Запуск Telegram бота
### Режим polling (для разработки)
```bash
python -m tg_bot
```
Бот будет работать в режиме long‑polling.

### Режим webhook (для продакшена)
1. Установите `USE_WEBHOOK=true` в `.env`
2. Укажите `WEBHOOK_HOST=https://xxxx.ngrok.io` (после запуска ngrok)
3. Запустите бота:
   ```bash
   python -m tg_bot
   ```
   Бот запустит aiohttp сервер на порту `3001` и установит вебхук.

## Шаг 4: Запуск ngrok туннеля
```bash
ngrok http 8000
```
Если бот использует вебхук на порту 3001, пробросьте и его:
```bash
ngrok http 3001
```
Или используйте мультиплексный туннель (ngrok позволяет пробрасывать несколько портов).

После запуска ngrok выдаст публичный HTTPS URL вида `https://xxxx.ngrok.io`.

## Шаг 5: Настройка BotFather
1. Откройте BotFather в Telegram (`@BotFather`)
2. Выберите своего бота
3. Отправьте команду `/setwebhook`
4. Укажите URL вебхука: `https://xxxx.ngrok.io/webhook`
5. Если бот работает в режиме polling, этот шаг можно пропустить.

## Шаг 6: Настройка Telegram Mini App (TWA)
1. Получите URL Mini App: `https://xxxx.ngrok.io/static/miniapp/courier/index.html`
2. В BotFather настройте меню бота, добавьте кнопку "Open Web App" с этим URL.
3. Либо используйте прямую ссылку `https://t.me/your_bot?startapp=xxxx` (через параметр `startapp`).

## Шаг 7: Проверка работоспособности
1. Откройте бота в Telegram, нажмите кнопку Mini App – должно открыться приложение курьера.
2. Проверьте авторизацию: приложение должно отправить `initData` на сервер и получить данные пользователя.
3. Проверьте API: откройте `https://xxxx.ngrok.io/api/bot/identify/` с заголовками Telegram.

## Автоматический запуск
Используйте скрипт `start_all.bat` для одновременного запуска Django и бота (polling). Затем вручную запустите ngrok.

## Устранение неполадок
### 1. Ngrok выдает ошибку "tunnel session failed"
- Проверьте интернет‑соединение.
- Убедитесь, что ngrok авторизован (выполните `ngrok authtoken YOUR_TOKEN`).

### 2. BotFather не принимает вебхук
- Убедитесь, что URL заканчивается на `/webhook`.
- Убедитесь, что бот запущен в режиме webhook и слушает порт 3001.
- Проверьте, что ngrok туннель активен и порт 3001 проброшен.

### 3. Mini App не загружается
- Проверьте, что статические файлы собраны (`npm run build` в `frontend/courier/`).
- Убедитесь, что Django обслуживает статику (в режиме DEBUG статика раздаётся автоматически).
- Проверьте консоль браузера на наличие ошибок CORS (если нужно, добавьте `CORS_ALLOW_ALL_ORIGINS = True` в settings.py).

### 4. Ошибки базы данных
- Убедитесь, что PostgreSQL запущен на порту 5454.
- Выполните миграции: `python manage.py migrate`.

## Дополнительные настройки
### CORS для TWA
Добавьте в `WERP_system/settings.py`:
```python
CORS_ALLOW_ALL_ORIGINS = True  # для разработки
```
или
```python
CORS_ALLOWED_ORIGINS = [
    "https://xxxx.ngrok.io",
    "https://web.telegram.org",
]
```

### Логирование
Логи бота пишутся в `tg_bot.log`, логи Django – в консоль.

## Готово!
Теперь у вас есть полностью рабочая система:
- Django сервер с API
- Telegram бот с вебхуком
- Telegram Mini App для курьеров
- Публичный доступ через ngrok
- Интеграция с BotFather

Для продакшена замените ngrok на облачный хостинг (например, VPS с Nginx и SSL).