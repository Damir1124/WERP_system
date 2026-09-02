@echo off
chcp 65001 >nul

:: Корневая директория проекта (там где manage.py)
set "ROOT_DIR=%~dp0"
set PYTHON_PATH=%ROOT_DIR%.venv\Scripts\python.exe
set NPM_PATH=npm

:MENU
cls
echo ╔══════════════════════════════════════════════════╗
echo ║       WERP / Osnova 2.0 — УПРАВЛЕНИЕ            ║
echo ╠══════════════════════════════════════════════════╣
echo ║  [1] ПОЛНЫЙ ЗАПУСК  (Docker + Migrate + App)    ║
echo ║  [2] БЫСТРЫЙ СТАРТ  (Django + Бот + Ngrok)      ║
echo ║  [3] СБОРКА ФРОНТЕНДА (courier + client)        ║
echo ║  [4] ПРИМЕНИТЬ МИГРАЦИИ                         ║
echo ║  [5] ОТКРЫТЬ DJANGO ADMIN в браузере            ║
echo ║  [6] ОТКРЫТЬ MINI APP КУРЬЕРА в браузере        ║
echo ║  [7] ОТКРЫТЬ MINI APP КЛИЕНТА в браузере        ║
echo ║  [8] ПОКАЗАТЬ ЛОГИ (последние 50 строк)         ║
echo ║  [9] ОСТАНОВИТЬ ВСЁ И ВЫЙТИ                     ║
echo ║  [10] ПЕРЕЗАПУСТИТЬ БОТА                          ║
echo ║  [11] ОТКРЫТЬ DASHBOARD                           ║
echo ╚══════════════════════════════════════════════════╝
echo.

set /p choice="Выбери действие (1-11): "

if "%choice%"=="1" goto START_ALL
if "%choice%"=="2" goto RESTART_APP
if "%choice%"=="3" goto BUILD_FRONTEND
if "%choice%"=="4" goto RUN_MIGRATIONS
if "%choice%"=="5" goto OPEN_ADMIN
if "%choice%"=="6" goto OPEN_COURIER
if "%choice%"=="7" goto OPEN_CLIENT
if "%choice%"=="8" goto SHOW_LOGS
if "%choice%"=="9" goto KILL_ALL
if "%choice%"=="10" goto RESTART_BOT
if "%choice%"=="11" goto OPEN_DASHBOARD
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:START_ALL
echo.
echo [1/4] Запуск базы данных (Docker)...
cd /d "%ROOT_DIR%"
docker-compose up -d
timeout /t 5 >nul

echo [2/4] Применение миграций...
:: МЫ УБИРАЕМ СЛОЖНЫЕ ПУТИ И ПРОСТО ПЕРЕХОДИМ В КОРЕНЬ
cd /d "%ROOT_DIR%"
"%PYTHON_PATH%" manage.py migrate
if errorlevel 1 (
    echo.
    echo [!] ОШИБКА: Не удалось запустить миграции. 
    echo Проверь, что manage.py лежит в: %ROOT_DIR%
    pause
    goto MENU
)
goto RESTART_APP

:RESTART_APP
echo.
echo Очистка старых процессов...
taskkill /f /im python.exe /t >nul 2>&1
taskkill /f /im ngrok.exe /t >nul 2>&1
timeout /t 2 >nul

echo Запуск Django (порт 8000)...
:: ГЛАВНЫЙ МОМЕНТ: Сначала переходим, потом запускаем
cd /d "%ROOT_DIR%"
start "Django Server" cmd /k "cd /d "%ROOT_DIR%" && "%PYTHON_PATH%" manage.py runserver 127.0.0.1:8000"

timeout /t 2 >nul

echo Запуск Telegram Бота...
start "Telegram Bot" /min cmd /k "cd /d "%ROOT_DIR%" && "%PYTHON_PATH%" -m tg_bot"

timeout /t 1 >nul

echo Запуск Ngrok туннеля...
start "Ngrok Tunnel" cmd /k "ngrok http 8000 --url monkhood-chaperone-stinger.ngrok-free.dev"

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║  ✅ СИСТЕМА ЗАПУЩЕНА!                            ║
echo ╠══════════════════════════════════════════════════╣
echo ║  Django:  http://localhost:8000                  ║
echo ║  Admin:   http://localhost:8000/admin/           ║
echo ║  Dashb:   http://localhost:8000/dashboard/       ║
echo ║  Курьер:  http://localhost:8000/miniapp/courier/ ║
echo ║  Клиент:  http://localhost:8000/miniapp/client/  ║
echo ║  API:     http://localhost:8000/api/bot/         ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Нажми любую клавишу для возврата в меню...
pause >nul
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:RESTART_BOT
echo.
echo Перезапуск Telegram Бота...
echo Остановка текущего процесса бота...

:: Ищем и убиваем процесс python.exe, который запущен с tg_bot
powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*tg_bot*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

:: Также пробуем закрыть окно по заголовку (на случай если первый способ не сработал)
taskkill /f /fi "WINDOWTITLE eq Telegram Bot*" >nul 2>&1

timeout /t 2 >nul

echo Запуск Telegram Бота...
start "Telegram Bot" /min cmd /k "cd /d "%ROOT_DIR%" && "%PYTHON_PATH%" -m tg_bot"

echo.
echo ✅ Бот успешно перезапущен!
echo.
echo Нажми любую клавишу для возврата в меню...
pause >nul
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:BUILD_FRONTEND
echo.
echo ══════════════════════════════════════════════════
echo   СБОРКА ФРОНТЕНДА
echo ══════════════════════════════════════════════════
echo.

echo [1/2] Сборка Mini App КУРЬЕРА...
cd /d "%ROOT_DIR%frontend\courier"
call %NPM_PATH% run build
if errorlevel 1 (
    echo [!] ОШИБКА при сборке курьерского Mini App!
    cd /d "%ROOT_DIR%"
    pause
    goto MENU
)
cd /d "%ROOT_DIR%"
echo [OK] Курьерский Mini App собран → static/miniapp/courier/

echo.
echo [2/2] Сборка Mini App КЛИЕНТА...
cd /d "%ROOT_DIR%frontend\client"
call %NPM_PATH% run build
if errorlevel 1 (
    echo [!] ОШИБКА при сборке клиентского Mini App!
    cd /d "%ROOT_DIR%"
    pause
    goto MENU
)
cd /d "%ROOT_DIR%"
echo [OK] Клиентский Mini App собран → static/miniapp/client/

echo.
echo ✅ Оба Mini App успешно собраны!
echo.
echo ⚠️  ВАЖНО: Если изменился ngrok URL — обнови .env.local файлы:
echo    frontend\courier\.env.local
echo    frontend\client\.env.local
echo    и пересобери снова (пункт 3)
echo.
pause
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:RUN_MIGRATIONS
cd /d "%ROOT_DIR%"
echo.
echo ══════════════════════════════════════════════════
echo   ПРИМЕНЕНИЕ МИГРАЦИЙ
echo ══════════════════════════════════════════════════
echo.
"%PYTHON_PATH%" manage.py migrate
echo.
echo Нажми любую клавишу для возврата в меню...
pause >nul
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:OPEN_ADMIN
start "" "http://localhost:8000/admin/"
goto MENU

:OPEN_COURIER
start "" "http://localhost:8000/miniapp/courier/"
goto MENU

:OPEN_CLIENT
start "" "http://localhost:8000/miniapp/client/"
goto MENU

:OPEN_DASHBOARD
start "" "http://localhost:8000/dashboard/"
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:SHOW_LOGS
cd /d "%ROOT_DIR%"
echo.
echo ══════════════════════════════════════════════════
echo   ПОСЛЕДНИЕ ЛОГИ БОТА (tg_bot.log)
echo ══════════════════════════════════════════════════
echo.
if exist tg_bot.log (
    powershell -command "Get-Content '%ROOT_DIR%tg_bot.log' -Tail 50"
) else (
    echo Файл tg_bot.log не найден.
)
echo.
pause
goto MENU

:: ─────────────────────────────────────────────────────────────────────────────
:KILL_ALL
cd /d "%ROOT_DIR%"
echo.
echo Полная остановка системы и закрытие окон...

:: 1. Убиваем фоновые процессы
taskkill /f /im python.exe /t >nul 2>&1
taskkill /f /im ngrok.exe /t >nul 2>&1

:: 2. Жестко закрываем открытые скриптом окна по их заголовкам
taskkill /f /fi "WINDOWTITLE eq Django Server*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Telegram Bot*" >nul 2>&1
taskkill /f /fi "Ngrok Tunnel*" >nul 2>&1

:: 3. Останавливаем базу данных в Docker
docker-compose stop
echo.
echo [✓] Все процессы завершены, окна закрыты. 
echo [✓] Главное окно закроется через 3 сек.
timeout /t 3 >nul
exit
