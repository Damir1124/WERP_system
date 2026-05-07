from django.db import models
from django.db.models import Sum
from apps.workers.models import Worker
from apps.products.models import Product
from apps.clients.models import Client


class DeliveryLog(models.Model):
    """Учет доставки по рейсам курьеров"""
    courier = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='couriers', verbose_name='Курьер')
    total_quantity = models.IntegerField(verbose_name='Количевство',
                                         help_text='Кол-во проданой воды с тарой или несоо'
                                                   'тветсвие, пропажа', null=True,
                                         blank=True)
    total_sold = models.IntegerField(verbose_name='Всего проданно:', null=True, blank=True)
    date = models.DateField(verbose_name='Дата')

    class Meta:
        verbose_name = "Журнал учета тар"

    def __str__(self):
        return f'{self.courier} - {self.date}'

    def calculate_total_quantity(self):
        """Вычисляет общее количество на основе связанных движений."""
        total_quantity = 0
        for move in self.deliverylogmove_set.all():
            if move.action == DeliveryLogMove.ActionType.TAKEN:
                total_quantity += move.quantity
            else:
                total_quantity -= move.quantity
        self.total_quantity = total_quantity
        self.save()

    def calculate_total_sold(self):
        """Вычисляет общее число проданной воды учитывая последовательные записи с типом BG"""
        total_sold = 0
        moves = list(self.deliverylogmove_set.all().order_by('date',
                                                             'id'))  # Получаем все движения, отсортированные по дате и ID

        for i, move in enumerate(moves):
            if move.action == DeliveryLogMove.ActionType.TAKEN:
                total_sold += move.quantity
            elif move.action == DeliveryLogMove.ActionType.BROUGHT:
                # Проверяем если предыдущая запись тоже была BROUGHT минусуем ее на колво проданного
                if i > 0 and moves[i - 1].action == DeliveryLogMove.ActionType.BROUGHT:
                    total_sold -= move.quantity

        self.total_sold = total_sold

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Сначала сохраняем запись
        self.check_total_quantity()
        self.calculate_total_sold()

    def check_total_quantity(self):
        """Проверяет соответствие total_quantity.

        Ранее логика опиралась на устаревшую модель DeliveryJournalProducts.
        Сейчас источник истины — модель Order (статус DELIVERED).
        Сравниваем total_quantity журнала с суммой доставленных BOTTLE_20L
        за ту же дату и курьера.
        """
        total_sales_bottle_20l = Order.objects.filter(
            status=Order.Status.DELIVERED,
            product__type_product=Product.TypeProduct.BOTTLE_20L,
            trip__shift__courier=self.courier,
            delivered_at__date=self.date,
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        if self.total_quantity != total_sales_bottle_20l:
            print(
                f"Несоответствие для курьера {self.courier}: total_quantity = {self.total_quantity}, "
                f"продажи BOTTLE_20L (Order) = {total_sales_bottle_20l}"
            )
        else:
            print(
                f"Совпадение для курьера {self.courier}: total_quantity = {self.total_quantity}, "
                f"продажи BOTTLE_20L (Order) = {total_sales_bottle_20l}"
            )


class DeliveryLogMove(models.Model):
    """Инфа о рейсах"""

    class ActionType(models.TextChoices):
        TAKEN = 'TK', 'Взято'
        BROUGHT = 'BG', 'Принесено'
        RETURNED = 'RT', 'Возврат'

    delivery_log = models.ForeignKey(DeliveryLog, on_delete=models.CASCADE, verbose_name='Журнал')
    action = models.CharField(choices=ActionType.choices, verbose_name='Тип действия', max_length=2)
    quantity = models.IntegerField(verbose_name='Количество')
    date = models.DateField(verbose_name='Дата дейсвия')

    def __str__(self):
        sign = '-' if self.action == self.ActionType.TAKEN else '+'
        return f'{self.delivery_log.courier.full_name} - {sign}{self.quantity} - {self.action}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Сначала сохраняем движение
        self.delivery_log.calculate_total_quantity()  # Затем обновляем общее количество в журнале


class DeliveryJournal(models.Model):
    """Deprecated: DeliveryJournal model removed.

    Ранее использовался для ручных отчетов курьеров. Источник правды в
    новой архитектуре — модели CourierShift/CourierTrip/Order.
    Этот класс удалён из кода. Если требуется историческая совместимость,
    используйте резервные таблицы или миграции для доступа к старым данным.
    """


class CourierShift(models.Model):
    """Смена курьера"""
    class Status(models.TextChoices):
        OPEN   = 'OP', 'Открыта'
        CLOSED = 'CL', 'Закрыта'

    courier     = models.ForeignKey('workers.Worker', on_delete=models.CASCADE, verbose_name='Курьер')
    date        = models.DateField(auto_now_add=True, verbose_name='Дата смены')
    status      = models.CharField(choices=Status.choices, default=Status.OPEN, max_length=2)
    cash_total  = models.IntegerField(default=0, verbose_name='Наличные за смену')
    card_total  = models.IntegerField(default=0, verbose_name='Безнал за смену')
    opened_at   = models.DateTimeField(auto_now_add=True)
    closed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Смена курьера"
        verbose_name_plural = "Смены курьеров"
        ordering = ['-date']

    def __str__(self):
        return f'Смена {self.courier} от {self.date} ({self.status})'

    def close(self):
        """Закрытие смены"""
        from django.utils import timezone
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])


class CourierTrip(models.Model):
    """Рейс внутри смены"""
    class Status(models.TextChoices):
        ACTIVE = 'AC', 'В пути'
        DONE   = 'DN', 'Завершён'

    shift        = models.ForeignKey(CourierShift, on_delete=models.CASCADE, related_name='trips')
    full_loaded  = models.IntegerField(verbose_name='Загружено полных баклажек')
    full_returned = models.IntegerField(default=0, verbose_name='Возвращено полных (недоставленных)')
    status       = models.CharField(choices=Status.choices, default=Status.ACTIVE, max_length=2)
    started_at   = models.DateTimeField(auto_now_add=True)
    finished_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Рейс курьера"
        verbose_name_plural = "Рейсы курьеров"
        ordering = ['-started_at']

    def __str__(self):
        return f'Рейс #{self.id} смены {self.shift.id} ({self.status})'

    def get_trip_summary(self) -> dict:
        """Справка по рейсу: остатки тары в машине в реальном времени"""
        from django.db.models import Sum
        delivered = self.orders.filter(
            status=Order.Status.DELIVERED
        ).aggregate(total=Sum('quantity'))['total'] or 0

        empty_received = self.orders.filter(
            status=Order.Status.DELIVERED,
            container_op=Order.ContainerOp.EXCHANGE
        ).aggregate(total=Sum('quantity'))['total'] or 0

        defective = self.orders.filter(
            status=Order.Status.DELIVERED,
            container_op=Order.ContainerOp.DEFECTIVE
        ).aggregate(total=Sum('quantity'))['total'] or 0

        full_remain = self.full_loaded - delivered - self.full_returned
        return {
            'full_loaded': self.full_loaded,
            'delivered': delivered,
            'full_returned': self.full_returned,
            'full_remain': full_remain,
            'empty_received': empty_received,
            'defective_received': defective,
        }


class Order(models.Model):
    """Заказ — строка рейса"""
    class Status(models.TextChoices):
        PENDING   = 'PD', 'Ожидает'
        DELIVERED = 'DL', 'Доставлен'
        CANCELLED = 'CN', 'Отменён'

    class ContainerOp(models.TextChoices):
        EXCHANGE  = 'EX', 'Обмен (пустая → полная)'
        SELL_WITH = 'SW', 'Продажа с тарой'
        DEFECTIVE = 'DF', 'Возврат брака'

    class PaymentType(models.TextChoices):
        CASH  = 'CH', 'Наличные'
        CARD  = 'CD', 'Карта'
        BONUS = 'BS', 'Бонус'

    trip          = models.ForeignKey(CourierTrip, on_delete=models.CASCADE, related_name='orders')
    client        = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True)
    product       = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity      = models.IntegerField(default=1, verbose_name='Количество')
    price         = models.IntegerField(blank=True, null=True, verbose_name='Сумма')
    payment_type  = models.CharField(choices=PaymentType.choices, default=PaymentType.CASH, max_length=2)
    status        = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=2)
    container_op  = models.CharField(choices=ContainerOp.choices, null=True, blank=True, max_length=2,
                                     verbose_name='Операция с тарой',
                                     help_text='Заполняется курьером при подтверждении доставки')
    note          = models.CharField(max_length=255, null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    delivered_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.id} ({self.product}, {self.quantity} шт.)'

    def save(self, *args, **kwargs):
        """Автоматический расчет цены при сохранении"""
        if self.price is None:
            self.price = self.product.price * self.quantity
        super().save(*args, **kwargs)
