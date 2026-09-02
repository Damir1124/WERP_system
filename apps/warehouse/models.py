from django.db import models
from apps.products.models import Product
from django.core.validators import MinValueValidator
from apps.accounting.models import Contract


# ═══════════════════════════════════════════════════════════════════════════════
#  АВТОНОМНЫЙ КОНТУР СКЛАДСКИХ ПРОДУКТОВ
#  Полностью отдельная сущность WarehouseProduct — НЕ связана с Product.
#  Связь с ассортиментом реализована через ProductWarehouseMapping (M2M).
# ═══════════════════════════════════════════════════════════════════════════════


class WarehouseProduct(models.Model):
    """Складской продукт — полностью автономная сущность, отдельная от ассортимента Product"""
    name = models.CharField(max_length=120, unique=True, verbose_name="Наименование")
    sku = models.CharField(max_length=50, blank=True, verbose_name="Артикул")
    unit = models.CharField(max_length=20, default='шт', verbose_name="Единица измерения")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = 'Складской продукт'
        verbose_name_plural = 'Складские продукты'
        ordering = ['name']

    def __str__(self):
        return self.name


class WarehouseStockBalance(models.Model):
    """Остатки складских продуктов (один баланс на продукт)"""
    warehouse_product = models.OneToOneField(
        WarehouseProduct,
        on_delete=models.CASCADE,
        related_name='balance',
        verbose_name="Складской продукт"
    )
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Остаток"
    )
    last_received_date = models.DateTimeField(null=True, blank=True, verbose_name="Последний приход")
    last_departure_date = models.DateTimeField(null=True, blank=True, verbose_name="Последний расход")

    class Meta:
        verbose_name = 'Остаток складского продукта'
        verbose_name_plural = 'Остатки складских продуктов'

    def __str__(self):
        return f"{self.warehouse_product.name}: {self.quantity} {self.warehouse_product.unit}"


class WarehouseStockMovement(models.Model):
    """Приход/расход складских продуктов (журнал движений)"""
    class OperationType(models.TextChoices):
        INCOME = 'IN', 'Приход'
        EXPENSE = 'OUT', 'Расход'

    warehouse_product = models.ForeignKey(
        WarehouseProduct,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name="Складской продукт"
    )
    operation_type = models.CharField(
        max_length=3,
        choices=OperationType.choices,
        verbose_name="Тип операции"
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Количество")
    note = models.TextField(max_length=255, blank=True, verbose_name="Примечание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    class Meta:
        verbose_name = 'Движение складского продукта'
        verbose_name_plural = 'Движения складских продуктов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_operation_type_display()} {self.warehouse_product.name} - {self.quantity}"


class WarehouseInventoryAdjustment(models.Model):
    """Ручная корректировка остатков складских продуктов"""
    class AdjustmentType(models.TextChoices):
        INCREASE = 'INC', 'Увеличение'
        DECREASE = 'DEC', 'Уменьшение'
        SET = 'SET', 'Установка значения'

    warehouse_product = models.ForeignKey(
        WarehouseProduct,
        on_delete=models.CASCADE,
        related_name='adjustments',
        verbose_name="Складской продукт"
    )
    adjustment_type = models.CharField(
        max_length=3,
        choices=AdjustmentType.choices,
        verbose_name="Тип корректировки"
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество",
        help_text='Количество для увеличения/уменьшения или новое значение при установке'
    )
    reason = models.TextField(
        max_length=500,
        verbose_name="Причина корректировки",
        help_text='Обязательно укажите причину корректировки остатков'
    )
    adjusted_by = models.ForeignKey(
        'workers.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто выполнил корректировку"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата корректировки")
    note = models.TextField(max_length=1000, blank=True, verbose_name="Дополнительные примечания")

    class Meta:
        verbose_name = 'Корректировка складского продукта'
        verbose_name_plural = 'Корректировки складских продуктов'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_adjustment_type_display()} {self.warehouse_product.name} - {self.quantity}'


class ProductWarehouseMapping(models.Model):
    """Связь многие-ко-многим: Product ассортимента ↔ складские продукты.

    Позволяет одному Product списывать несколько складских продуктов
    (и наоборот) при продажах. Коэффициент задаёт, сколько единиц
    складского продукта списывается за 1 проданный продукт.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='warehouse_mappings',
        verbose_name="Продукт ассортимента"
    )
    warehouse_product = models.ForeignKey(
        WarehouseProduct,
        on_delete=models.CASCADE,
        related_name='product_mappings',
        verbose_name="Складской продукт"
    )
    coefficient = models.PositiveIntegerField(
        default=1,
        verbose_name="Коэффициент",
        help_text="Сколько единиц складского продукта списывается за 1 проданный продукт"
    )

    class Meta:
        verbose_name = 'Связь продукта со складом'
        verbose_name_plural = 'Связи продуктов со складом'
        unique_together = ('product', 'warehouse_product')

    def __str__(self):
        return f"{self.product.name} → {self.warehouse_product.name} (×{self.coefficient})"



class Garage(models.Model):
    """Учет транспортных средств"""
    vehicle_name = models.CharField(max_length=255, verbose_name='Название автомобиля')
    plate_number = models.CharField(max_length=15, verbose_name='Номерной знак', null=True)
    milage = models.PositiveIntegerField(verbose_name='Пробег', validators=[MinValueValidator(0)])
    year = models.DateField(verbose_name="Год выпуска")
    courier = models.OneToOneField('workers.Worker', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Курьер')

    class Meta:
        unique_together = ('milage', 'vehicle_name')
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили'

    def save(self, *args, **kwargs):
        # Номерной знак всегда храним в верхнем регистре
        if self.plate_number:
            self.plate_number = self.plate_number.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.courier:
            return str(self.courier.full_name)
        return self.vehicle_name
