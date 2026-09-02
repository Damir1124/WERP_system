"""
Тест декоративных номеров заказов (Order.display_number).

Запуск: python manage.py test tests.logistics.test_display_number
"""

from django.test import TestCase
from apps.logistics.models import Order, OrderNumberCounter
from apps.logistics.services import get_next_display_number, create_order_with_display_number


class DisplayNumberTest(TestCase):
    """Проверка логики декоративных номеров."""

    def test_first_number_is_1(self):
        """Первый новый заказ получает N001."""
        n = get_next_display_number()
        self.assertEqual(n, 1)

    def test_sequential_numbers(self):
        """Следующие получают N002, N003 и далее."""
        n1 = get_next_display_number()
        n2 = get_next_display_number()
        n3 = get_next_display_number()
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 2)
        self.assertEqual(n3, 3)

    def test_wrap_after_999(self):
        """После N999 следующий получает N001."""
        # Сначала создаём счётчик (если нет)
        get_next_display_number()
        c = OrderNumberCounter.objects.first()
        c.current_number = 999
        c.save()

        n = get_next_display_number()
        self.assertEqual(n, 1)

        n2 = get_next_display_number()
        self.assertEqual(n2, 2)

    def test_create_order_has_display_number(self):
        """create_order_with_display_number создаёт заказ с display_number."""
        from apps.products.models import Product
        from apps.clients.models import Client

        client = Client.objects.create(
            name="Тест",
            phone="998901234567",
        )

        order = create_order_with_display_number(
            client=client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING,
        )

        self.assertIsNotNone(order.display_number)
        self.assertGreaterEqual(order.display_number, 1)
        self.assertLessEqual(order.display_number, 999)

    def test_human_number_format(self):
        """human_number возвращает формат 042 (без буквы N)."""
        order = Order(display_number=7)
        self.assertEqual(order.human_number, '007')

        order = Order(display_number=42)
        self.assertEqual(order.human_number, '042')

        order = Order(display_number=999)
        self.assertEqual(order.human_number, '999')

        order = Order(display_number=None)
        # Для старых заказов без номера — fallback на id как строку
        self.assertEqual(order.human_number, str(order.id))

    def test_old_orders_without_number(self):
        """Старые заказы без номера не ломаются."""
        from apps.clients.models import Client
        client = Client.objects.create(name="Тест", phone="998901234567")
        order = Order.objects.create(
            client=client,
            payment_type=Order.PaymentType.CASH,
            status=Order.Status.PENDING,
            # Не передаём display_number — старый заказ без номера
        )
        # Не должно быть ошибок
        self.assertIsNone(order.display_number)
        self.assertIsNotNone(str(order))
        self.assertIn(f'#{order.id}', str(order))

    def test_not_unique_constraint(self):
        """Повторение номера допустимо (не уникальное поле)."""
        order1 = Order(display_number=1)
        order2 = Order(display_number=1)
        # Просто проверяем, что поля создаются
        self.assertEqual(order1.display_number, order2.display_number)