"""
Сервисы логистики.

Содержит:
1. Декоративные номера заказов (Order.display_number) — 1–999 с циклическим
   переиспользованием и select_for_update() для безопасной параллельной выдачи.
2. Парсинг и агрегацию адресов общежития (блок/этаж/комната) для скрытой
   команды курьера «сводка по адресам».

Пример декоративного номера:
    from apps.logistics.services import create_order_with_display_number

    order = create_order_with_display_number(
        client=client,
        payment_type=Order.PaymentType.CASH,
        status=Order.Status.PENDING,
    )
"""

import logging
import re

from django.db import transaction
from django.db.models import F

from apps.logistics.models import Order, OrderNumberCounter

logger = logging.getLogger(__name__)

MAX_DISPLAY_NUMBER = 999


def get_next_display_number() -> int:
    """Вернуть следующий декоративный номер (1–999) атомарно.

    Блокирует строку счётчика через select_for_update() —
    два одновременных вызова получат разные номера.
    """
    with transaction.atomic():
        # select_for_update блокирует строку до конца транзакции
        counter = OrderNumberCounter.objects.select_for_update().first()

        if counter is None:
            # Первый запуск — создаём запись счётчика
            counter = OrderNumberCounter.objects.create(current_number=0)

        # Вычисляем следующий номер
        next_number = counter.current_number + 1
        if next_number > MAX_DISPLAY_NUMBER:
            next_number = 1

        # Обновляем счётчик напрямую через F(), чтобы избежать гонок
        OrderNumberCounter.objects.filter(pk=counter.pk).update(
            current_number=next_number
        )

        logger.debug(
            "Display number issued: %d (counter was %d)",
            next_number, counter.current_number,
        )

        return next_number


def create_order_with_display_number(**kwargs) -> Order:
    """Создать Order с автоматически заполненным display_number.

    Все точки создания заказа должны использовать эту функцию
    вместо прямого Order.objects.create() — иначе заказы
    могут остаться без декоративного номера.

    Параллельные вызовы безопасны благодаря select_for_update().
    """
    display_number = get_next_display_number()
    kwargs['display_number'] = display_number
    order = Order.objects.create(**kwargs)
    logger.info(
        "Order #%s created with display_number=N%03d",
        order.id, display_number,
    )
    return order


# Парсинг и агрегация адресов общежития (блок/этаж/комната)
#
# Стандарт ввода адреса общежития:
#   «Блок A, 3 этаж, комната 12»
#   «Блок B 5 эт. комн. 7»
#   «Корпус 2, 4 этаж, кв 15»
#   «A 3 12»
# Блок — латинская буква A–Z или цифра; этаж и комната — целые числа.
# Разделители любые (запятая, пробел, точка, дефис).
# Синонимы: блок/корпус/подъезд, этаж/эт., комната/комн./кв./№.

# Регулярки для извлечения полей адреса.
# Блок: слово «блок/корпус/подъезд» + буква/цифра, либо одиночная буква A–Z в начале.
_RE_BLOCK = re.compile(
    r'(?:блок|корпус|подъезд|б)\s*([a-zа-я]|\d{1,2})|^([a-z])',
    re.IGNORECASE,
)
# Этаж: число до или после слова «этаж/эт.» (стандарт: «3 этаж»).
_RE_FLOOR = re.compile(
    r'(\d{1,2})\s*(?:этаж|эт\.?|этаже)|(?:этаж|эт\.?|этаже)\s*(\d{1,2})',
    re.IGNORECASE,
)
# Комната: слово «комната/комн./кв./№» + число.
_RE_ROOM = re.compile(
    r'(?:комнат|комн\.?|кв\.?|квартир|№)\s*(\d{1,4})',
    re.IGNORECASE,
)


def parse_dormitory_address(text: str) -> dict | None:
    """Разобрать адрес общежития на блок/этаж/комнату.

    Возвращает dict {'block', 'floor', 'room'} или None, если адрес пуст.
    Поля, которые не удалось распознать, равны None — такой заказ
    считается «неагрегированным» и выводится отдельно.

    Примеры:
        parse_dormitory_address('Блок A, 3 этаж, комната 12')
        # -> {'block': 'A', 'floor': 3, 'room': 12}
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    block = None
    m = _RE_BLOCK.search(text)
    if m:
        # Блок может быть в группе 1 (после слова) или группе 2 (голая буква в начале)
        raw = (m.group(1) or m.group(2) or '').strip()
        if raw:
            # Буква — оставляем как есть (верхний регистр), цифра — int
            block = raw.upper() if raw.isalpha() else int(raw)

    floor = None
    m = _RE_FLOOR.search(text)
    if m:
        # Число может быть до слова (группа 1) или после (группа 2)
        floor = int(m.group(1) or m.group(2))

    room = None
    m = _RE_ROOM.search(text)
    if m:
        room = int(m.group(1))

    # Компактный формат «A 3 12»: блок буквой, затем два числа (этаж, комната).
    # Срабатывает только если блок распознан, а этаж/комната ещё не найдены.
    if block is not None and (floor is None or room is None):
        numbers = re.findall(r'\d{1,4}', text)
        if len(numbers) >= 2:
            if floor is None:
                floor = int(numbers[0])
            if room is None:
                room = int(numbers[1])

    return {'block': block, 'floor': floor, 'room': room}


def get_order_water_qty(order) -> int:
    """Суммарное количество воды 19л (тип продукта 19W) в заказе.

    Принимает объект Order (с prefetch items__product) либо dict из
    OrderSerializer (items с product_type).
    """
    from apps.products.models import Product

    # dict из сериализатора: items = [{'product_type': ..., 'quantity': ...}]
    if isinstance(order, dict):
        items = order.get('items') or []
        total = 0
        for item in items:
            if isinstance(item, dict):
                if item.get('product_type') == Product.TypeProduct.WATER:
                    total += int(item.get('quantity') or 0)
            else:
                if item.product.type_product == Product.TypeProduct.WATER:
                    total += int(item.quantity or 0)
        return total

    # Объект Order: items — QuerySet объектов OrderItem
    items = getattr(order, 'items', None)
    if items is not None:
        return sum(
            item.quantity
            for item in items.all()
            if item.product.type_product == Product.TypeProduct.WATER
        )
    return 0


def aggregate_orders_by_address(orders) -> dict:
    """Сгруппировать заказы по адресу общежития (блок → этаж → комнаты).

    Двухуровневая агрегация:
    - по этажу — общее кол-во воды на этаж (water_qty);
    - по комнатам — сколько шт в каждой комнате (rooms).

    Принимает итерируемый объект заказов (Order или dict из сериализатора).
    Возвращает dict:
        {
            'groups': [
                {
                    'block': 'A', 'floor': 3,
                    'water_qty': 12,          # общее кол-во воды на этаж
                    'rooms': [
                        {'room': 12, 'water_qty': 5},
                        {'room': 15, 'water_qty': 7},
                    ],
                    'orders': [<order>, ...],
                },
                ...
            ],
            'unparsed': [<order>, ...],   # заказы без распознанного адреса
        }

    Группы отсортированы по блоку, затем этажу; комнаты — по номеру.
    """
    groups: dict[tuple, dict] = {}
    unparsed: list = []

    for order in orders:
        address = getattr(order, 'delivery_address_text', None)
        if isinstance(order, dict):
            address = order.get('delivery_address_text') or order.get('client_address')

        parsed = parse_dormitory_address(address or '')
        water_qty = get_order_water_qty(order)

        # Для агрегации нужны блок и этаж (комната не обязательна)
        if not parsed or parsed['block'] is None or parsed['floor'] is None:
            unparsed.append(order)
            continue

        key = (parsed['block'], parsed['floor'])
        group = groups.setdefault(
            key,
            {
                'block': parsed['block'],
                'floor': parsed['floor'],
                'water_qty': 0,
                'rooms': {},
                'orders': [],
            },
        )
        group['water_qty'] += water_qty
        group['orders'].append(order)

        # Детализация по комнатам (если комната распознана)
        if parsed['room'] is not None:
            room_key = parsed['room']
            group['rooms'][room_key] = group['rooms'].get(room_key, 0) + water_qty

    sorted_groups = sorted(
        groups.values(),
        key=lambda g: (str(g['block']), g['floor']),
    )
    for g in sorted_groups:
        g['rooms'] = [
            {'room': room, 'water_qty': qty}
            for room, qty in sorted(g['rooms'].items())
        ]

    return {'groups': sorted_groups, 'unparsed': unparsed}