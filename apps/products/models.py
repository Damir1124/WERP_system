from django.db import models

class Product(models.Model):
    """Таблица продуктов(ассортимента)"""
    class TypeProduct(models.TextChoices):
        COOLERS = "CL", 'Кулеры'
        ACCESSORY = 'AR', "Аксессуары"
        WATER = '19W', "Вода"
        BOTTLE_20L = 'B19W', "Вода + тара 19"
        BOTTLE = 'BT', 'Тара'


    name = models.CharField(max_length=120, null=False, unique=True, verbose_name="Имя продукта")
    type_product = models.CharField(max_length=4,
                                    choices=TypeProduct.choices,
                                    default=TypeProduct.COOLERS,
                                    verbose_name="Тип продукта")
    price = models.IntegerField(null=False, verbose_name="Стоимость")
    track_inventory = models.BooleanField(
        default=True,
        verbose_name="Учитывать на складе",
        help_text="Если отмечено, то для этого продукта будет вестись учет остатков на складе"
    )
    created_at = models.DateField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.name
