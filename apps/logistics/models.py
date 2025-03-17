from django.db import models
from apps.workers.models import Worker
from apps.products.models import Product

from django.utils import timezone

class DeliveryLog(models.Model):
    class ActionType(models.TextChoices):
        TAKEN = 'TK', 'Взято'
        BROUGHT = 'BG', 'Принесено'
        RETURNED = 'RT', 'Возврат'

    courier_name = models.ForeignKey(Worker, on_delete=models.SET, related_name='couriers', verbose_name='Курьер')
    action = models.CharField(choices=ActionType.choices, max_length=2, verbose_name="Тип действия")
    quantity = models.IntegerField(verbose_name='Количевство')
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Журнал учета тар"

    def __str__(self):
        return f'{self.action} - {self.quantity}шт'


class DeliveryJournal(models.Model):
    class PaymentsType(models.TextChoices):
        CARD = 'CD', 'Карта'
        CASH = 'CH', 'Наличные'
        BONUS = 'BS', 'Бонус'

    courier = models.ForeignKey(Worker, on_delete=models.DO_NOTHING, verbose_name='Курьер')
    date = models.DateField(auto_now_add=True, verbose_name='Дата')
    total_price = models.IntegerField(default=0, verbose_name='Сумма')
    payment_type = models.CharField(choices=PaymentsType.choices, default=PaymentsType.CASH, verbose_name='Тип оплаты')

    class Meta:
        verbose_name = "Журнал доставок"
        verbose_name_plural = "Журналы доставок"
        ordering = ['-date']  # Сортировка по дате

    def __str__(self):
        return f'Отчет курьера {self.courier} за {self.date}: {self.total_price} {self.payment_type}'

    def calculate_total_price(self):
        """Вычисляет общую сумму на основе связанных продуктов."""
        self.total_price = sum(product.product.price * product.quantity for product in self.products.all())
        self.save()

    @classmethod
    def reset_daily_journal(cls):
        """Обнуляет данные в журнале при смене дня."""
        today = timezone.now().date()
        cls.objects.filter(date=today).delete()


class DeliveryJournalProducts(models.Model):
    note = models.CharField(verbose_name='Описание', null=True)
    delivery_journal = models.ForeignKey(DeliveryJournal, on_delete=models.CASCADE, related_name='products',
                                         verbose_name='Журнал доставки')
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Продукт')
    quantity = models.IntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name = "Продукт в журнале доставок"
        verbose_name_plural = "Продукты в журналах доставок"

    def __str__(self):
        return f'{self.product} ({self.quantity} шт.)'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Сначала сохраняем продукт
        self.delivery_journal.calculate_total_price()  # Затем обновляем общую сумму в журнале
