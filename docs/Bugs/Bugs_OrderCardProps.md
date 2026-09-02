# Баг: Карточка заказа показывает «Локация» / «Адрес не указан»

## Симптом
В экранах «Пул» (`Pool.jsx`) и «Рейс» (`Trip.jsx`) карточка заказа (`OrderCard.jsx`):
- в свёрнутом виде показывала `📍 Локация` (будто координат нет);
- в раскрытом виде — `Адрес не указан`,
хотя у заказа реально задан адрес доставки.

## Причина
После перехода на многоадресность (`Order.delivery_address → ClientAddress`) сериализатор `OrderSerializer` отдаёт адрес под **новыми именами** полей: `delivery_address_text`, `delivery_latitude`, `delivery_longitude`.

`OrderCard.jsx` был обновлён и читает именно эти поля. Но функции трансформации заказов в родительских экранах всё ещё пробрасывали **старые** имена:
- `Pool.jsx` → `transformOrder` возвращал `address`, `latitude`, `longitude`
- `Trip.jsx` → `transformedOrder` возвращал `address`, `latitude`, `longitude`

В итоге `OrderCard` получал `undefined` вместо `delivery_address_text` → срабатывали fallback-ветки «Локация» / «Адрес не указан».

> 💡 **Почему так вышло:** изменение имён полей в сериализаторе не было синхронизировано со всеми местами, которые формируют пропсы для `OrderCard`. Карточка — единственный потребитель, но данные в неё попадают через промежуточный `transformOrder`, который «переименовал» поля в обратную сторону.

## Где в коде
- `frontend/courier/src/components/OrderCard/OrderCard.jsx:86-114` — читает `delivery_address_text` / `delivery_latitude` / `delivery_longitude`
- `frontend/courier/src/pages/Pool.jsx:60-74` — `transformOrder` (до исправления: `address`/`latitude`/`longitude`)
- `frontend/courier/src/pages/Trip.jsx:172-187` — `transformedOrder` (до исправления: `address`/`latitude`/`longitude`)
- `apps/bot_bridge/serializers.py:58-60` — источник имён `delivery_address_text` и т.д.

## Решение
Изменены **ключи** (не значения) в обеих трансформациях:

```javascript
// ДО (проблемный код)
const transformOrder = (order) => ({
  // ...
  address: order.client_address || 'Адрес не указан',
  latitude: order.latitude || null,
  longitude: order.longitude || null,
});

// ПОСЛЕ (исправление)
const transformOrder = (order) => ({
  // ...
  delivery_address_text: order.delivery_address_text || 'Адрес не указан',
  delivery_latitude: order.delivery_latitude || null,
  delivery_longitude: order.delivery_longitude || null,
});
```
Аналогично для `transformedOrder` в `Trip.jsx`.

## Как не допустить снова
1. **Единый источник истины для имён полей** — это ответ API. Если меняете имена в сериализаторе, делайте grep по всему фронтенду на старое имя (`address`, `latitude` в контексте заказа) и обновляйте все `transform*` функции за один проход.
2. **Типизация / общий mapper.** Завести один хелпер `mapOrderFromApi(apiOrder)` и использовать его во всех экранах, чтобы имена полей не дублировались.
3. Визуально проверять карточку заказа (свёрнутый + раскрытый вид) после любого изменения `OrderSerializer`.

## Связанные концепции
- [[Modules_BotBridge|Модуль Bot Bridge]] — `OrderSerializer` и поля `delivery_address_*`
- [[Modules_Logistics|Модуль Логистики]] — FK `Order.delivery_address`
