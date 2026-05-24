from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import DeliveryLog, DeliveryLogMove, Order, CourierShift, OrderItem


@receiver(post_save, sender=DeliveryLogMove)
def update_delivery_log_totals(sender, instance, **kwargs):
    """Обновление total_quantity и total_sold в DeliveryLog после изменения DeliveryLogMove"""
    delivery_log = instance.delivery_log
    delivery_log.calculate_total_quantity()
    delivery_log.calculate_total_sold()
    # Сохраняем агрегаты журнала (это другой sender, безопасно)
    delivery_log.save()


@receiver(post_save, sender=DeliveryLog)
def check_delivery_log_total_quantity(sender, instance, **kwargs):
    """Проверка соответствия total_quantity после сохранения DeliveryLog"""
    instance.check_total_quantity()


@receiver(pre_save, sender=OrderItem)
def recalculate_order_price(sender, instance, **kwargs):
    """Пересчет цены позиции заказа перед сохранением, если количество изменилось"""
    if instance.price is None:
        instance.price = instance.product.price * instance.quantity
    elif instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.quantity != instance.quantity:
            instance.price = instance.product.price * instance.quantity


@receiver(post_save, sender=Order)
def update_shift_totals_on_order(sender, instance, created, **kwargs):
    """
    Пересчёт cash_total/card_total в смене при изменении заказа.

    ВАЖНО: используем агрегацию по всем DELIVERED заказам смены,
    а НЕ инкремент — иначе при повторном save() заказа сумма задвоится.
    Защита от trip=None: если заказ не привязан к рейсу, пропускаем.
    """
    if not instance.trip or not instance.trip.shift:
        return

    shift = instance.trip.shift

    # Агрегируем все DELIVERED заказы смены через OrderItem
    cash_total = OrderItem.objects.filter(
        order__trip__shift=shift,
        order__status=Order.Status.DELIVERED,
        order__payment_type=Order.PaymentType.CASH,
    ).aggregate(total=Sum('price'))['total'] or 0

    card_total = OrderItem.objects.filter(
        order__trip__shift=shift,
        order__status=Order.Status.DELIVERED,
        order__payment_type=Order.PaymentType.CARD,
    ).aggregate(total=Sum('price'))['total'] or 0

    # Используем queryset.update() — не вызывает post_save на CourierShift
    CourierShift.objects.filter(pk=shift.pk).update(
        cash_total=cash_total,
        card_total=card_total,
    )
