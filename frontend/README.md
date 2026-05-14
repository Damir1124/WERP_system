# Mini App Frontend для WERP / Osnova 2.0

Telegram Mini App (TWA) для трёх ролевых профилей: курьер, клиент, администратор.

## Структура

```
frontend/
├── courier/          — Mini App для курьера (Vite + React + Tailwind)
├── client/           — Mini App для клиента (Vite + React + Tailwind)
└── README.md         — этот файл
```

## Технологии

- **React 18** через Vite — компонентный подход
- **Tailwind CSS** — утилитарные классы, не надо писать CSS вручную
- **@twa-dev/sdk** — TypeScript-обёртка над `window.Telegram.WebApp`
- **React Router DOM** — навигация между страницами

## Как запустить разработку

### 1. Установить Node.js (v18+)
```bash
node --version   # проверка
```

### 2. Создать проект курьера
```bash
cd frontend/courier
npm create vite@latest . -- --template react
npm install
```

### 3. Установить зависимости
```bash
npm install @twa-dev/sdk react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 4. Настроить Tailwind
`tailwind.config.js`:
```js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

`src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 5. Настроить Vite
`vite.config.js`:
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/miniapp/courier/',
  build: {
    outDir: '../../static/miniapp/courier',
    emptyOutDir: true,
  }
})
```

### 6. Создать `.env` файл
```
VITE_API_URL=https://yourdomain.com
```

### 7. Запустить dev-сервер
```bash
npm run dev
```

## Сборка для продакшена

```bash
npm run build
# → файлы появятся в static/miniapp/courier/
```

Django автоматически раздаёт всё из `STATICFILES_DIRS`. URL: `https://yourdomain.com/static/miniapp/courier/index.html`

## Локальная разработка TWA

Telegram не открывает `localhost`. Нужен публичный HTTPS-туннель:

### Вариант 1: ngrok (проще)
```bash
npm install -g ngrok
ngrok http 8000
# → получишь https://xxxx.ngrok.io → вставь в .env и в настройки бота
```

### Вариант 2: Cloudflare Tunnel (стабильнее, бесплатно)
```bash
cloudflared tunnel --url http://localhost:8000
```

## Авторизация TWA

Telegram подписывает данные пользователя (`initData`) своим секретным ключом. Django проверяет подпись через `TelegramInitDataPermission` в `apps/bot_bridge/permissions.py`.

**Заголовки для API запросов:**
```javascript
headers: {
  'Content-Type': 'application/json',
  'X-Telegram-ID': tgId,           // идентификация курьера
  'X-Telegram-Init-Data': initData, // валидация на сервере
}
```

## Nginx конфигурация для продакшена

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # Статика Django (включает собранные Mini App)
    location /static/ {
        alias /путь/к/проекту/staticfiles/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Все остальные запросы → Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

## Порядок действий при реализации P3

1. [Django] Добавить tg_id, is_admin в Worker. Миграция.
2. [Django] Добавить /api/bot/identify/ endpoint.
3. [Django] Добавить все новые bot_bridge endpoints (courier pool, trip, client orders, admin stats).
4. [Django] Написать TelegramInitDataPermission в bot_bridge/permissions.py.
5. [Django] Написать notify.py для уведомлений клиентам.
6. [Bot] Создать tg_bot/ структуру. Настроить роутеры по ролям.
7. [Frontend] Создать frontend/courier/ через Vite (шаги 1-8 выше).
8. [Frontend] Создать frontend/client/ аналогично.
9. [Build] npm run build в обоих приложениях → файлы в static/miniapp/.
10. [Django] python manage.py collectstatic.
11. [Nginx] Настроить конфиг. Получить SSL.
12. [Bot] Прописать HTTPS URL кнопок Mini App.
13. [Тест] Проверить открытие TWA в Telegram → запросы доходят до Django.