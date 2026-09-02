from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import models
import logging

from apps.products.models import Product
from apps.logistics.models import Order
from apps.accounting.models import SubjectContract
from .models import (
    WarehouseProduct,
    WarehouseStockBalance,
    WarehouseStockMovement,
    WarehouseInventoryAdjustment,
)

logger = logging.getLogger(__name__)


# ─── Авто-создание остатка при создании складского продукта ──────────────────


@receiver(post_save, sender=WarehouseProduct)
def create_warehouse_stock_balance(sender, instance, created, **kwargs):
    """Создание баланса складского продукта при его создании"""
    if created:
        WarehouseStockBalance.objects.get_or_create(
            warehouse_product=instance,
            defaults={'quantity': 0}
        )
        logger.info("Создан WarehouseStockBalance для складского продукта %s", instance.name)


# ─── Обновление остатка при движении (приход/расход) ─────────────────────────


@receiver(post_save, sender=WarehouseStockMovement)
def update_balance_on_warehouse_movement(sender, instance, created, **kwargs):
    """Обновление остатка при создании движения (приход/расход)"""
    if not created:
        return

    balance, _ = WarehouseStockBalance.objects.get_or_create(
        warehouse_product=instance.warehouse_product,
        defaults={'quantity': 0}
    )

    if instance.operation_type == WarehouseStockMovement.OperationType.INCOME:
        balance.quantity += instance.quantity
        balance.last_received_date = timezone.now()
    elif instance.operation_type == WarehouseStockMovement.OperationType.EXPENSE:
        balance.quantity = max(0, balance.quantity - instance.quantity)
        balance.last_departure_date = timezone.now()

    balance.save(update_fields=['quantity', 'last_received_date', 'last_departure_date'])
    logger.info(
        "Движение %s: %s %s шт. Остаток теперь: %s",
        instance.get_operation_type_display(),
        instance.warehouse_product.name,
        instance.quantity,
        balance.quantity,
    )


# ─── Обновление остатка при ручной корректировке ─────────────────────────────


@receiver(post_save, sender=WarehouseInventoryAdjustment)
def update_balance_on_warehouse_adjustment(sender, instance, created, **kwargs):
    """Запись движения при корректировке.

    Баланс обновляется автоматически сигналом update_balance_on_warehouse_movement
    при создании WarehouseStockMovement (единая точка обновления).
    """
    # Для SET вычисляем разницу между новым и текущим значением
    if instance.adjustment_type == WarehouseInventoryAdjustment.AdjustmentType.SET:
        balance, _ = WarehouseStockBalance.objects.get_or_create(
            warehouse_product=instance.warehouse_product,
            defaults={'quantity': 0}
        )
        diff = instance.quantity - balance.quantity
        if diff > 0:
            operation = WarehouseStockMovement.OperationType.INCOME
            quantity = diff
        elif diff < 0:
            operation = WarehouseStockMovement.OperationType.EXPENSE
            quantity = abs(diff)
        else:
            return  # значение не изменилось, движение не нужно
    elif instance.adjustment_type == WarehouseInventoryAdjustment.AdjustmentType.INCREASE:
        operation = WarehouseStockMovement.OperationType.INCOME
        quantity = instance.quantity
    else:  # DECREASE
        operation = WarehouseStockMovement.OperationType.EXPENSE
        quantity = instance.quantity

    # Запись в журнал движений для аудита (баланс обновится сигналом движения)
    WarehouseStockMovement.objects.create(
        warehouse_product=instance.warehouse_product,
        operation_type=operation,
        quantity=quantity,
        note=f'Корректировка инвентаря: {instance.reason}. {instance.note or ""}'
    )
    logger.info(
        "Корректировка %s для %s: %s %s шт.",
        instance.get_adjustment_type_display(),
        instance.warehouse_product.name,
        operation,
        quantity,
    )


# ─── Авто-списание при продажах Product через маппинг ────────────────────────


def _deduct_warehouse_for_product(product, quantity, note):
    """Списывает складские продукты по маппингу для проданного Product.

    Создаёт движение EXPENSE — баланс обновится автоматически
    сигналом update_balance_on_warehouse_movement (единая точка обновления).
    """
    mappings = product.warehouse_mappings.select_related('warehouse_product').all()
    if not mappings.exists():
        return False

    for mapping in mappings:
        wp = mapping.warehouse_product
        qty_to_deduct = mapping.coefficient * quantity

        balance, _ = WarehouseStockBalance.objects.get_or_create(
            warehouse_product=wp,
            defaults={'quantity': 0}
        )

        if balance.quantity >= qty_to_deduct:
            WarehouseStockMovement.objects.create(
                warehouse_product=wp,
                operation_type=WarehouseStockMovement.OperationType.EXPENSE,
                quantity=qty_to_deduct,
                note=note
            )
            logger.info(
                "Списано %d ед. складского продукта %s (маппинг %s → %s, коэф. %s)",
                qty_to_deduct, wp.name, product.name, wp.name, mapping.coefficient,
            )
        else:
            logger.warning(
                "Недостаточно складского продукта %s. Нужно: %s, доступно: %s",
                wp.name, qty_to_deduct, balance.quantity,
            )
    return True


@receiver(post_save, sender=Order)
def deduct_warehouse_on_order(sender, instance, created, **kwargs):
    """Списание складских продуктов при подтверждении заказа (статус DELIVERED)"""
    if instance.status != Order.Status.DELIVERED:
        return

    for item in instance.items.select_related('product').all():
        _deduct_warehouse_for_product(
            product=item.product,
            quantity=item.quantity,
            note=f"Заказ #{instance.pk}, позиция #{item.id} ({item.product.name})"
        )


@receiver(post_save, sender=SubjectContract)
def deduct_warehouse_on_subject_contract(sender, instance, created, **kwargs):
    """Списание/оприходование складских продуктов по предметам контрактов.

    Поддерживает два типа предметов:
    - instance.product (Product ассортимента) — через маппинг ProductWarehouseMapping;
    - instance.warehouse_product (WarehouseProduct, комплектующие) — напрямую.
    """
    contract_type = instance.contract.contract_type

    # ── Закупка комплектующих напрямую (WarehouseProduct) ──────────────────────
    if instance.warehouse_product:
        wp = instance.warehouse_product
        if contract_type == 'BY':  # закупка — приход на склад
            WarehouseStockMovement.objects.create(
                warehouse_product=wp,
                operation_type=WarehouseStockMovement.OperationType.INCOME,
                quantity=instance.quantity,
                note=f"Контракт #{instance.contract.pk} (закупка комплектующих): {instance}"
            )
            logger.info(
                "Оприходовано %s ед. складского продукта %s (закупка комплектующих по контракту #%s)",
                instance.quantity, wp.name, instance.contract.pk,
            )
        elif contract_type == 'SL':  # продажа комплектующих — расход со склада
            WarehouseStockMovement.objects.create(
                warehouse_product=wp,
                operation_type=WarehouseStockMovement.OperationType.EXPENSE,
                quantity=instance.quantity,
                note=f"Контракт #{instance.contract.pk} (продажа комплектующих): {instance}"
            )
            logger.info(
                "Списано %s ед. складского продукта %s (продажа комплектующих по контракту #%s)",
                instance.quantity, wp.name, instance.contract.pk,
            )
        return

    # ── Товар ассортимента (Product) через маппинг ─────────────────────────────
    if not instance.product:
        return

    if contract_type == 'SL':  # SELL — продажа, списываем со склада
        _deduct_warehouse_for_product(
            product=instance.product,
            quantity=instance.quantity,
            note=f"Контракт #{instance.contract.pk} (продажа): {instance}"
        )
    elif contract_type == 'BY':  # BUY — закупка, приходуем на склад
        mappings = instance.product.warehouse_mappings.select_related('warehouse_product').all()
        for mapping in mappings:
            wp = mapping.warehouse_product
            qty = mapping.coefficient * instance.quantity
            # Создаём движение INCOME — баланс обновится сигналом движения
            WarehouseStockMovement.objects.create(
                warehouse_product=wp,
                operation_type=WarehouseStockMovement.OperationType.INCOME,
                quantity=qty,
                note=f"Контракт #{instance.contract.pk} (закупка): {instance}"
            )
            logger.info(
                "Оприходовано %s ед. складского продукта %s (закупка по контракту #%s)",
                qty, wp.name, instance.contract.pk,
            )