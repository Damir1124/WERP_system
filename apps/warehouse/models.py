from django.db import models
from apps.products.models import Product
from django.core.validators import MinValueValidator
from apps.accounting.models import Contract



class StockBalance(models.Model):
    """Баланс позиций на складе"""
    product = models.ForeignKey(Product,
                                on_delete=models.CASCADE,
                                null=True,
                                blank=True,
                                related_name='products',
                                verbose_name="Продукт")
    quantity = models.IntegerField(null=False,
                                   default=1,
                                   verbose_name="Количство на складе",
                                   validators=[MinValueValidator(1)])
    last_received_date = models.DateTimeField(verbose_name='Дата последнего прибавления', null=True, blank=True)
    last_departure_date = models.DateTimeField(verbose_name='Дата последнего убавления', null=True, blank=True)

    class Meta:
        verbose_name = 'Склад'


    def __str__(self):
        return f"{self.product.name} на складе {self.quantity} шт"


class StockMovement(models.Model):
    """Движение позиций со склада на склад"""
    class OperationTypeChoices(models.TextChoices):
        BUY = 'Buy', 'В плюс'
        SELL = 'Sell', 'В минус'

    sold_product = models.ForeignKey(Product,
                                on_delete=models.CASCADE,
                                null=True,
                                blank=True,
                                related_name='sold_product',
                                verbose_name='Продукт'
    )
    contract = models.ForeignKey(Contract,
                                 on_delete=models.CASCADE,
                                 null=True,
                                 blank=True,
                                 related_name="contrats",
                                 verbose_name='Контракт'
    )
    operation_type = models.CharField(max_length=10, choices=OperationTypeChoices.choices)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Количество')
    data = models.DateField(auto_now_add=True)
    note = models.TextField(max_length=255, verbose_name='Примечание', null=True)

    class Meta:
        verbose_name = "Лог Движений на складе"

    def __str__(self):
        return f"{self.sold_product} - {self.operation_type}" if self.sold_product else "Без продукта"


class Garage(models.Model):
    """Учет транспортных средств"""
    vehicle_name = models.CharField(max_length=255, verbose_name='Название автомобиля')
    plate_number = models.CharField(max_length=6, verbose_name='Номерной знак', null=True)
    milage = models.PositiveIntegerField(verbose_name='Пробег', validators=[MinValueValidator(0)])
    year = models.DateField(verbose_name="Год выпуска")
    courier = models.OneToOneField('workers.Worker', on_delete=models.CASCADE, verbose_name='Курьер')

    class Meta:
        unique_together = ('milage', 'vehicle_name')
        verbose_name = 'Гараж'

    def __str__(self):
        return str(self.courier.full_name)


class InventoryAdjustment(models.Model):
    """
    Ручная корректировка остатков на складе через админку.
    Используется для исправления расхождений, инвентаризации и т.д.
    """
    class AdjustmentType(models.TextChoices):
        INCREASE = 'INC', 'Увеличение'
        DECREASE = 'DEC', 'Уменьшение'
        SET = 'SET', 'Установка значения'
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    adjustment_type = models.CharField(
        max_length=3,
        choices=AdjustmentType.choices,
        verbose_name='Тип корректировки'
    )
    quantity = models.IntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)],
        help_text='Количество для увеличения/уменьшения или новое значение при установке'
    )
    reason = models.TextField(
        verbose_name='Причина корректировки',
        max_length=500,
        help_text='Обязательно укажите причину корректировки остатков'
    )
    adjusted_by = models.ForeignKey(
        'workers.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Кто выполнил корректировку'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата корректировки')
    note = models.TextField(
        verbose_name='Дополнительные примечания',
        max_length=1000,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Корректировка инвентаря'
        verbose_name_plural = 'Корректировки инвентаря'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.get_adjustment_type_display()} {self.product.name} - {self.quantity} шт.'
    
    def save(self, *args, **kwargs):
        """При сохранении корректировки автоматически обновляем StockBalance"""
        from django.utils import timezone
        
        # Проверяем, нужно ли учитывать этот продукт на складе
        if not self.product.track_inventory:
            # Если продукт не отслеживается на складе, просто сохраняем запись корректировки
            # но не меняем StockBalance
            super().save(*args, **kwargs)
            return
        
        # Вызываем родительский save сначала, чтобы получить id
        super().save(*args, **kwargs)
        
        # Получаем или создаем StockBalance для продукта
        stock_balance, created = StockBalance.objects.get_or_create(
            product=self.product,
            defaults={'quantity': 0}
        )
        
        # Применяем корректировку в зависимости от типа
        if self.adjustment_type == self.AdjustmentType.INCREASE:
            stock_balance.quantity += self.quantity
            stock_balance.last_received_date = timezone.now()
        elif self.adjustment_type == self.AdjustmentType.DECREASE:
            stock_balance.quantity = max(0, stock_balance.quantity - self.quantity)
            stock_balance.last_departure_date = timezone.now()
        elif self.adjustment_type == self.AdjustmentType.SET:
            stock_balance.quantity = max(0, self.quantity)
            # Если новое значение больше старого - считаем приходом, иначе - уходом
            if self.quantity > stock_balance.quantity:
                stock_balance.last_received_date = timezone.now()
            else:
                stock_balance.last_departure_date = timezone.now()
        
        stock_balance.save()
        
        # Создаем запись в StockMovement для аудита
        StockMovement.objects.create(
            sold_product=self.product,
            operation_type=StockMovement.OperationTypeChoices.BUY if self.adjustment_type in [self.AdjustmentType.INCREASE, self.AdjustmentType.SET] else StockMovement.OperationTypeChoices.SELL,
            quantity=abs(self.quantity),
            note=f'Корректировка инвентаря: {self.reason}. {self.note or ""}'
        )
