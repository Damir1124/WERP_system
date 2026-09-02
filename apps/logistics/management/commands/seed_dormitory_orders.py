"""
Management command: создание тестовых заказов общежития для проверки
скрытой команды курьера «/сводка» (агрегация по адресу).

Запуск:
    python manage.py seed_dormitory_orders [--count N]

Создаёт N (по умолчанию 10) заказов в пуле (без назначенного курьера,
status=PENDING) с адресами общежития в разных форматах. Часть заказов
имеет «неагрегируемые» адреса, чтобы проверить вывод кнопками.

Курьер может взять эти заказы через бота (📦 Заказы → взять), открыть
рейс и вызвать /сводка.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.clients.models import Client
from apps.logistics.models import Order, OrderItem
from apps.logistics.services import create_order_with_display_number
from apps.products.models import Product


# (адрес, количество воды)
SEED_ORDERS = [
    ('Блок A, 3 этаж, комната 12', 2),
    ('Блок A, 3 этаж, комната 12', 1),
    ('Блок A, 3 этаж, комната 15', 1),
    ('Блок A, 5 этаж, комната 20', 2),
    ('Блок B, 5 этаж, комната 7', 3),
    ('Блок B, 2 этаж, комната 4', 1),
    ('Корпус 2, 4 этаж, кв 15', 2),
    ('Блок C 1 эт. комн. 3', 1),
    # Неагрегируемые адреса (попадут в unparsed → кнопками)
    ('Улица Ленина, дом 5', 1),
    ('Общежитие, без номера комнаты', 2),
]


class Command(BaseCommand):
    help = 'Создать тестовые заказы общежития для проверки агрегации /сводка'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=len(SEED_ORDERS),
            help='Сколько заказов создать (по умолчанию все из набора)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options['count']

        water = Product.objects.filter(type_product=Product.TypeProduct.WATER).first()
        if not water:
            self.stderr.write(
                self.style.ERROR('Не найден продукт «Вода» (type_product=19W). '
                                 'Сначала создайте продукт.')
            )
            return

        created = 0
        for i, (address, qty) in enumerate(SEED_ORDERS[:count]):
            # Корректный узбекский номер: +998 + 9 цифр (код оператора 90 + 7 цифр)
            phone = f'+99890{1000000 + i:07d}'
            client, _ = Client.objects.get_or_create(
                phone=phone,
                defaults={'name': f'Тест Общежитие {i + 1}'},
            )

            order = create_order_with_display_number(
                client=client,
                trip=None,
                assigned_courier=None,
                payment_type=Order.PaymentType.CASH,
                status=Order.Status.PENDING,
                delivery_address_text=address,
            )
            OrderItem.objects.create(
                order=order,
                product=water,
                quantity=qty,
            )
            created += 1
            self.stdout.write(
                self.style.SUCCESS(f'  Заказ #{order.display_number:03d} — {address} (вода {qty})')
            )

        self.stdout.write(self.style.SUCCESS(f'\nСоздано заказов: {created}'))
        self.stdout.write(
            'Теперь откройте смену и рейс в боте, возьмите эти заказы '
            'и введите /сводка.'
        )
