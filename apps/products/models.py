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
    image_url = models.URLField(
        blank=True,
        default='',
        verbose_name="Фото товара (URL)",
        help_text="Внешний URL изображения (если не загружен файл)"
    )
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name="Фото товара (файл)",
        help_text="Загрузите изображение товара (будет доступно по /media/products/)"
    )
    is_visible_in_catalog = models.BooleanField(
        default=True,
        verbose_name="Показывать в каталоге",
        help_text="Если отмечено, товар показывается в каталоге клиентского приложения"
    )
    track_inventory = models.BooleanField(
        default=True,
        verbose_name="Учитывать на складе",
        help_text="Если отмечено, то для этого товара будет учитываться учет остатков на складе"
    )
    created_at = models.DateField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.name
