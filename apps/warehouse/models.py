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


