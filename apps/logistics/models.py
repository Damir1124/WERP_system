from django.db import models
from django.db.models import Sum
from apps.workers.models import Worker
from apps.products.models import Product
from django.utils import timezone


class DeliveryLog(models.Model):
    """Учет доставки по рейсам курьеров"""
    courier = models.ForeignKey(Worker, on_delete=models.SET, related_name='couriers', verbose_name='Курьер')
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
        """Вычисляет общее число проданной воды"""
        total_sold = 0
        for move in self.deliverylogmove_set.all():
            if move.action == DeliveryLogMove.ActionType.TAKEN: # Может еще условия добавлю потомучто из-за смены даты
                                                                # не корректно отображается
                total_sold += move.quantity
        self.total_sold = total_sold

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Сначала сохраняем запись
        self.check_total_quantity()
        self.calculate_total_sold()

    def check_total_quantity(self):
        """Проверяет соответствие total_quantity после сохранения DeliveryLog
        и работает в связке с функцией models_save в админке"""
        total_sales_bottle_20l = DeliveryJournalProducts.objects.filter(
            delivery_journal__date=self.date,
            delivery_journal__courier=self.courier,
            product__type_product=Product.TypeProduct.BOTTLE_20L
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        if self.total_quantity != total_sales_bottle_20l:
            print(f"Несоответствие для курьера {self.courier}: total_quantity = {self.total_quantity}, "
                  f"продажи BOTTLE_20L = {total_sales_bottle_20l}")
        else:
            print(f"Совпадение для курьера {self.courier}: total_quantity = {self.total_quantity}, "
                  f"продажи BOTTLE_20L = {total_sales_bottle_20l}")


class DeliveryLogMove(models.Model):
    """Инфа о рейсах"""

    class ActionType(models.TextChoices):
        TAKEN = 'TK', 'Взято'
        BROUGHT = 'BG', 'Принесено'
        RETURNED = 'RT', 'Возврат'

    delivery_log = models.ForeignKey(DeliveryLog, on_delete=models.CASCADE, verbose_name='Журнал')
    action = models.CharField(choices=ActionType.choices, verbose_name='Тип действия')
    quantitly = models.IntegerField(verbose_name='Количество')
    date = models.DateField(verbose_name='Дата дейсвия')

    def __str__(self):
        sign = '-' if self.action == self.ActionType.TAKEN else '+'
        return f'{self.delivery_log.courier.full_name} - {sign}{self.quantitly} - {self.action}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Сначала сохраняем движение
        self.delivery_log.calculate_total_quantity()  # Затем обновляем общее количество в журнале


class DeliveryJournal(models.Model):
    """Отчеты курьеров"""

    courier = models.ForeignKey(Worker, on_delete=models.DO_NOTHING, verbose_name='Курьер')
    date = models.DateField(verbose_name='Дата')
    card_price = models.IntegerField(default=0, verbose_name='Сумма картой')
    total_price = models.IntegerField(default=0, verbose_name='Общая сумма')

    class Meta:
        verbose_name = "Журнал доставок"
        verbose_name_plural = "Журналы доставок"
        ordering = ['-date']  # Сортировка по дате

    def __str__(self):
        return f'Отчет курьера {self.courier} за {self.date}: {self.total_price}'

    def update_total_price(self):
        """Пересчитывает общую сумму отчета"""
        total_price = 0
        card_price = 0
        for product in self.products.all():
            if product.payment_type == DeliveryJournalProducts.PaymentsType.BONUS:
                total_price -= abs(product.price) or 0  # Вычитаем при бонусной оплате
            elif product.payment_type == DeliveryJournalProducts.PaymentsType.CARD:
                card_price += product.price or 0 # Прибаляем при оплате картой
            else:
                total_price += product.price or 0  # Прибавляем в любом случае случаях
        self.total_price = total_price
        self.card_price = card_price
        self.save()

    @classmethod
    def reset_daily_journal(cls):
        """Обнуляет данные в журнале при смене дня."""
        today = timezone.now().date()
        cls.objects.filter(date=today).delete()


class DeliveryJournalProducts(models.Model):
    """Инфа о продуктах в отчете"""

    class PaymentsType(models.TextChoices):
        CARD = 'CD', 'Карта'
        CASH = 'CH', 'Наличные'
        BONUS = 'BS', 'Бонус'

    note = models.CharField(verbose_name='Описание', null=True, blank=True)
    delivery_journal = models.ForeignKey(DeliveryJournal, on_delete=models.CASCADE, related_name='products',
                                         verbose_name='Журнал доставки')
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Продукт', default=2)
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    price = models.IntegerField(blank=True, null=True, verbose_name='Цена')
    payment_type = models.CharField(choices=PaymentsType.choices, default=PaymentsType.CASH, verbose_name='Тип оплаты')

    class Meta:
        verbose_name = "Продукт в журнале доставок"
        verbose_name_plural = "Продукты в журналах доставок"

    def __str__(self):
        return f'{self.product} ({self.quantity} шт.)'

    def save(self, *args, **kwargs):
        """Пересчет цены и обновление total_price в журнале"""
        if self.price is None:  # Если цена не указана, считаем по формуле
            self.price = self.product.price * self.quantity

        super().save(*args, **kwargs)  # Сохраняем запись
        self.delivery_journal.update_total_price()  # Пересчитываем общую сумму
