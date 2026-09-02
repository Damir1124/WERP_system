# Баг: При авто-удалении 4-го адреса заказ теряет адрес («Адрес не указан»)

## Симптом
Когда у клиента уже 3 сохранённых адреса, и курьер (или клиент через Mini App) добавляет 4-й, система удаляет самый старый `ClientAddress` по лимиту «максимум 3». После этого заказы, которые были привязаны к удалённому адресу, в карточке/уведомлении показывают «Адрес не указан» — хотя по факту вода туда доставлялась.

## Причина
`Order.delivery_address` — это ForeignKey с `on_delete=models.SET_NULL` ([`apps/logistics/models.py`](apps/logistics/models.py:250)). Авто-удаление «лишнего» адреса по лимиту обнуляло эту ссылку, и исторический заказ терял адрес доставки. Адресная книга клиента (`ClientAddress`) — изменяемая справочная таблица, а заказ — исторический факт; хранить факт доставки как живую ссылку на справочник оказалось небезопасно.

> 💡 **Почему так вышло:** лимит «3 адреса» реализован жёстким `delete()` самого старого, без учёта того, что на адрес могут ссылаться заказы. FK с `SET_NULL` молча обнулял связь, и баг проявлялся только при просмотре старых заказов.

## Где в коде
- `apps/logistics/models.py:250` — `Order.delivery_address` (FK, `SET_NULL`)
- `apps/clients/views.py:173` — `save_client_address`: лимит `addresses.count() > 3` → `addresses.last().delete()`
- `apps/bot_bridge/serializers.py:296` — `OrderCreateModelSerializer.create()`: тот же лимит через `old_ids = ...[:extra-3]` → `delete()`
- `apps/bot_bridge/serializers.py:54` — `OrderSerializer` раньше читал `source='delivery_address.address_text'`

## Решение
Два слоя защиты:

**1. Снимок (snapshot) адреса прямо в `Order`.** Добавлены поля [`apps/logistics/models.py`](apps/logistics/models.py:258):
```python
delivery_address_text = models.CharField(max_length=120, blank=True, default='')
delivery_latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
delivery_longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
```
При создании заказа значения копируются из `ClientAddress` (или из сырых данных запроса, если адрес не привязан):
```python
# apps/bot_bridge/serializers.py (create)
if delivery_address:
    validated_data['delivery_address_text'] = delivery_address.address_text
    validated_data['delivery_latitude'] = delivery_address.latitude
    validated_data['delivery_longitude'] = delivery_address.longitude
```
То же сделано в `ClientOrderCreateView` ([`apps/bot_bridge/views.py`](apps/bot_bridge/views.py:1023)) и `OrderForm.save()` ([`apps/logistics/forms.py`](apps/logistics/forms.py:140)). `OrderSerializer` и `notify.py` теперь читают снимок `order.delivery_address_text`, а не `order.delivery_address.address_text`. Миграция `0007`.

**2. Защита лимита — не удалять адреса с заказами.** В обоих местах лимита добавлен фильтр `orders__isnull=True`:
```python
# ДО (проблемный код)
old_ids = list(client.addresses.order_by('last_used_at','created_at').values_list('id', flat=True)[:extra-3])
ClientAddress.objects.filter(id__in=old_ids).delete()

# ПОСЛЕ (исправление)
old_ids = list(
    client.addresses
    .filter(orders__isnull=True)          # не трогаем привязанные к заказам
    .order_by('last_used_at', 'created_at')
    .values_list('id', flat=True)[:extra - 3]
)
if old_ids:
    ClientAddress.objects.filter(id__in=old_ids).delete()
# если все 3 адреса заняты заказами — 4-й оставляем, привязанные не удаляем
```

## Как не допустить снова
1. **Исторические факты хранить снимком в самой записи**, а не живой ссылкой на изменяемую справочную таблицу. FK — для удобства (автоподстановка), снимок — для отображения/истории.
2. **Любое каскадное/авто-удаление по лимиту** должно проверять обратные ссылки (`orders__isnull=True`) и не трогать записи, на которые ссылаются другие сущности.
3. При добавлении поля-ссылки с `SET_NULL` сразу спросить: «а что будет с историей, если эту запись удалят?» — и при необходимости сделать снимок.

## Связанные концепции
- [[Modules_Logistics|Модуль Логистики]] — поля `delivery_address` (FK) и `delivery_address_text/lat/lon` (снимок)
- [[Modules_Clients|Модуль Клиентов]] — `ClientAddress`, лимит 3 адреса
- [[Bugs_OrderCardProps|Карточка «Локация»/«Адрес не указан»]] — тот же симптом, другая причина
