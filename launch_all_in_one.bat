@echo off
echo ============================================
echo Запуск WERP системы (Django + Bot + Ngrok)
echo ============================================
echo.

echo 1. Проверка зависимостей...
if not exist "C:\Users\Damir\AppData\Local\Python\bin\python.exe" (
    echo Python не найден.
    pause
    exit /b 1
)

echo 2. Запуск Django сервера на порту 8000...
start "Django Server" cmd /k "C:\Users\Damir\AppData\Local\Python\bin\python.exe" manage.py runserver 0.0.0.0:8000

echo 3. Ожидание запуска сервера (5 секунд)...
timeout /t 5 /nobreak >nul

echo 4. Запуск Telegram бота в режиме polling...
start "Telegram Bot" cmd /k "C:\Users\Damir\AppData\Local\Python\bin\python.exe" -m tg_bot

echo 5. Запуск ngrok туннеля на порт 8000...
if exist "C:\Users\Damir\ngrok.exe" (
    start "Ngrok Tunnel" cmd /k "C:\Users\Damir\ngrok.exe" http 8000
) else (
    echo Ngrok не найден в C:\Users\Damir\ngrok.exe
    echo Запустите ngrok вручную: ngrok http 8000
)

echo.
echo ============================================
echo ВСЁ ЗАПУЩЕНО!
echo ============================================
echo.
echo 1. Django сервер: http://localhost:8000
echo 2. Ngrok туннель: https://monkhood-chaperone-stinger.ngrok-free.dev (ваш URL может отличаться)
echo 3. Telegram бот: работает в режиме polling (проверьте логи в окне "Telegram Bot")
echo.
echo Инструкция:
echo - Откройте Mini App: https://monkhood-chaperone-stinger.ngrok-free.dev/static/miniapp/courier/index.html
echo - Проверьте API: https://monkhood-chaperone-stinger.ngrok-free.dev/api/bot/identify/
echo - Для вебхука измените .env: USE_WEBHOOK=true, WEBHOOK_HOST=https://monkhood-chaperone-stinger.ngrok-free.dev
echo - Затем перезапустите бота.
echo.
pause