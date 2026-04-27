# Концепция: WebSockets и Django Channels

**Назначение:** Живой мониторинг и уведомления в реальном времени.

## Архитектура
1. **Django Channels** - обработка WebSocket соединений
2. **Redis** - бэкенд для channel layers
3. **ASGI** - асинхронный сервер

## Использование в Osnova 2.0

### 1. Мониторинг доставок
```python
# consumers.py
class DeliveryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "delivery_updates",
            self.channel_name
        )
        await self.accept()
    
    async def delivery_update(self, event):
        await self.send(text_data=json.dumps(event))
```

### 2. Уведомления для админа
```python
# signals.py
@receiver(post_save, sender=FinancialTransactions)
async def notify_admin_on_transaction(sender, instance, created, **kwargs):
    if created:
        await channel_layer.group_send(
            "admin_dashboard",
            {
                "type": "transaction.created",
                "amount": instance.amount,
                "transaction_type": instance.transaction_type
            }
        )
```

### 3. Геолокация курьеров
```python
# bot_bridge/views.py
@api_view(['POST'])
def update_courier_location(request):
    courier = get_courier_by_tg_id(request.headers.get('X-Telegram-ID'))
    courier.latitude = request.data['lat']
    courier.longitude = request.data['lng']
    courier.save()
    
    # Отправить обновление через WebSocket
    async_to_sync(channel_layer.group_send)(
        f"courier_{courier.id}",
        {"type": "location.updated", "location": request.data}
    )
```

## Настройка
1. Установить зависимости:
```bash
pip install channels channels-redis
```

2. Настроить `asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/delivery/', DeliveryConsumer.as_asgi()),
        ])
    ),
})
```

3. Добавить в `settings.py`:
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

## Преимущества
- Мгновенные обновления в админке
- Отслеживание курьеров на карте
- Уведомления о новых заказах

[[Index]] | [[Concepts_DjangoSignals]] | [[Modules_BotBridge]]