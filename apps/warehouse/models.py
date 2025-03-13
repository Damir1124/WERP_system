from django.db import models
from apps.products.models import Product
from django.core.validators import MinValueValidator


class StockBalance(models.Model):
    product = models.ForeignKey(Product,
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True,
                                related_name='products',
                                verbose_name="Продукт")
    quantitly = models.IntegerField(null=False,
                                    default=1,
                                    verbose_name="Количство на складе",
                                    validators=[MinValueValidator(1)])
    last_received_date = models.DateField(verbose_name='Дата последнего прибавления', null=True)
    last_departure_date = models.DateField(verbose_name='Дата последнего убавления', null=True)

    class Meta:
        verbose_name = 'Склад'


    def __str__(self):
        return f"{self.product.name} на складе {self.quantitly} шт"


class StockMovement(models.Model):
    class OperationTypeChoices(models.TextChoices):
        BY = 'By', 'В плюс'
        SELL = 'Sell', 'В минус'

    sold_product = models.ForeignKey(Product,
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True,
                                related_name='sold_product',
                                verbose_name='Продукт'
    )
    # contract = models.ForeignKey(Contract,
    #                              on_delete=models.SET_NULL,
    #                              null=True,
    #                              blank=True,
    #                              related_name="contrats",
    #                              verbose_name='Контракт'
    # )
    operation_type = models.CharField(max_length=10, choices=OperationTypeChoices.choices)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Количество')
    data = models.DateField(auto_now_add=True)
    note = models.TextField(max_length=255, verbose_name='Примечание', null=True)

    class Meta:
        verbose_name = "Лог Движений на складе"

    def __str__(self):
        return f"{self.sold_product} - {self.operation_type}" if self.sold_product else "Без продукта"


class Garage(models.Model):
    vehicle_name = models.CharField(max_length=255, verbose_name='Название автомобиля')
    milage = models.PositiveIntegerField(verbose_name='Пробег', validators=[MinValueValidator(0)])
    year = models.PositiveIntegerField(
        verbose_name='Год',
        validators=[MinValueValidator(2015)]
    )
    courier = models.OneToOneField('workers.Worker', on_delete=models.CASCADE, verbose_name='Курьер')

    class Meta:
        unique_together = ('milage', 'vehicle_name')
        verbose_name = 'Гараж'

    def __str__(self):
        return str(self.courier.full_name)
