# Функция: Закрытие рейса с автоматическим переносом заказов

> Дата реализации: 2026-06-21  
> Статус: ✅ Реализовано и протестировано

## Зачем эта функция

Курьер должен иметь возможность завершить рейс в любой момент, даже если остались недоставленные заказы. Система автоматически переносит незавершённые заказы в следующий рейс, чтобы они не потерялись и не требовали ручного переназначения.

**Бизнес-сценарий:**
1. Курьер загрузил 20 баклажек, взял 15 заказов
2. Доставил 12 заказов, 3 клиента не ответили
3. Курьер закрывает рейс → 3 недоставленных заказа автоматически открепляются
4. На следующий день курьер открывает новый рейс → эти 3 заказа автоматически подхватываются

## Frontend: Экран закрытия рейса

### Компонент TripClose.jsx

**Путь:** `frontend/courier/src/pages/TripClose.jsx`

**Маршрут:** `/trip/close`

**Структура экрана:**

```
┌─────────────────────────────────────┐
│  📋 Итоги рейса #42                 │ ← Градиентный заголовок (#1450A3)
├─────────────────────────────────────┤
│                                     │
│  📦 Баклажки                        │
│  Загружено         20 бак           │ ← Цвет #1450A3
│  Доставлено        12 бак           │ ← Зелёный
│  Осталось в машине  8 бак           │ ← Синий
│                                     │
│  📭 Тара                            │
│  Пустых собрано     3 шт            │ ← Пульсирующий жёлтый (#fcd34d)
│                                     │
│  ┌───────────────────────────────┐  │
│  │ 📭 При выгрузке на склад      │  │ ← Синий блок-напоминание
│  │    сдайте 3 пустых баклажек   │  │
│  └───────────────────────────────┘  │
│                                     │
│  💰 Финансы                         │
│  💵 Наличные    450,000 сум         │ ← Зелёный
│  💳 Карта       120,000 сум         │ ← Синий (скрыт если 0)
│  ─────────────────────────────────  │
│  Итого          570,000 сум         │ ← Жирный, 20px
│                                     │
│  [✅ Закрыть рейс]                  │ ← Primary button
│  [← Назад]                          │ ← Secondary button
│                                     │
└─────────────────────────────────────┘
```

### Дизайн-решения

**1. Градиентный заголовок**
```jsx
background: 'linear-gradient(135deg, #1450A3 0%, #0d3a70 100%)'
```
Почему: Визуально отделяет экран закрытия от обычного рейса, создаёт ощущение "финальной точки".

**2. Пульсирующая анимация для пустых баклажек**
```css
@keyframes pulse {
  0%, 100% {
    opacity: 0.7;
    text-shadow: 0 0 4px rgba(252, 211, 77, 0.4);
    transform: scale(1);
  }
  50% {
    opacity: 1;
    text-shadow: 0 0 20px rgba(252, 211, 77, 1), 0 0 30px rgba(252, 211, 77, 0.6);
    transform: scale(1.05);
  }
}
```
Почему: Привлекает внимание к важной информации — курьер должен не забыть сдать пустые баклажки на склад.

**3. Блок напоминания (не предупреждение)**
```jsx
background: 'rgba(96, 165, 250, 0.1)'  // Синий, не жёлтый
```
Почему: Это не ошибка и не предупреждение — это просто напоминание. Жёлтый цвет создавал бы ложное ощущение проблемы.

### Передача данных через React Router state

**В Trip.jsx:**
```jsx
navigate('/trip/close', {
  state: {
    summary: {
      full_loaded: summary.full_loaded ?? 0,
      delivered: summary.delivered ?? 0,
      full_remain: summary.full_remain ?? 0,
      empty_received: summary.empty_expected ?? 0,  // API возвращает empty_expected
    },
    financials: {
      cash_expected: summary.cash_expected ?? 0,
      card_expected: summary.card_expected ?? 0,
    },
    tripId: trip?.id,
  }
})
```

**Почему через state, а не через API-запрос:**
- Данные уже загружены на странице Trip.jsx
- Не нужен дополнительный запрос к серверу
- Мгновенный переход без задержки на загрузку

**Защита от прямого перехода:**
```jsx
if (!tripId) {
  navigate('/trip', { replace: true })
  return null
}
```

## Backend: API закрытия рейса

### Endpoint: TripCloseView

**Путь:** `apps/bot_bridge/views.py`

**URL:** `POST /api/bot/courier/trips/{pk}/close/`

**Логика:**

```python
def post(self, request, pk):
    courier = request.courier
    trip = get_object_or_404(CourierTrip, pk=pk)
    
    # 1. Проверка принадлежности
    if trip.shift.courier.tg_id != courier.tg_id:
        return Response({'error': 'Этот рейс принадлежит другому курьеру'}, 403)
    
    # 2. Проверка статуса
    if trip.status != CourierTrip.Status.ACTIVE:
        return Response({'error': 'Рейс уже закрыт'}, 400)
    
    # 3. Открепление незавершённых заказов
    pending_orders = trip.orders.filter(status=Order.Status.PENDING)
    pending_count = pending_orders.count()
    pending_orders.update(trip=None)  # Открепляем от рейса
    
    # 4. Закрытие рейса
    trip.status = CourierTrip.Status.DONE
    trip.finished_at = timezone.now()
    trip.save()
    
    return Response({
        'success': True,
        'finished_at': trip.finished_at.isoformat(),
        'pending_transferred': pending_count,
    })
```

### Почему незавершённые заказы НЕ блокируют закрытие

**Альтернативный подход (отклонён):**
```python
if pending_orders.exists():
    return Response({'error': 'Сначала доставьте все заказы'}, 400)
```

**Проблемы этого подхода:**
1. Курьер не может закрыть рейс если клиент не отвечает
2. Заказы "застревают" в рейсе до конца смены
3. Курьер не может начать новый рейс с новыми заказами

**Наш подход:**
- Открепляем заказы от рейса (`trip=None`)
- Они остаются назначенными на курьера (`assigned_courier` не меняется)
- При открытии нового рейса автоматически подхватываются

## Backend: Автоматический перенос заказов

### Дополнение CourierTripListView.post()

**Путь:** `apps/bot_bridge/views.py`

**URL:** `POST /api/bot/courier/trips/` (открытие нового рейса)

**Добавленная логика:**

```python
def post(self, request):
    # ... создание рейса ...
    trip = CourierTrip.objects.create(
        shift=active_shift,
        full_loaded=full_loaded,
        status=CourierTrip.Status.ACTIVE
    )
    
    # Переносим "осиротевшие" заказы
    orphan_orders = Order.objects.filter(
        trip=None,                          # Открепились от предыдущего рейса
        assigned_courier=courier,           # Назначены на этого курьера
        status=Order.Status.PENDING         # Ещё не доставлены
    )
    transferred_count = orphan_orders.count()
    orphan_orders.update(trip=trip)         # Привязываем к новому рейсу
    
    return Response({
        'message': 'Рейс открыт',
        'trip': serializer.data,
        'transferred_orders': transferred_count  # Сколько заказов перенесено
    })
```

### Почему это работает

**Жизненный цикл заказа:**

```
1. Создание заказа
   ├─ status = PENDING
   ├─ trip = None
   └─ assigned_courier = None

2. Курьер берёт заказ из пула
   ├─ assigned_courier = courier
   └─ trip = current_trip

3. Курьер закрывает рейс (заказ не доставлен)
   ├─ trip = None              ← Открепляется
   └─ assigned_courier = courier  ← Остаётся!

4. Курьер открывает новый рейс
   └─ trip = new_trip          ← Автоматически подхватывается
```

**Ключевое отличие:**
- `trip` — временная привязка к конкретному рейсу
- `assigned_courier` — постоянная привязка к курьеру до доставки

## Полный цикл работы

### Сценарий 1: Успешная доставка всех заказов

```
1. Курьер открывает рейс → загружает 20 баклажек
2. Берёт 15 заказов из пула → assigned_courier=курьер, trip=рейс_1
3. Доставляет все 15 заказов → status=DELIVERED
4. Закрывает рейс → pending_transferred=0
```

### Сценарий 2: Частичная доставка

```
1. Курьер открывает рейс_1 → загружает 20 баклажек
2. Берёт 15 заказов из пула
3. Доставляет 12 заказов → status=DELIVERED
4. 3 клиента не отвечают → status=PENDING
5. Закрывает рейс_1 → pending_transferred=3, эти заказы: trip=None
6. На следующий день открывает рейс_2 → transferred_orders=3
7. Эти 3 заказа автоматически в рейсе_2
```

### Сценарий 3: Переназначение заказа

```
1. Курьер_А берёт заказ → assigned_courier=А, trip=рейс_А1
2. Курьер_А закрывает рейс → trip=None, assigned_courier=А
3. Диспетчер переназначает заказ на Курьера_Б → assigned_courier=Б
4. Курьер_Б открывает рейс → заказ подхватывается в рейс_Б1
```

## Связанные концепции

- [[Concepts_OrderItem]] — структура заказов с несколькими продуктами
- [[Feature_ShiftManagement]] — управление сменами и рейсами
- [[Modules_Logistics]] — модели CourierShift, CourierTrip, Order

## Технические детали

### API методы

**Frontend (`api.js`):**
```javascript
closeTrip: (tripId) => apiFetch(`/courier/trips/${tripId}/close/`, { method: 'POST' })
```

**Backend (`urls.py`):**
```python
path('courier/trips/<int:pk>/close/', views.TripCloseView.as_view(), name='trip_close')
```

### Навигация после закрытия

```jsx
await api.closeTrip(tripId)
navigate('/shift', { replace: true })  // replace: true — нельзя вернуться назад
```

**Почему `replace: true`:**
- Рейс уже закрыт, возврат на экран закрытия бессмысленен
- Предотвращает повторное нажатие "Закрыть рейс"
- Кнопка "Назад" в браузере ведёт на страницу смены, а не на закрытый рейс

## Будущие улучшения

1. **Уведомление диспетчера** — когда курьер закрывает рейс с незавершёнными заказами
2. **Причина незавершения** — курьер может указать причину (клиент не отвечает, неверный адрес и т.д.)
3. **Автоматическое переназначение** — если заказ не доставлен 2 дня подряд, система предлагает переназначить на другого курьера
4. **Статистика переносов** — сколько раз заказ переносился между рейсами

## Тестирование

### Ручное тестирование

1. Открыть смену и рейс
2. Взять несколько заказов из пула
3. Доставить часть заказов
4. Нажать "Завершить рейс"
5. Проверить, что недоставленные заказы открепились (`trip=None`)
6. Открыть новый рейс
7. Проверить, что заказы автоматически подхватились

### Проверка в админке Django

```python
# Проверить открепление
Order.objects.filter(trip=None, assigned_courier__isnull=False, status='PENDING')

# Проверить перенос
trip = CourierTrip.objects.last()
trip.orders.filter(status='PENDING').count()
```
