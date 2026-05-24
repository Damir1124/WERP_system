# Модуль: Mini App Курьера (`frontend/courier/`)

> Последнее обновление: 2026-05-24 (рефакторинг дизайна по макету v2)

---

## Зачем этот модуль

Telegram Mini App для курьера — это веб-приложение, которое открывается прямо внутри Telegram. Курьер видит свои заказы, управляет рейсом и подтверждает доставки без выхода из мессенджера. Бэкенд — Django API (`/api/bot/courier/...`), фронтенд — React + Vite.

---

## Стек и зависимости

| Компонент | Технология | Зачем |
|-----------|-----------|-------|
| Фреймворк | React 18 + Vite | Компонентный подход, быстрая сборка |
| Стили | Чистый CSS (CSS-переменные) | Без Tailwind — меньше размер, полный контроль |
| Telegram SDK | `@twa-dev/sdk` | `window.Telegram.WebApp`, tg_id, initData |
| Роутинг | `react-router-dom` v7 | Навигация между экранами |
| HTTP | `fetch` (встроенный) | Запросы к Django DRF API |

> 💡 **Почему отказались от Tailwind:** Tailwind генерирует CSS только для классов которые есть в JSX. При переходе на кастомный дизайн с CSS-переменными проще писать чистый CSS — он предсказуем, легко читается и не требует знания утилитарных классов. CSS уменьшился с 16 kB до 10 kB.

---

## Структура файлов

```
frontend/courier/
├── src/
│   ├── index.css          ← Все стили: CSS-переменные, компоненты
│   ├── main.jsx           ← Точка входа React
│   ├── App.jsx            ← Shell: topbar + роутинг + bottom-nav
│   ├── tg.js              ← Инициализация Telegram.WebApp, tgId, initData
│   ├── api.js             ← Все fetch-запросы к /api/bot/courier/...
│   └── pages/
│       ├── Trip.jsx       ← Экран "Мой рейс"
│       ├── Pool.jsx       ← Экран "Пул заказов" + создание заказа
│       ├── OrderConfirm.jsx ← Подтверждение доставки
│       ├── Shifts.jsx     ← История смен
│       └── Colleagues.jsx ← Коллеги на смене
├── vite.config.js         ← base: '/static/miniapp/courier/', outDir: '../../static/miniapp/courier'
├── .env.local             ← VITE_API_URL=https://...ngrok.../api/bot
└── package.json
```

---

## CSS-система (Design Tokens)

Все цвета и отступы — через CSS-переменные в [`frontend/courier/src/index.css`](../frontend/courier/src/index.css):

```css
:root {
  --ink:        #1a1a1a;   /* основной текст */
  --ink2:       #444;      /* вторичный текст */
  --ink3:       #777;      /* подписи, метки */
  --bg:         #ffffff;   /* карточки */
  --bg2:        #f5f5f3;   /* фон страницы */
  --bg3:        #ebebea;   /* заголовки блоков */
  --border:     rgba(0,0,0,0.14);
  --blue:       #1450a3;   /* акцент, кнопки */
  --blue-bg:    #e8f0fc;
  --green:      #1d7a3a;   /* успех, наличные */
  --green-bg:   #e6f5eb;
  --amber:      #a35a00;   /* предупреждение, остаток */
  --teal:       #0d6e5a;   /* пустые баклажки */
  --red:        #c0392b;   /* ошибки, брак */
}
```

> 💡 **Почему CSS-переменные, а не константы в JS:** CSS-переменные работают нативно в браузере, не требуют импортов, доступны в любом компоненте без пропсов. Это стандартный подход для дизайн-систем (аналог Tailwind config, но без сборщика).

---

## Экраны и их логика

### 1. Мой рейс (`Trip.jsx`)

**Что показывает:** счётчики тары, деньги, список заказов рейса.

**Состояния:**
- Нет смены → кнопка "Открыть смену" → `POST /api/bot/courier/shifts/`
- Смена есть, нет рейса → кнопка "Начать рейс" → `POST /api/bot/courier/trips/`
- Активный рейс → счётчики из `summary`, список `orders`

**API:** `GET /api/bot/courier/trip/current/`

Ответ:
```json
{
  "active_shift": true,
  "active_trip": true,
  "trip": { "orders": [...], "id": 5 },
  "summary": {
    "full_loaded": 12, "delivered": 7, "full_remain": 5,
    "empty_expected": 4, "cash_expected": 245000, "card_expected": 80000
  }
}
```

---

### 2. Пул заказов (`Pool.jsx`)

**Что показывает:** свободные заказы (PENDING без курьера), кнопка "Взять", форма создания заказа.

**Взять заказ:** `POST /api/bot/courier/pool/<id>/assign/`

**Создать заказ (модальное окно):**
```json
POST /api/bot/courier/orders/create/
{
  "trip": 5,
  "client": null,
  "payment_type": "CH",
  "items": [{ "product": 3, "quantity": 2, "exchange_qty": 0, "sell_with_qty": 0, "defective_qty": 0 }]
}
```

> ⚠️ **Важно:** `payment_type` должен быть `"CH"` (не `"CASH"`). Маппинг в `Pool.jsx`:
> ```js
> const PAY_MAP = { 'CASH': 'CH', 'CARD': 'CD', 'BONUS': 'BS' }
> ```

---

### 3. Подтверждение доставки (`OrderConfirm.jsx`)

**Что показывает:** по каждому продукту — stepper для учёта тары (обмен/с тарой/брак), выбор оплаты, итого.

**Логика тары (только для продуктов типа Вода 20л):**

| Поле | Смысл | Действие на складе |
|------|-------|-------------------|
| `exchange_qty` | Клиент отдал пустую тару | Списать BOTTLE × exchange_qty |
| `sell_with_qty` | Продажа с тарой (тара остаётся у клиента) | Списать BOTTLE × sell_with_qty |
| `defective_qty` | Брак — тара возвращается | НЕ списывать |

**Подтверждение:** `POST /api/bot/courier/orders/confirm/`
```json
{ "order_id": 42, "confirmed": true, "note": "" }
```

> 💡 **Почему `exchange_qty` в `OrderItem`, а не в `Order`:** Один заказ может содержать несколько продуктов. Учёт тары привязан к конкретной позиции (Вода 20л), а не ко всему заказу. Это позволяет в одном заказе иметь и воду с обменом тары, и кулер без тары.

---

### 4. История смен (`Shifts.jsx`)

**API:** `GET /api/bot/courier/shifts/`

Показывает список смен с итогами (наличные, карта, кол-во рейсов/заказов). Кнопка "Закрыть смену" для открытых смен.

---

### 5. Коллеги (`Colleagues.jsx`)

**API:** `GET /api/bot/courier/colleagues/`

Показывает курьеров с открытой сменой сегодня. Аватар — инициалы из имени. Статистика: доставлено, наличные, карта.

---

## App Shell (`App.jsx`)

Структура приложения:

```
<Router>
  <div class="app-shell">
    <TopBar />          ← заголовок меняется по маршруту
    <Routes>            ← страницы
    <BottomNav />       ← 4 вкладки: Пул / Рейс / Смены / Коллеги
  </div>
</Router>
```

На экране подтверждения (`/order/:id/confirm`) TopBar и BottomNav скрываются — страница рендерит свой заголовок.

---

## Авторизация

Каждый запрос к API добавляет заголовок:
```
X-Telegram-ID: <tg_id>
```

Django проверяет через `IsCourier` permission: ищет `Worker.objects.get(tg_id=...)`.

В режиме разработки (вне Telegram) `tg.js` использует `effectiveTgId` — fallback на `DEV_TG_ID` из `.env.local`.

---

## Сборка и деплой

```bash
cd frontend/courier
npm run build
# → файлы в static/miniapp/courier/
# Django раздаёт через STATICFILES_DIRS
# URL: /miniapp/courier/ → serve_spa('courier') → index.html
```

**Vite config:**
```js
base: '/static/miniapp/courier/',
build: { outDir: '../../static/miniapp/courier', emptyOutDir: true }
```

> 💡 **Почему `base` важен:** Vite вставляет `base` в пути к JS/CSS файлам в `index.html`. Если `base` не совпадает с реальным URL где лежат файлы — браузер не найдёт ассеты и приложение не загрузится.

---

## Известные ограничения

- `OrderConfirm.jsx` загружает данные заказа через `getCurrentTrip()` — если заказ не в активном рейсе, он не найдётся. Нужен отдельный endpoint `GET /api/bot/orders/<id>/`.
- Поле `client_address` в `OrderSerializer` не сериализуется — нужно добавить `client__address` в `ClientSerializer` или вложенный сериализатор.
- Telegram не открывает `localhost` — для разработки нужен ngrok: `VITE_API_URL=https://xxxx.ngrok-free.dev/api/bot`.
