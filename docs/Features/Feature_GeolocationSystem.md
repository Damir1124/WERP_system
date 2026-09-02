# Feature: Система геолокации для заказов

> Дата реализации: 07.07.2026  
> Статус: ✅ Завершено

## Зачем это нужно

Курьеру необходимо точно знать место доставки для GPS-навигации. Текстовый адрес ("ул. Пушкина, д. 10") понятен человеку, но не всегда точен для навигатора. Система поддерживает **гибридный подход**: текстовый адрес для понимания + GPS-координаты для навигации.

## Что реализовано

### 1. База данных — расширение модели Client

**Файл:** `apps/clients/models.py`

```python
latitude = models.DecimalField(
    max_digits=10,  # Было 9 → стало 10
    decimal_places=6,
    null=True,
    blank=True,
    verbose_name='Широта'
)
longitude = models.DecimalField(
    max_digits=10,  # Было 9 → стало 10
    decimal_places=6,
    null=True,
    blank=True,
    verbose_name='Долгота'
)
```

**Почему max_digits=10:**
- Широта: от -90.000000 до +90.000000 (3 цифры до запятой)
- Долгота: от -180.000000 до +180.000000 (4 цифры до запятой)
- 6 знаков после запятой дают точность ~10 см на местности
- Старое значение (9) не вмещало долготу 180.123456

**Миграция:** `apps/clients/migrations/0003_alter_client_latitude_alter_client_longitude.py`

---

### 2. Интерактивная карта — компонент LocationPicker

**Файл:** `frontend/courier/src/components/LocationPicker.jsx`

**Зависимости:**
```json
{
  "react-leaflet": "4.2.1",
  "leaflet": "1.9.4"
}
```

**Почему версия 4.2.1, а не 5.x:**
- Версия 5.x требует React 19
- В проекте используется React 18.3.1
- Версия 4.2.1 полностью совместима

**Ключевые возможности:**

1. **Автоматическое определение позиции при открытии**
   ```javascript
   useEffect(() => {
     if (!initialPosition && navigator.geolocation) {
       navigator.geolocation.getCurrentPosition(
         (pos) => {
           const newPos = {
             lat: parseFloat(pos.coords.latitude.toFixed(6)),
             lon: parseFloat(pos.coords.longitude.toFixed(6))
           }
           setPosition(newPos)
           setMapCenter(newPos) // Центрируем карту
         }
       )
     }
   }, [initialPosition])
   ```

2. **Компонент MapUpdater для плавного центрирования**
   ```javascript
   function MapUpdater() {
     const map = useMap()
     useEffect(() => {
       map.setView([mapCenter.lat, mapCenter.lon], 15)
     }, [map, mapCenter])
     return null
   }
   ```
   
   **Почему отдельный компонент:**
   - `MapContainer` не реагирует на изменение prop `center` после монтирования
   - `useMap()` hook работает только внутри дочерних компонентов MapContainer
   - MapUpdater следит за `mapCenter` и программно обновляет вид карты

3. **Клик по карте для выбора точки**
   ```javascript
   function LocationMarker() {
     useMapEvents({
       click(e) {
         const newPos = {
           lat: parseFloat(e.latlng.lat.toFixed(6)),
           lon: parseFloat(e.latlng.lng.toFixed(6))
         }
         setPosition(newPos)
       },
     })
     return <Marker position={[position.lat, position.lon]} />
   }
   ```

**UI/UX:**
- Полноэкранное модальное окно
- Кнопка "📡 Моя локация" для повторного центрирования
- Отображение координат с точностью до 6 знаков
- Кнопки "Отмена" и "✓ Подтвердить"

---

### 3. Форма создания заказа — интеграция карты

**Файл:** `frontend/courier/src/pages/OrderCreate.jsx`

**Три способа указать координаты:**

| Кнопка | Действие | Что происходит |
|--------|----------|----------------|
| 📡 Текущая локация | `handleRequestLocation()` | HTML5 Geolocation API → сохраняет координаты |
| 🗺️ Выбрать на карте | `handleSelectLocationOnMap()` | Открывает LocationPicker → сохраняет координаты |
| 📍 Сохранённая метка | `handleOpenMap()` | Открывает Google Maps с координатами клиента из БД |

**ВАЖНОЕ РЕШЕНИЕ: Координаты НЕ заполняют поле адреса**

```javascript
// ❌ БЫЛО (неправильно):
const handleLocationSelect = (lat, lon) => {
  setGeoLocation({ lat, lon })
  if (!address) {
    setAddress(`${lat}, ${lon}`) // Автозаполнение
  }
}

// ✅ СТАЛО (правильно):
const handleLocationSelect = (lat, lon) => {
  setGeoLocation({ lat, lon })
  // Адрес НЕ трогаем — пользователь сам введёт текст
}
```

**Почему так:**
- Текстовый адрес нужен для понимания ("ул. Пушкина, д. 10, кв. 5, домофон 123")
- Координаты нужны для GPS-навигации
- Это **независимые поля** — курьер может указать оба или только одно
- Автозаполнение адреса координатами создавало путаницу

**Поддерживаемые сценарии:**
1. Только текстовый адрес (старый способ)
2. Только координаты (быстрое создание заказа)
3. **Текстовый адрес + координаты** (рекомендуется)

---

### 4. Карточка заказа — отображение геолокации

**Файл:** `frontend/courier/src/components/OrderCard/OrderCard.jsx`

**Свёрнутое состояние (одна строка):**

```javascript
<div className="address-truncated">
  {order.latitude && order.longitude && order.address 
    ? `📍 | ${order.address}`  // Есть оба → иконка + адрес
    : order.address || '📍 Локация'}  // Только адрес или только координаты
</div>
```

**Развёрнутое состояние (детали):**

```javascript
<div className="detail-section detail-row">
  <div className="detail-col">
    <div className="detail-label">Адрес</div>
    <div className="detail-value">
      {order.address || 'Адрес не указан'}
    </div>
  </div>
  {order.latitude && order.longitude && (
    <a
      href={`https://www.google.com/maps/search/?api=1&query=${order.latitude},${order.longitude}`}
      target="_blank"
      className="call-button"
      style={{ background: 'var(--blue)' }}
    >
      📍 Локация
    </a>
  )}
</div>
```

**Почему кнопка стилизована как "📞 Позвонить":**
- Единообразие UI — обе кнопки справа от текста
- Класс `.call-button` уже имеет правильные отступы и размеры
- Синий цвет (`var(--blue)`) отличает от зелёной кнопки звонка

**Логика отображения:**

| Что есть в заказе | Свёрнутое | Развёрнутое |
|-------------------|-----------|-------------|
| Адрес + координаты | `📍 \| ул. Пушкина, д. 10` | Адрес слева, кнопка "📍 Локация" справа |
| Только адрес | `ул. Пушкина, д. 10` | Адрес слева, кнопки нет |
| Только координаты | `📍 Локация` | "Адрес не указан", кнопка "📍 Локация" справа |

---

### 5. Пул заказов — упрощение интерфейса

**Файл:** `frontend/courier/src/pages/Pool.jsx`

**Что убрано:**
- Блок "Новый заказ от клиента" (строки 86-100)
- Импорт `CreateOrderModal`
- State `showCreate`
- Модальное окно создания заказа

**Почему убрано:**
- Создание заказа теперь через отдельную страницу `/order/create`
- Модальное окно было временным решением
- Упрощение навигации — одна точка входа для создания заказа

---

## Технические детали

### Округление координат

**Проблема:** JavaScript может хранить координаты с избыточной точностью (например, 41.31115123456789), что вызывает ошибку валидации Django (`max 6 digits after decimal`).

**Решение:**
```javascript
const lat = parseFloat(position.coords.latitude.toFixed(6))
const lon = parseFloat(position.coords.longitude.toFixed(6))
```

**Почему `parseFloat()` после `toFixed()`:**
- `toFixed(6)` возвращает **строку** "41.311151"
- `parseFloat()` преобразует обратно в число 41.311151
- Без `parseFloat()` в JSON уйдёт строка, что вызовет ошибку на backend

### Размер бандла

```
Before: 434.22 KB (129.58 KB gzip)
After:  427.70 KB (127.67 KB gzip)
```

**Почему уменьшился:**
- Убран `CreateOrderModal` из `Pool.jsx`
- Leaflet добавлен только в `LocationPicker` (lazy loading через динамический импорт)

### Стили Leaflet

**Файл:** `frontend/courier/src/index.css`

```css
/* ── Leaflet Map Styles ──────────────────────────────────────────────────── */
.leaflet-container {
  font-family: var(--font);
}

.leaflet-popup-content-wrapper {
  border-radius: 8px;
}

.leaflet-popup-content {
  font-size: 14px;
}
```

**Почему нужны кастомные стили:**
- Leaflet использует свой шрифт по умолчанию
- Popup-окна имеют квадратные углы (не соответствуют дизайну)
- Размер шрифта в popup слишком большой для мобильного

---

## Связи с другими модулями

### Backend (Django)

**Модель Order** (`apps/logistics/models.py`) уже имеет поля:
```python
client_address = models.CharField(max_length=255, null=True, blank=True)
latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
```

**API endpoint** (`apps/bot_bridge/views.py`):
```python
class OrderCreateView(APIView):
    def post(self, request):
        # Принимает client_lat, client_lon
        # Сохраняет в Order.latitude, Order.longitude
```

### Frontend (React)

**Компоненты:**
- `LocationPicker.jsx` — интерактивная карта (новый)
- `OrderCreate.jsx` — форма создания заказа (обновлён)
- `OrderCard.jsx` — карточка заказа (обновлён)
- `Pool.jsx` — пул заказов (упрощён)

**Зависимости:**
- `react-leaflet` — React-обёртка для Leaflet
- `leaflet` — библиотека карт (OpenStreetMap)

---

## Известные ограничения

### 1. Точность геолокации

HTML5 Geolocation API зависит от:
- GPS (точность ~5-10 метров)
- Wi-Fi (точность ~20-50 метров)
- Сотовые вышки (точность ~100-1000 метров)

**Решение:** Курьер может скорректировать позицию кликом по карте.

### 2. Разрешения браузера

Если пользователь запретил доступ к геолокации:
- Карта откроется на координатах Ташкента (41.311151, 69.279737)
- Курьер может вручную найти место на карте

### 3. Offline-режим

Leaflet требует интернет для загрузки тайлов карты. В offline-режиме карта не работает.

**Возможное улучшение:** Кэширование тайлов через Service Worker (не реализовано).

---

## Как не допустить ошибок

### ❌ Частая ошибка: Автозаполнение адреса координатами

```javascript
// НЕПРАВИЛЬНО:
if (!address) {
  setAddress(`${lat}, ${lon}`)
}
```

**Почему плохо:**
- Координаты в поле адреса выглядят непонятно для пользователя
- Курьер не может добавить детали (квартира, домофон)
- Смешивание двух независимых полей

### ✅ Правильно: Независимые поля

```javascript
// Адрес — отдельно
<input value={address} onChange={(e) => setAddress(e.target.value)} />

// Координаты — отдельно
{geoLocation && (
  <div>✓ Координаты: {geoLocation.lat}, {geoLocation.lon}</div>
)}
```

### ❌ Частая ошибка: Забыть parseFloat() после toFixed()

```javascript
// НЕПРАВИЛЬНО:
const lat = position.coords.latitude.toFixed(6) // Строка!

// ПРАВИЛЬНО:
const lat = parseFloat(position.coords.latitude.toFixed(6)) // Число
```

---

## Связанные концепции

- [[Concepts/ReactLeaflet|React Leaflet]] — интеграция Leaflet с React
- [[Concepts/HTML5Geolocation|HTML5 Geolocation API]] — как работает navigator.geolocation
- [[Modules/Clients|Модуль Clients]] — модель Client с полями latitude/longitude

---

## Дальнейшие улучшения

### 1. Обратное геокодирование (Reverse Geocoding)

**Идея:** При выборе точки на карте автоматически получать текстовый адрес через API (Nominatim, Google Geocoding).

**Плюсы:**
- Курьер не вводит адрес вручную
- Адрес всегда соответствует координатам

**Минусы:**
- Требует API-ключ (Google) или rate-limiting (Nominatim)
- Адрес может быть неточным (например, "Unnamed Road")

### 2. Сохранение последней позиции курьера

**Идея:** При открытии карты центрировать на последней известной позиции курьера (из предыдущего заказа).

**Реализация:**
- Сохранять `lastKnownPosition` в localStorage
- Использовать как `initialPosition` для LocationPicker

### 3. Маршрут до клиента

**Идея:** Показывать маршрут от текущей позиции курьера до места доставки.

**Реализация:**
- Использовать Leaflet Routing Machine
- Интеграция с OSRM (Open Source Routing Machine)

---

## Итог

Система геолокации реализована с учётом реальных потребностей курьеров:
- ✅ Быстрое определение текущей позиции
- ✅ Точный выбор места на карте
- ✅ Гибридная поддержка текстового адреса и GPS-координат
- ✅ Удобная навигация через Google Maps

**Ключевое решение:** Текстовый адрес и координаты — независимые поля. Это даёт максимальную гибкость и избегает путаницы.
