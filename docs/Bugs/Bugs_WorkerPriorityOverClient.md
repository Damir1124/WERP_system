# Баг: Дубль Client для работника при прямом входе в клиентский Mini App

## Симптом

Launcher корректно определял роль через [`resolve_user_role()`](../../apps/bot_bridge/utils.py:82) — Worker искался **первым**, поэтому приоритет работника над клиентом работал. Но было две проблемы:

### Проблема 1: дубль Client при прямом входе

1. Работник (курьер/оператор/владелец) открывал клиентский Mini App **напрямую** (например, по старой ссылке или из истории Telegram).
2. Клиентский фронтенд вызывал `POST /api/bot/client/register/` (бесшовный вход по tg_id).
3. [`ClientRegisterView`](../../apps/bot_bridge/views.py:1397) не проверял таблицу `Worker` и создавал **дубль Client** с тем же `tg_id`.

В результате в базе появлялся «мусорный» клиент, который дублировал работника. Приоритет Worker в `resolve_user_role()` продолжал работать, но данные засорялись, а при будущих изменениях логики (например, если приоритет случайно поменяется) работник мог «превратиться» в клиента.

### Проблема 2 (реальный кейс): разные tg_id у Worker и Client

У пользователя в базе оказались **два разных Telegram ID**:

| Сущность | Имя | tg_id | Что открывалось |
|----------|-----|-------|-----------------|
| Worker (id=10, courier) | Damir | `754549459` | Курьерский Mini App |
| Client (id=120) | Damir | `754549457` | Клиентский Mini App |

Настоящий ID пользователя — `754549457`. Он был привязан только к **Client**, поэтому Launcher корректно открывал клиентский Mini App — приоритет Worker не мог сработать, потому что у этого ID **не было** записи в Worker. Ошибочный ID `754549459` был записан у Worker.

**Решение:** исправлен tg_id у Worker id=10 на `754549457`. После этого `resolve_user_role(754549457)` возвращает `COURIER` → `target_app: courier`.

## Причина

**Два независимых контура идентификации не были согласованы:**

| Контур | Функция | Что делает |
|--------|---------|------------|
| Определение роли | [`resolve_user_role()`](../../apps/bot_bridge/utils.py:82) | Worker → Client → UNKNOWN (приоритет Worker ✅) |
| Регистрация клиента | [`ClientRegisterView`](../../apps/bot_bridge/views.py:1397) | Создаёт Client по tg_id **без проверки Worker** ❌ |

`resolve_user_role()` — это «единый источник истины» о роли, но `ClientRegisterView` его не использовал. Он слепо создавал клиента, не спрашивая: «а не является ли этот tg_id уже сотрудником?».

## Где в коде

- [`apps/bot_bridge/utils.py`](../../apps/bot_bridge/utils.py:100) — `resolve_user_role()`: Worker ищется первым (правильно).
- [`apps/bot_bridge/views.py`](../../apps/bot_bridge/views.py:1420) — `ClientRegisterView.post()`: создание Client без проверки Worker (проблема).
- [`frontend/client/src/App.jsx`](../../frontend/client/src/App.jsx:83) — `loginByTgId()`: не обрабатывал ответ `status: 'worker'`.

## Решение

### 1. Бэкенд — защита от дубля в `ClientRegisterView`

**ДО (проблемный код):**
```python
existing = Client.objects.filter(tg_id=tg_id).first()
if existing:
    return Response({... 'status': 'exists', ...})

# Создаём клиента по tg_id с именем из Telegram (или заглушкой)
client = Client.objects.create(tg_id=tg_id, name=client_name, phone='')
```

**ПОСЛЕ (исправление):**
```python
# Приоритет работника: если tg_id уже привязан к Worker — не создаём
# дубль Client. Пользователь является сотрудником, а не клиентом.
worker = Worker.objects.filter(tg_id=tg_id).first()
if worker:
    return Response({
        'status': 'worker',
        'message': 'Пользователь является сотрудником',
        'worker_id': worker.id,
        'name': worker.full_name,
        'registered': False,
    })

existing = Client.objects.filter(tg_id=tg_id).first()
if existing:
    return Response({... 'status': 'exists', ...})

client = Client.objects.create(tg_id=tg_id, name=client_name, phone='')
```

### 2. Фронтенд — обработка ответа `status: 'worker'`

В [`frontend/client/src/App.jsx`](../../frontend/client/src/App.jsx:83) при ответе `status: 'worker'` клиентский Mini App перенаправляет пользователя обратно в Launcher:

```jsx
if (data.status === 'worker') {
  window.location.href = '/static/miniapp/launcher/index.html'
  return
}
```

Launcher повторно вызовет `/api/bot/identify/` и отправит работника в правильный Mini App (courier / operator / owner).

### 3. Тесты

В [`tests/bot_bridge/test_identify.py`](../../tests/bot_bridge/test_identify.py) добавлен `test_client_register_worker_priority`:

```python
def test_client_register_worker_priority(self):
    """Регистрация клиента не создаёт дубль для работника (приоритет Worker)"""
    response = self.client.post(reverse('bot_bridge:client_register'),
                                {'name': 'Дубль', 'tg_id': 1001}, format='json')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(data['status'], 'worker')
    self.assertFalse(Client.objects.filter(tg_id=1001).exists())
```

Также обновлены устаревшие тесты:
- `test_unknown_returns_registration` → `test_unknown_returns_client_app` (актуальное поведение: неизвестный идёт в клиентский Mini App для бесшовного входа по tg_id).
- `test_client_registration_binds_tg_id` — регистрация теперь без телефона (по tg_id).

## Как не допустить снова

**Правило:** любая операция, которая создаёт или определяет сущность по `tg_id`, обязана проходить через единый источник истины — [`resolve_user_role()`](../../apps/bot_bridge/utils.py:82). Если функция определяет роль как `WORKER` — никакой другой код не должен создавать `Client` для этого же `tg_id`.

Порядок приоритета (закреплён в docstring функции):

```
Worker (любой worker_type) → Client → UNKNOWN (бесшовный вход в клиентский Mini App)
```

## Связанные концепции

- [[Concepts_TelegramBotAuth|Авторизация Telegram бота через tg_id]]
- [[Concepts_TelegramMiniApp|Telegram Mini App (TWA)]]
- [[Feature_Launcher|Launcher — единая точка входа в Mini App]]