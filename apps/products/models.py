from django.db import models

class Product(models.Model):
    """Таблица продуктов(ассортимента)"""
    class TypeProduct(models.TextChoices):
        COOLERS = "CL", 'Кулеры'
        ACCESSORY = 'AR', "Аксессуары"
        WATER = 'WE', "Вода"
        BOTTLE_20L = 'B20L', "Вода c тарой 20L"


    name = models.CharField(max_length=120, null=False, unique=True, verbose_name="Имя продукта")
    type_product = models.CharField(max_length=4,
                                    choices=TypeProduct.choices,
                                    default=TypeProduct.COOLERS,
                                    verbose_name="Тип продукта")
    price = models.IntegerField(null=False, verbose_name="Стоимость")
    created_at = models.DateField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.name
