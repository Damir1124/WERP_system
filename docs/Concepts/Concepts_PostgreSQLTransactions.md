# Концепция: PostgreSQL транзакции и select_for_update

## Зачем это нужно в нашем проекте

В WERP есть несколько мест, где два одновременных запроса не должны выдать один и тот же результат:

1. **Декоративные номера заказов** — [`get_next_display_number()`](apps/logistics/services.py:27) не должен выдать номер 42 двум разным заказам.
2. Списание остатков со склада — два курьера одновременно подтверждают доставку, остаток не должен уйти в минус.
3. Закрытие смены и параллельное создание заказа — суммы не должны «потеряться».

Для этого используется `select_for_update()` — блокировка строки на уровне БД.

## Как это работает (с нуля)

### Аналогия из реальной жизни

Представь очередь в одно окно. Каждый клиент подходит к окну, решает свою задачу и отходит. Пока один клиент у окна, остальные ждут.

`select_for_update()` — это «занять окно». Пока одна транзакция держит блокировку на строке, другая транзакция, пытающаяся заблокировать ту же строку, **ждёт**.

### Техническое объяснение

```python
from django.db import transaction

def get_next_number():
    with transaction.atomic():
        # 1. PostgreSQL блокирует строку на запись
        # 2. Другие транзакции, пытающиеся сделать то же самое, ждут
        counter = Counter.objects.select_for_update().first()
        
        # 3. Читаем значение
        next_num = counter.value + 1
        
        # 4. Пишем новое значение
        counter.value = next_num
        counter.save()
        
        # 5. Выход из transaction.atomic() → COMMIT → строка разблокирована
        return next_num
```

**Что происходит в БД (грубо):**

| Время | Транзакция A | Транзакция B |
|-------|-------------|-------------|
| T1 | `BEGIN` | `BEGIN` |
| T2 | `SELECT ... FOR UPDATE` — строка заблокирована | — |
| T3 | Читает: value=41 | `SELECT ... FOR UPDATE` — **ждёт** |
| T4 | Пишет: value=42 | ждёт |
| T5 | `COMMIT` — строка разблокирована | ждёт |
| T6 | — | Получает блокировку, читает: value=42 |
| T7 | — | Пишет: value=43, `COMMIT` |

Результат: A получила 42, B получила 43. Никакой гонки.

### Что если не использовать select_for_update?

```python
# БЕЗ блокировки — RACE CONDITION
def get_next_number_race():
    counter = Counter.objects.first()
    next_num = counter.value + 1   # Обе транзакции прочитают 41
    counter.value = next_num
    counter.save()                  # Обе запишут 42
    return next_num                 # Обе вернут 42 — ОШИБКА!
```

| Время | Транзакция A | Транзакция B |
|-------|-------------|-------------|
| T1 | Читает: value=41 | Читает: value=41 |
| T2 | Вычисляет: 42 | Вычисляет: 42 |
| T3 | Записывает: 42 | Записывает: 42 |
| T4 | — | Обе получили 42! |

## В нашем коде

### `get_next_display_number()` — декоративные номера

[`apps/logistics/services.py:27`](apps/logistics/services.py:27):

```python
def get_next_display_number() -> int:
    with transaction.atomic():
        counter = OrderNumberCounter.objects.select_for_update().first()
        if counter is None:
            counter = OrderNumberCounter.objects.create(current_number=0)
        next_number = counter.current_number + 1
        if next_number > 999:
            next_number = 1
        OrderNumberCounter.objects.filter(pk=counter.pk).update(
            current_number=next_number
        )
        return next_number
```

Особенности:
- Использует `update()` с фильтром по PK, а не `counter.save()` — это гарантирует атомарный UPDATE без лишнего чтения.
- Счётчик создаётся при первом вызове (lazy initialization).
- Максимальное значение 999, после чего сброс на 1.

### Почему `select_for_update()` а не `LOCK TABLE`

- `LOCK TABLE` блокирует **всю таблицу** — даже если там миллион строк. Это убивает производительность.
- `select_for_update()` блокирует **только одну строку**. Остальные строки таблицы доступны для чтения и записи.
- В нашем случае в таблице `OrderNumberCounter` всего одна строка — разница невелика, но это правильный паттерн.

### Почему не `F()` объект

`F()` позволяет атомарно увеличить счётчик без гонок:

```python
Counter.objects.update(value=F('value') + 1)
counter = Counter.objects.get()
```

Но мы не можем так сделать, потому что нам нужно **прочитать** новое значение после инкремента, а `F()` не возвращает результат. В PostgreSQL есть `RETURNING`, но Django ORM его не поддерживает в `update()`.

## Альтернативные подходы

### Оптимистичная блокировка (Optimistic Locking)

Добавить поле `version` в модель, читать его, а при записи проверять:

```python
counter = Counter.objects.get(id=1)
old_version = counter.version
counter.value += 1
counter.version += 1
updated = Counter.objects.filter(
    id=1, version=old_version
).update(value=counter.value, version=counter.version)
if updated == 0:
    # Конфликт — кто-то изменил строку раньше
    raise RetryNeeded()
```

**Плюсы:** не блокирует строку на чтение.
**Минусы:** требует повторной попытки (retry) при конфликте.

### Redis-счётчик

```python
import redis
r = redis.Redis()
next_number = r.incr('order_display_counter')
if next_number > 999:
    r.set('order_display_counter', 1)
    next_number = 1
```

**Плюсы:** очень быстро, не нагружает PostgreSQL.
**Минусы:** добавляет зависимость от Redis, при сбое Redis счётчик сбросится.

### Почему в WERP выбран `select_for_update`

- Простота — не нужен Redis, не нужны retry.
- Транзакционность — если создание заказа упадёт, счётчик **не откатится**. Это **правильно**: номер считается выданным, даже если заказ не создался. Если бы мы откатывали счётчик, то при повторной попытке номер был бы тот же, что могло бы запутать.
- Нагрузка минимальна — одна строка, одна транзакция, один `SELECT ... FOR UPDATE`.

## Ловушки и частые ошибки

### 1. `select_for_update()` работает только внутри `transaction.atomic()`

```python
# НЕПРАВИЛЬНО — вне транзакции select_for_update ничего не делает
counter = Counter.objects.select_for_update().first()

# ПРАВИЛЬНО
with transaction.atomic():
    counter = Counter.objects.select_for_update().first()
```

### 2. Блокировка держится до конца транзакции

```python
with transaction.atomic():
    counter = Counter.objects.select_for_update().first()
    # ... долгая операция ...
    # Всё это время строка заблокирована!
    # Другие транзакции ждут
```

Не делайте долгих операций внутри заблокированной транзакции — это приведёт к таймаутам.

### 3. `select_for_update()` блокирует только строки, которые вернул запрос

```python
# Блокирует строку с id=1
Counter.objects.filter(id=1).select_for_update().first()

# НЕ блокирует строку с id=2
Counter.objects.filter(id=2).select_for_update().first()
```

### 4. `select_for_update(nowait=True)` — не ждать, а сразу ошибка

```python
try:
    counter = Counter.objects.select_for_update(nowait=True).first()
except OperationalError:
    # Строка уже заблокирована
    pass
```

Полезно, когда вы не хотите ждать, а хотите сразу сказать пользователю «попробуйте позже».

## Связанные файлы

- [`apps/logistics/services.py`](apps/logistics/services.py) — реализация `get_next_display_number()`
- [`apps/logistics/models.py`](apps/logistics/models.py:377) — модель `OrderNumberCounter`
- [`tests/logistics/test_display_number.py`](tests/logistics/test_display_number.py) — тесты счётчика
- [Документация Django по select_for_update](https://docs.djangoproject.com/en/5.0/ref/models/querysets/#select-for-update)