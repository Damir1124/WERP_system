from django.db import models


# Устаревшие модели DeliveryLog, DeliveryLogMove, DeliveryJournal удалены.
# Источник правды — архитектура CourierShift → CourierTrip → Order → OrderItem.


class CourierShift(models.Model):
    """Смена курьера"""
    class Status(models.TextChoices):
        OPEN   = 'OP', 'Открыта'
        CLOSED = 'CL', 'Закрыта'

    courier     = models.ForeignKey('workers.Worker', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Курьер')
    date        = models.DateField(auto_now_add=True, verbose_name='Дата смены')
    status      = models.CharField(choices=Status.choices, default=Status.OPEN, max_length=2)
    cash_total  = models.IntegerField(default=0, verbose_name='Наличные за смену')
    card_total  = models.IntegerField(default=0, verbose_name='Безнал за смену')
    opened_at   = models.DateTimeField(auto_now_add=True)
    closed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Смена курьера"
        verbose_name_plural = "Смены курьеров"
        ordering = ['-date']

    def __str__(self):
        courier_name = self.courier.full_name if self.courier else '—'
        return f'Смена {courier_name} от {self.date} ({self.status})'

    def close(self):
        """Закрытие смены"""
        from django.utils import timezone
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])


class CourierTrip(models.Model):
    """Рейс внутри смены"""
    class Status(models.TextChoices):
        ACTIVE = 'AC', 'В пути'
        DONE   = 'DN', 'Завершён'

    shift        = models.ForeignKey(CourierShift, on_delete=models.CASCADE, related_name='trips')
    full_loaded  = models.IntegerField(verbose_name='Загружено полных баклажек')
    full_returned = models.IntegerField(default=0, verbose_name='Возвращено полных (недоставленных)')
    status       = models.CharField(choices=Status.choices, default=Status.ACTIVE, max_length=2)
    started_at   = models.DateTimeField(auto_now_add=True)
    finished_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Рейс курьера"
        verbose_name_plural = "Рейсы курьеров"
        ordering = ['-started_at']

    def __str__(self):
        return f'Рейс #{self.id} смены {self.shift.id} ({self.status})'

    def get_trip_summary(self) -> dict:
        """Справка по рейсу: остатки тары в машине в реальном времени.
        
        Логика расчёта:
        - delivered: сумма quantity всех позиций типа WATER из доставленных заказов
          (quantity при подтверждении перезаписывается на exchange_qty)
        - full_remain: full_loaded - delivered (остаток полных баклажек в машине)
        - empty_received: сумма (exchange_qty - sell_with_qty) по всем доставленным заказам
          * exchange_qty — курьер забрал пустую тару взамен полной
          * sell_with_qty — клиент купил тару, пустой НЕ вернул (вычитаем)
          * Для sell_with_qty создаётся отдельная позиция BOTTLE, но мы всё равно вычитаем
        - defective_qty НЕ считается — брак пока ни на что не влияет
        
        Примеры:
        
        Пример 1:
          Рейс загружен: full_loaded=50
          Заказ 1: exchange=1, sell_with=1 → quantity=1 (перезаписан), empty=0 (1-1)
          Результат: delivered=1, full_remain=49, empty_received=0
        
        Пример 2 (после примера 1):
          Заказ 2: exchange=2, sell_with=0 → quantity=2, empty=2 (2-0)
          Результат: delivered=3, full_remain=47, empty_received=2
        """
        from django.db.models import Sum
        from apps.logistics.models import OrderItem
        from apps.products.models import Product
        
        # Получаем все позиции из доставленных заказов этого рейса
        delivered_items = OrderItem.objects.filter(
            order__trip=self,
            order__status=Order.Status.DELIVERED,
            product__type_product=Product.TypeProduct.WATER  # только тип WATER считается как баклажка
        )
        
        # Доставлено баклажек (сумма quantity всех WATER-позиций доставленных заказов)
        # quantity при подтверждении перезаписывается на exchange_qty (см. bot_bridge/views.py:381)
        delivered = delivered_items.aggregate(total=Sum('quantity'))['total'] or 0
        
        # Осталось полных в машине
        full_remain = self.full_loaded - delivered
        
        # Пустых в машине = сумма (exchange_qty - sell_with_qty) по всем доставленным заказам
        # Формула: empty_received = Σ(exchange_qty - sell_with_qty)
        delivered_order_items = OrderItem.objects.filter(
            order__trip=self,
            order__status=Order.Status.DELIVERED
        )
        
        empty_received = 0
        for item in delivered_order_items:
            empty_received += (item.exchange_qty - item.sell_with_qty)
        
        # defective_qty > 0 означает брак тары (для справки, но не влияет на расчёты)
        defective = delivered_order_items.aggregate(total=Sum('defective_qty'))['total'] or 0
        
        return {
            'full_loaded': self.full_loaded,
            'delivered': delivered,
            'full_returned': self.full_returned,
            'full_remain': full_remain,
            'empty_received': empty_received,
            'defective_received': defective,
        }


class Order(models.Model):
    """Заказ — строка рейса (многопозиционный)"""
    class Status(models.TextChoices):
        PENDING   = 'PD', 'Ожидает'
        DELIVERED = 'DL', 'Доставлен'
        CANCELLED = 'CN', 'Отменён'

    class PaymentType(models.TextChoices):
        CASH  = 'CH', 'Наличные'
        CARD  = 'CD', 'Карта'
        BONUS = 'BS', 'Бонус'

    trip          = models.ForeignKey(CourierTrip, on_delete=models.CASCADE, related_name='orders',
                                      null=True, blank=True, verbose_name='Рейс')
    client        = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True)
    delivery_address = models.ForeignKey(
        'clients.ClientAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Адрес доставки'
    )
    # Снимок адреса на момент создания заказа (история доставки не зависит от ClientAddress).
    # ClientAddress может быть удалён при добавлении 4-го адреса — снимок сохраняет факт доставки.
    delivery_address_text = models.CharField(
        max_length=120, blank=True, default='', verbose_name='Адрес доставки (снимок)'
    )
    delivery_latitude = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True, verbose_name='Широта (снимок)'
    )
    delivery_longitude = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True, verbose_name='Долгота (снимок)'
    )
    assigned_courier = models.ForeignKey(
        'workers.Worker',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_orders',
        verbose_name='Назначенный курьер'
    )
    created_by_worker = models.ForeignKey(
        'workers.Worker',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_orders',
        verbose_name='Создал заказ'
    )
    payment_type  = models.CharField(choices=PaymentType.choices, default=PaymentType.CASH, max_length=2)
    status        = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=2)
    note          = models.CharField(max_length=255, null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    delivered_at  = models.DateTimeField(null=True, blank=True)

    # Декоративный номер (1-999) для отображения сотрудникам, например «Заказ N042».
    # НЕ является уникальным бизнес-идентификатором и НЕ используется для API/URL.
    # Настоящий идентификатор — Order.id. См. apps/logistics/services.py.
    display_number = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name='Декоративный номер'
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    @property
    def human_number(self) -> str:
        """Форматированный декоративный номер: 042 (для старых заказов — id)."""
        if self.display_number is not None:
            return f"{self.display_number:03d}"
        return str(self.id)

    def __str__(self):
        if self.pk is None:
            return f'Заказ (новый, display_number={self.display_number})'
        items_count = self.items.count()
        if self.display_number:
            return f'Заказ #{self.display_number:03d} (ID:{self.id}, {items_count} поз.)'
        return f'Заказ #{self.id} ({items_count} позиций)'

    def get_total_price(self):
        """Динамический подсчет стоимости заказа на основе связанных позиций"""
        from django.db.models import Sum
        total = self.items.aggregate(total=Sum('price'))['total']
        return total if total is not None else 0

    def display_address(self) -> str:
        """Человекочитаемый адрес доставки.

        Формат:
        1. Только координаты (без текста) — 'Location';
        2. И текст, и координаты — 'Location | <текст>';
        3. Только текст — '<текст>';
        4. Ничего — 'Адрес не указан'.

        Если текстовый адрес — заглушка 'Location' (например, при создании
        только по координатам), она не дублируется с маркером локации.
        """
        text = (self.delivery_address_text or '').strip()
        has_coords = self.delivery_latitude is not None and self.delivery_longitude is not None

        # Заглушка 'Location' / '📍 Location' в тексте не считается реальным адресом
        if text.lower() in ('location', '📍 location'):
            text = ''

        if text and has_coords:
            return f'Location | {text}'
        if has_coords:
            return 'Location'
        if text:
            return text
        return 'Адрес не указан'

class OrderItem(models.Model):
    """Позиция заказа (многопозиционная структура)"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name='Продукт')
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    price = models.IntegerField(null=True, blank=True, verbose_name='Цена за позицию') # Авто-расчет: product.price * quantity
    
    # Специфические поля для учета тары (актуально только для продуктов с type == 'B20L')
    exchange_qty = models.IntegerField(default=0, verbose_name='Обмен тары (возврат)')
    sell_with_qty = models.IntegerField(default=0, verbose_name='Продажа с тарой')
    defective_qty = models.IntegerField(default=0, verbose_name='Брак тары')
    
    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"
        ordering = ['id']
    
    def __str__(self):
        return f'Позиция #{self.id} ({self.product}, {self.quantity} шт.)'
    
    def save(self, *args, **kwargs):
        """Автоматический расчет цены позиции при сохранении"""
        import logging
        logger = logging.getLogger(__name__)
        from apps.products.models import Product as _Product
        
        # Установка exchange_qty по умолчанию для новых записей
        # При создании OrderItem для продуктов типа WATER/BOTTLE_20L устанавливаем exchange_qty = quantity
        # Это стартовое значение, которое курьер увидит при подтверждении и сможет изменить
        if self.pk is None and self.exchange_qty == 0:
            if self.product.type_product in (_Product.TypeProduct.WATER, _Product.TypeProduct.BOTTLE_20L):
                self.exchange_qty = self.quantity
                logger.info(f"OrderItem save: set exchange_qty to {self.exchange_qty} for new item")

        # ВАЖНО: Мы больше не пересчитываем quantity как сумму контейнерных полей!
        # quantity - это заказанное количество воды.
        # exchange_qty, sell_with_qty, defective_qty - это детализация того, что произошло с тарой
        # для этого количества воды.
        # Сумма (exchange_qty + sell_with_qty + defective_qty) должна быть равна quantity,
        # но мы не должны менять quantity, если клиент просто распределил тару.
        # Если мы пересчитываем quantity, то при подтверждении заказа (когда мы обновляем
        # exchange_qty и sell_with_qty) quantity будет удваиваться или обнуляться.
        
        if self.product.type_product in (_Product.TypeProduct.WATER, _Product.TypeProduct.BOTTLE_20L):
            logger.info(f"OrderItem save: product type {self.product.type_product}, quantity={self.quantity}, exchange_qty={self.exchange_qty}, sell_with_qty={self.sell_with_qty}, defective_qty={self.defective_qty}")
        
        # Пересчитываем цену только если она не задана (при создании)
        # При обновлении (например, при подтверждении заказа) мы сбрасываем price в None,
        # чтобы он пересчитался.
        if self.price is None:
            # ВАЖНО: Цена тары теперь учитывается через отдельный OrderItem (создаётся в views.py при sell_with_qty > 0)
            # Поэтому здесь мы просто считаем: product.price * quantity
            # Никаких дополнительных расчётов с тарой не нужно
            self.price = self.product.price * self.quantity
            logger.info(f"OrderItem save: product={self.product.name}, quantity={self.quantity}, price={self.price}")

        super().save(*args, **kwargs)


class OrderNumberCounter(models.Model):
    """Счётчик декоративных номеров заказов (1-999).

    Хранит единственную рабочую запись с последним выданным номером.
    При new_order_number() блокируется строка через select_for_update()
    в рамках транзакции, что гарантирует уникальность номера при
    одновременном создании заказов.

    После N999 следующий номер снова равен 1.
    Номера не возвращаются в пул после отмены заказа.
    """
    current_number = models.PositiveSmallIntegerField(
        default=0, verbose_name='Текущий номер'
    )

    class Meta:
        verbose_name = 'Счетчик номеров заказов'
        verbose_name_plural = 'Счетчик номеров заказов'

    def __str__(self):
        return f'Счетчик: {self.current_number}'
