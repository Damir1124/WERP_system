# OrderCard Component

Компонент карточки заказа для Telegram Mini App курьеров с двумя состояниями: свёрнутое и развёрнутое.

## Структура файлов

```
components/OrderCard/
├── OrderCard.jsx              # Основной компонент
├── OrderCard.css              # Стили компонента
├── FreshnessIndicator.jsx     # Индикатор свежести заказа
└── README.md                  # Документация
```

## Использование

```jsx
import OrderCard from '../components/OrderCard/OrderCard.jsx'

// Для пула заказов
<OrderCard
  order={orderData}
  isPoolOrder={true}
  onAccept={() => handleAssign(order.id)}
/>

// Для заказов в рейсе
<OrderCard
  order={orderData}
  isTripOrder={true}
  onConfirm={() => navigate(`/order/${order.id}/confirm`)}
/>
```

## Props

### order (Object, required)
Объект заказа со следующими полями:

```javascript
{
  id: number,                    // ID заказа
  created_at: string,            // ISO дата создания
  address: string,               // Адрес доставки
  latitude: number | null,       // Широта (для карты)
  longitude: number | null,      // Долгота (для карты)
  payment_type: string,          // 'cash' | 'card' | 'transfer'
  payment_type_label: string,    // Читаемое название типа оплаты
  items: Array<{                 // Список товаров
    id: number,
    product_name: string,
    product_type: string,        // 'WT' для воды
    quantity: number
  }>,
  client: {                      // Данные клиента
    name: string,
    phone: string
  },
  created_by: string             // Кто создал заказ
}
```

### isPoolOrder (boolean, optional)
Если `true`, показывает кнопку "🚛 Взять заказ"

### isTripOrder (boolean, optional)
Если `true`, показывает кнопку "✅ Подтвердить доставку"

### onAccept (function, optional)
Callback для кнопки "Взять заказ"

### onConfirm (function, optional)
Callback для кнопки "Подтвердить доставку"

## Особенности

### Индикатор свежести
Цветная точка слева показывает возраст заказа:
- 🟢 Зелёный: менее 3 часов
- 🟡 Жёлтый: от 3 до 6 часов
- 🔴 Красный: более 6 часов (с pulse-анимацией)

Пороги настраиваются в [`config/orderFreshness.js`](../../config/orderFreshness.js)

### Свёрнутое состояние
Одна строка с ключевой информацией:
- Индикатор свежести
- ID заказа (#123)
- Количество товара (бейдж)
- Адрес (truncated)
- Тип оплаты (бейдж)
- Шеврон (↓)

### Развёрнутое состояние
Раскрывается при клике, показывает:
- Полный адрес + кнопка "Открыть на карте" (если есть координаты)
- Телефон клиента (кликабельная ссылка)
- Список товаров (вода выделена 💧)
- Дата и время создания
- Кто создал заказ
- Кнопки действий

## Анимации

- Раскрытие/закрытие: 250ms ease
- Шеврон: rotate 180deg, 200ms
- Pulse для красного индикатора

## Цветовая схема

Светло-синяя минималистичная тема, определена в CSS-переменных:
- `--accent-blue`: #3b82f6
- `--accent-green`: #22c55e
- `--accent-yellow`: #f59e0b
- `--accent-red`: #ef4444

## Интеграция

Компонент интегрирован в:
- [`pages/Pool.jsx`](../../pages/Pool.jsx) - пул свободных заказов
- [`pages/Trip.jsx`](../../pages/Trip.jsx) - заказы текущего рейса
