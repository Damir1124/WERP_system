"""
Тесты парсинга и агрегации адресов общежития (блок/этаж/комната).

Запуск: python manage.py test tests.logistics.test_dormitory_aggregation
"""

from django.test import TestCase

from apps.logistics.services import (
    parse_dormitory_address,
    aggregate_orders_by_address,
)


class ParseDormitoryAddressTest(TestCase):
    """Проверка парсера адреса общежития."""

    def test_full_standard_format(self):
        """Полный стандартный формат: «Блок A, 3 этаж, комната 12»."""
        result = parse_dormitory_address('Блок A, 3 этаж, комната 12')
        self.assertEqual(result, {'block': 'A', 'floor': 3, 'room': 12})

    def test_short_synonyms(self):
        """Сокращённые синонимы: «Блок B 5 эт. комн. 7»."""
        result = parse_dormitory_address('Блок B 5 эт. комн. 7')
        self.assertEqual(result, {'block': 'B', 'floor': 5, 'room': 7})

    def test_korpus_and_kv(self):
        """Корпус и кв.: «Корпус 2, 4 этаж, кв 15»."""
        result = parse_dormitory_address('Корпус 2, 4 этаж, кв 15')
        self.assertEqual(result, {'block': 2, 'floor': 4, 'room': 15})

    def test_compact_format(self):
        """Компактный формат: «A 3 12» — блок буквой, этаж и комната числами."""
        result = parse_dormitory_address('A 3 12')
        self.assertEqual(result, {'block': 'A', 'floor': 3, 'room': 12})

    def test_lowercase_block_normalized(self):
        """Блок в нижнем регистре приводится к верхнему."""
        result = parse_dormitory_address('блок c, 2 этаж, комната 5')
        self.assertEqual(result['block'], 'C')

    def test_empty_address_returns_none(self):
        """Пустой адрес возвращает None."""
        self.assertIsNone(parse_dormitory_address(''))
        self.assertIsNone(parse_dormitory_address('   '))
        self.assertIsNone(parse_dormitory_address(None))

    def test_missing_room_returns_none_room(self):
        """Если комната не распознана — поле room равно None."""
        result = parse_dormitory_address('Блок A, 3 этаж')
        self.assertEqual(result['block'], 'A')
        self.assertEqual(result['floor'], 3)
        self.assertIsNone(result['room'])


class AggregateOrdersByAddressTest(TestCase):
    """Проверка агрегации заказов по адресу."""

    def _order(self, address, water_qty=1):
        """Создать dict-заказ в формате OrderSerializer."""
        return {
            'id': 1,
            'delivery_address_text': address,
            'items': [{'product_type': '19W', 'quantity': water_qty}],
        }

    def test_groups_by_block_floor(self):
        """Заказы группируются по (блок, этаж) и суммируют воду по этажу."""
        orders = [
            self._order('Блок A, 3 этаж, комната 12', 2),
            self._order('Блок A, 3 этаж, комната 12', 1),
            self._order('Блок A, 3 этаж, комната 15', 1),
            self._order('Блок B, 5 этаж, комната 7', 3),
        ]
        result = aggregate_orders_by_address(orders)

        # 3 заказа на этаже 3 блока A суммируются в одну группу
        self.assertEqual(len(result['groups']), 2)
        self.assertEqual(result['unparsed'], [])

        by_key = {(g['block'], g['floor']): g for g in result['groups']}
        self.assertEqual(by_key[('A', 3)]['water_qty'], 4)   # 2+1+1
        self.assertEqual(by_key[('B', 5)]['water_qty'], 3)

        # Детализация по комнатам
        rooms_a3 = {r['room']: r['water_qty'] for r in by_key[('A', 3)]['rooms']}
        self.assertEqual(rooms_a3, {12: 3, 15: 1})   # 2+1 в комнате 12, 1 в комнате 15
        rooms_b5 = {r['room']: r['water_qty'] for r in by_key[('B', 5)]['rooms']}
        self.assertEqual(rooms_b5, {7: 3})

    def test_unparsed_orders_separated(self):
        """Заказы без распознанного адреса попадают в unparsed."""
        orders = [
            self._order('Блок A, 3 этаж, комната 12', 2),
            self._order('Улица Ленина, дом 5', 1),
            self._order('', 1),
        ]
        result = aggregate_orders_by_address(orders)

        self.assertEqual(len(result['groups']), 1)
        self.assertEqual(len(result['unparsed']), 2)

    def test_groups_sorted(self):
        """Группы отсортированы по блоку, затем этажу."""
        orders = [
            self._order('Блок B, 5 этаж, комната 7'),
            self._order('Блок A, 3 этаж, комната 12'),
            self._order('Блок A, 2 этаж, комната 1'),
        ]
        result = aggregate_orders_by_address(orders)
        blocks = [(g['block'], g['floor']) for g in result['groups']]
        self.assertEqual(blocks, [('A', 2), ('A', 3), ('B', 5)])
