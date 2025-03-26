from itertools import product

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.logistics.models import DeliveryJournalProducts
from apps.products.models import Product
from .models import StockBalance, StockMovement
from django.db import models
from apps.accounting.models import Contract, SubjectContract
import logging

logger = logging.getLogger(__name__)

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
def update_stock_balance_on_contract(sender, instance, created, **kwargs):
    """Обновления остатков по данным с контрактов"""
    logger.info('Сигнал сработал')
    print('signal open')
    if created:
        # Получаем все связанные SubjectContract
        subject_contracts = SubjectContract.objects.filter(contract=instance)

        for subject in subject_contracts:
            product = subject.product
            quantitly = subject.quantitly
            note = str(subject)
            print('check product')

            # Добавляет продукты в StockMovement при контракте на продажу
            if instance.contract_type == Contract.ContractType.SELL:
                stock_movement_sell = StockMovement.objects.create(
                    sold_product=product,
                    contract=instance,
                    operation_type=StockMovement.OperationTypeChoices.SELL,
                    quantitly=quantitly,
                    note=note
                )
                stock_movement_sell.save()

                StockBalance.objects.filter(product=stock_movement_sell.sold_product).update_or_create(
                    quantitly=models.F('quantitly') - stock_movement_sell.quantity
                )

            # Добавляет продукты в StockMovement при контракте на продажу
            elif instance.contract_type == Contract.ContractType.BUY:
                stock_movement_buy = StockMovement.objects.create(
                    sold_product=product,
                    contract=instance,
                    operation_type=StockMovement.OperationTypeChoices.BUY,
                    quantity=quantitly,
                    note=note
                )

                StockBalance.objects.filter(product=stock_movement_buy.sold_product).update_or_create(
                    quantitly=models.F('quantitly') + stock_movement_buy.quantity
                )




