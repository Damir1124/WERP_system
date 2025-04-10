from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import DeliveryLog, DeliveryLogMove, DeliveryJournalProducts


@receiver(post_save, sender=DeliveryLogMove)
def update_delivery_log_totals(sender, instance, **kwargs):
    """Обновление total_quantity и total_sold в DeliveryLog после изменения DeliveryLogMove"""
    delivery_log = instance.delivery_log
    delivery_log.calculate_total_quantity()
    delivery_log.calculate_total_sold()
    delivery_log.save()


@receiver(post_save, sender=DeliveryLog)
def check_delivery_log_total_quantity(sender, instance, **kwargs):
    """Проверка соответствия total_quantity после сохранения DeliveryLog"""
    instance.check_total_quantity()


@receiver(post_save, sender=DeliveryJournalProducts)
def update_delivery_journal_total_price(sender, instance, **kwargs):
    """Пересчет total_price в DeliveryJournal после изменения DeliveryJournalProducts"""
    delivery_journal = instance.delivery_journal
    delivery_journal.update_total_price()


@receiver(pre_save, sender=DeliveryJournalProducts)
def recalculate_price(sender, instance, **kwargs):
    """Пересчет цены перед сохранением, если количество изменилось"""
    if instance.pk:  # Если объект уже существует
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.quantity != instance.quantity:
            # Пересчитываем цену только если количество изменилось
            instance.price = instance.product.price * instance.quantity
    else:
        # Если объект новый устанавливаем цену
        instance.price = instance.product.price * instance.quantity


@receiver(post_save, sender=DeliveryJournalProducts)
def update_delivery_journal_totals(sender, instance, **kwargs):
    """Пересчет total_price и card_price в DeliveryJournal после изменения DeliveryJournalProducts"""
    delivery_journal = instance.delivery_journal
    total_price = 0
    card_price = 0

    for product in delivery_journal.products.all():
        if product.payment_type == DeliveryJournalProducts.PaymentsType.BONUS:
            total_price -= abs(product.price) or 0  # Вычитаем при бонусной оплате
        elif product.payment_type == DeliveryJournalProducts.PaymentsType.CARD:
            card_price += product.price or 0  # Прибавляем при оплате картой
        else:
            total_price += product.price or 0  # Прибавляем в остальных случаях

    delivery_journal.total_price = total_price
    delivery_journal.card_price = card_price
    delivery_journal.save()
