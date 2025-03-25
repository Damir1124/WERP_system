from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.logistics.models import DeliveryJournalProducts
from apps.products.models import Product
from .models import StockBalance
from django.db import models
from apps.accounting.models import Contract

@receiver(post_save, sender=Product)
def create_stock_balance_product(sender, instance, created, **kwargs):
    """Создание баланса продукта по созданному продукту"""
    if created:
        StockBalance.objects.create(product=instance, quantitly=0)


@receiver(post_save, sender=DeliveryJournalProducts)
def update_stock_balance_on_delivery(sender, isntance, created, **kwargs):
    """Обновления остатков по данным с отчетов курьеров(с продаж)"""
    if created:
        # Получение кол-во продукта
        quantitly_sold = isntance.quantitly
        product = isntance.product

        # Обновление баланса
        StockBalance.objects.filter(product=product).update(
            quantity=models.F('quantitly') - quantitly_sold
        )

@receiver(post_save, sender=Contract)
def update_stock_balance_on_contract(sender,  isntance, created, **kwargs):
    """Обновления остатков по данным с контрактов"""
    if created:
        if Contract.ContractType.SELL:
            StockBalance.objects.filter(product=product).update(
                quantity=models.F('quantitly') - quantitly_sold
            )
