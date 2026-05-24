from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import DeliveryLog, DeliveryLogMove, Order, CourierShift


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


@receiver(pre_save, sender=Order)
def recalculate_order_price(sender, instance, **kwargs):
    """Пересчет цены заказа перед сохранением, если количество изменилось"""
    if instance.price is None:
        instance.price = instance.product.price * instance.quantity
    elif instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.quantity != instance.quantity:
            instance.price = instance.product.price * instance.quantity


@receiver(post_save, sender=Order)
def update_shift_totals_on_order(sender, instance, created, **kwargs):
    """Обновление cash_total/card_total в смене при изменении заказа"""
    if instance.status == Order.Status.DELIVERED:
        shift = instance.trip.shift
        if instance.payment_type == Order.PaymentType.CARD:
            shift.card_total += instance.price
        else:
            shift.cash_total += instance.price
        shift.save(update_fields=['cash_total', 'card_total'])
