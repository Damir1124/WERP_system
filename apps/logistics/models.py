from django.db import models
from django.utils import timezone

from apps.workers.models import Worker
from apps.products.models import Product


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


class DeliveryReport(models.Model):
    note = models.TextField(verbose_name="Описание")

    cooler = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="coolers",
        limit_choices_to={'type_product': Product.TypeProduct.COOLERS}
    )
    cooler_quantity = models.PositiveIntegerField(default=0, verbose_name="Количество кулеров")

    accessory = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accessories",
        limit_choices_to={'type_product': Product.TypeProduct.ACCESSORY}
    )
    accessory_quantity = models.PositiveIntegerField(default=0, verbose_name="Количество аксессуаров")

    bottle = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bottles",
        limit_choices_to={'type_product': Product.TypeProduct.BOTTLE_20L}
    )
    bottle_quantity = models.PositiveIntegerField(default=0, verbose_name="Количество бутылей")

    water = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="waters",
        limit_choices_to={'type_product': Product.TypeProduct.WATER}
    )
    water_quantity = models.PositiveIntegerField(default=0, verbose_name="Количество воды")

    summary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма стоимости", default=0.00)
    payment = models.CharField(
        max_length=20,
        choices=[('card', 'Карта'), ('cash', 'Наличные'), ('bonus', 'Бонус')],
        verbose_name="Тип оплаты"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def calculate_summary(self):
        """Вычисляет сумму стоимости всех товаров с учетом количества"""
        total = 0
        for product, quantity in [
            (self.cooler, self.cooler_quantity),
            (self.accessory, self.accessory_quantity),
            (self.bottle, self.bottle_quantity),
            (self.water, self.water_quantity),
        ]:
            if product:
                total += product.price * quantity
        return total

    def save(self, *args, **kwargs):
        self.summary = self.calculate_summary()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Отчет {self.id} - {self.summary} сум"

