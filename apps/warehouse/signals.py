from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from apps.logistics.models import Order, OrderItem
from apps.products.models import Product
from .models import StockBalance, StockMovement
from django.db import models
from django.utils import timezone
from apps.accounting.models import Contract, SubjectContract
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def create_stock_balance_product(sender, instance, created, **kwargs):
    """Создание баланса продукта по созданному продукту"""
    if created:
        StockBalance.objects.create(product=instance, quantity=0)


# TODO: Устаревший сигнал, использовать Order
# @receiver(pre_save, sender=DeliveryJournalProducts)
# def track_delivery_journal_changes(sender, instance, **kwargs):
#     """Отслеживаем изменения до сохранения"""
#     if instance.pk:  # Если объект уже существует (обновление)
#         try:
#             old_instance = sender.objects.get(pk=instance.pk)
#             instance._old_quantity = old_instance.quantity
#             logger.debug("Сохранено старое значение quantity: %s для DeliveryJournalProducts ID=%s",
#                          instance._old_quantity, instance.pk)
#         except sender.DoesNotExist:
#             logger.warning("Не найден существующий DeliveryJournalProducts с ID=%s", instance.pk)


# TODO: Устаревший сигнал, использовать Order
# @receiver(post_save, sender=DeliveryJournalProducts)
# def update_stock_balance_on_delivery(sender, instance, created, **kwargs):
#     """Обновления остатков по данным с отчетов курьеров(с продаж)"""
#     logger.info("СИГНАЛ DeliveryJournalProducts ВЫЗВАН: ID=%s, created=%s", instance.pk, created)
#
#     product = instance.product
#
#     PRODUCT_MAP = {
#         Product.TypeProduct.BOTTLE_20L: Product.TypeProduct.BOTTLE,
#         # "вода с тарой" → "просто тара"
#     }
#
#     mapped_product_type = PRODUCT_MAP.get(product.type_product)
#     if mapped_product_type:
#         try:
#             product = Product.objects.get(type_product=mapped_product_type)
#             logger.info("Продукт подменён: действия будут выполняться с продуктом типа=%s", mapped_product_type)
#         except Product.DoesNotExist:
#             logger.warning("Продукт для подмены не найден: type=%s", mapped_product_type)
#             return
#
#     if created:
#         # Получение кол-во продукта
#         quantity_sold = instance.quantity
#
#         # Проверка наличия достаточного количества
#         try:
#             current_balance = StockBalance.objects.get(product=product)
#             if current_balance.quantity >= quantity_sold:
#                 # Создание записи движения товара
#                 StockMovement.objects.create(
#                     sold_product=product,
#                     operation_type=StockMovement.OperationTypeChoices.SELL,
#                     quantity=quantity_sold,
#                     note=f"Продажа через доставку #{instance.pk}"
#                 )
#
#                 # Обновление баланса
#                 StockBalance.objects.filter(product=product).update(
#                     quantity=models.F('quantity') - quantity_sold,
#                     last_departure_date=timezone.now()
#                 )
#                 logger.debug("Уменьшен StockBalance для продукта %s на %s", product, quantity_sold)
#             else:
#                 logger.warning("Недостаточно товара %s на складе. Запрошено: %s, доступно: %s",
#                                product, quantity_sold, current_balance.quantity)
#         except StockBalance.DoesNotExist:
#             logger.error("Не найден StockBalance для продукта %s", product)
#     else:
#         # Обработка обновления существующей записи
#         try:
#             # Получаем предыдущее значение
#             old_quantity = getattr(instance, '_old_quantity', 0)
#             new_quantity = instance.quantity
#
#             # Рассчитываем разницу
#             difference = new_quantity - old_quantity
#
#             if difference != 0:
#                 # Обновление баланса с учетом разницы
#                 current_balance = StockBalance.objects.get(product=product)
#
#                 if difference > 0:  # Увеличение количества проданных товаров
#                     # Проверяем наличие достаточного количества
#                     if current_balance.quantity >= difference:
#                         # Создаем запись о дополнительной продаже
#                         StockMovement.objects.create(
#                             sold_product=product,
#                             operation_type=StockMovement.OperationTypeChoices.SELL,
#                             quantity=difference,
#                             note=f"Обновленно: Дополнительная продажа через доставку #{instance.pk}"
#                         )
#
#                         # Обновляем баланс
#                         StockBalance.objects.filter(product=product).update(
#                             quantity=models.F('quantity') - difference,
#                             last_departure_date=timezone.now()
#                         )
#                         logger.debug('Уменьшен баланс при увеличении доставки для продукта %s на %s',
#                                      product, difference)
#                     else:
#                         logger.warning("Недостаточно товара %s на складе. Запрошено дополнительно: %s, доступно: %s",
#                                        product, difference, current_balance.quantity)
#
#                 else:  # difference < 0, уменьшение количества проданных товаров
#                     abs_difference = abs(difference)
#
#                     # Создаем запись о возврате товара как о покупке (поступлении)
#                     StockMovement.objects.create(
#                         sold_product=product,
#                         operation_type=StockMovement.OperationTypeChoices.BUY,
#                         quantity=abs_difference,
#                         note=f"Возврат товара от доставки #{instance.pk}"
#                     )
#
#                     # Обновляем баланс - увеличиваем количество на складе
#                     StockBalance.objects.filter(product=product).update(
#                         quantity=models.F('quantity') + abs_difference,
#                         last_received_date=timezone.now()
#                     )
#                     logger.debug('Увеличен баланс при уменьшении доставки для продукта %s на %s',
#                                  product, abs_difference)
#
#         except Exception as e:
#             logger.error("Ошибка при обновлении баланса: %s", e)
#
#     logger.info("СИГНАЛ DeliveryJournalProducts ЗАВЕРШЕН: ID=%s", instance.pk)


@receiver(pre_save, sender=SubjectContract)
def track_subject_contract_changes(sender, instance, **kwargs):
    """Отслеживаем изменения до сохранения"""
    if instance.pk:  # Если объект уже существует, обновление
        try:
            # Получаем старый объект
            old_instance = sender.objects.get(pk=instance.pk)
            # Сохраняем старое значение как атрибут
            instance._old_quantity = old_instance.quantity
            logger.debug("Сохранено старое значение quantity: %s", instance._old_quantity)
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender=SubjectContract)
def update_stock_balance_on_subject_contract(sender, instance, created, **kwargs):
    """Обновление остатков по данным с предметов контрактов"""
    # Проверяем, нужно ли учитывать этот продукт на складе
    if not instance.product.track_inventory:
        logger.info("Продукт %s не отслеживается на складе (track_inventory=False), пропускаем обновление остатков",
                   instance.product.name)
        return
    
    # Обновляем экземпляр из базы данных, чтобы получить актуальные данные
    instance.refresh_from_db()

    # Получаем необходимые данные
    product = instance.product
    quantity = instance.quantity
    note = str(instance)
    contract = instance.contract

    # Получаем или создаем запись в StockBalance
    stock_balance, _ = StockBalance.objects.get_or_create(product=product)

    # Обработка создания записи
    if created:
        if contract.contract_type == Contract.ContractType.SELL:
            StockMovement.objects.create(
                sold_product=product,
                contract=contract,
                operation_type=StockMovement.OperationTypeChoices.SELL,
                quantity=quantity,
                note=note
            )
            stock_balance.quantity -= quantity  # Уменьшаем количество на складе
            stock_balance.last_departure_date = timezone.now()

        elif contract.contract_type == Contract.ContractType.BUY:
            StockMovement.objects.create(
                sold_product=product,
                contract=contract,
                operation_type=StockMovement.OperationTypeChoices.BUY,
                quantity=quantity,
                note=note
            )
            stock_balance.quantity += quantity  # Увеличиваем количество на складе
            stock_balance.last_received_date = timezone.now()

    else:  # обработка обновления существующей записи
        # Получаем старое значение - используем сохраненное значение или получаем из БД
        old_quantity = getattr(instance, '_old_quantity',
                               instance.__class__.objects.get(pk=instance.pk).quantity)
        new_quantity = instance.quantity

        logger.debug("Старое количество: %s, Новое количество: %s для SubjectContract ID=%s",
                     old_quantity, new_quantity, instance.pk)

        # Вычисляем разницу
        difference = new_quantity - old_quantity

        # Обновление баланса только если есть изменения
        if difference != 0:
            if contract.contract_type == Contract.ContractType.SELL:
                if difference > 0:  # Увеличение продаж
                    # Проверяем достаточно ли остатков
                    if stock_balance.quantity >= difference:
                        # Создаем запись о дополнительной продаже
                        StockMovement.objects.create(
                            sold_product=product,
                            contract=contract,
                            operation_type=StockMovement.OperationTypeChoices.SELL,
                            quantity=difference,
                            note=f"{note} (дополнительная продажа)"
                        )

                        stock_balance.quantity -= difference
                        stock_balance.last_departure_date = timezone.now()
                        logger.debug('Уменьшаем количество на %s для продукта: %s (обновление SELL)',
                                     difference, stock_balance.product)
                    else:
                        logger.warning("Недостаточно товара %s на складе. Нужно: %s, доступно: %s",
                                       product, difference, stock_balance.quantity)

                else:  # difference < 0 уменьшение продажи
                    abs_difference = abs(difference)

                    # Для уменьшения продажи учитываем как покупку (возврат на склад)
                    StockMovement.objects.create(
                        sold_product=product,
                        contract=contract,
                        operation_type=StockMovement.OperationTypeChoices.BUY,  # используем BUY для возврата
                        quantity=abs_difference,
                        note=f"{note} (возврат товара)"
                    )

                    stock_balance.quantity += abs_difference
                    stock_balance.last_received_date = timezone.now()
                    logger.debug('Возврат на склад %s единиц продукта: %s (уменьшение продажи)',
                                 abs_difference, stock_balance.product)

            elif contract.contract_type == Contract.ContractType.BUY:
                if difference > 0:  # Увеличение закупки
                    # Создаем запись о дополнительной закупке
                    StockMovement.objects.create(
                        sold_product=product,
                        contract=contract,
                        operation_type=StockMovement.OperationTypeChoices.BUY,
                        quantity=difference,
                        note=f"{note} (дополнительная закупка)"
                    )

                    stock_balance.quantity += difference
                    stock_balance.last_received_date = timezone.now()
                    logger.debug('Увеличиваем количество на %s для продукта: %s (увеличение закупки)',
                                 difference, stock_balance.product)

                else:  # difference < 0, уменьшение закупки
                    abs_difference = abs(difference)

                    # Проверка наличия достаточного количества на складе
                    if stock_balance.quantity >= abs_difference:
                        # Для уменьшения закупки учитываем как продажу (изъятие со склада)
                        StockMovement.objects.create(
                            sold_product=product,
                            contract=contract,
                            operation_type=StockMovement.OperationTypeChoices.SELL,  # используем SELL для изъятия
                            quantity=abs_difference,
                            note=f"{note} (уменьшение закупки)"
                        )

                        stock_balance.quantity -= abs_difference
                        stock_balance.last_departure_date = timezone.now()
                        logger.debug('Уменьшаем количество на %s для продукта: %s (уменьшение закупки)',
                                     abs_difference, stock_balance.product)
                    else:
                        logger.warning(
                            "Недостаточно товара %s на складе для уменьшения закупки. Нужно: %s, доступно: %s",
                            product, abs_difference, stock_balance.quantity)

        # Сохраняем изменения в StockBalance
    stock_balance.save()
    logger.info("СИГНАЛ SubjectContract ЗАВЕРШЕН: ID=%s, stock_balance=%s",
                instance.pk, stock_balance.quantity)


@receiver(pre_delete, sender=SubjectContract)
def update_stock_before_subject_contract_delete(sender, instance, **kwargs):
    """Обновление остатков перед удалением предмета контракта"""
    # Проверяем, нужно ли учитывать этот продукт на складе
    if not instance.product.track_inventory:
        logger.info("Продукт %s не отслеживается на складе (track_inventory=False), пропускаем обновление остатков при удалении",
                   instance.product.name)
        return
    
    logger.info("СИГНАЛ pre_delete SubjectContract ВЫЗВАН: ID=%s", instance.pk)

    product = instance.product
    quantity = instance.quantity
    contract_type = instance.contract.contract_type  # Получаем тип контракта
    note = f"Удаление {str(instance)}"

    try:
        stock_balance = StockBalance.objects.get(product=product)

        if contract_type == Contract.ContractType.SELL:
            # Если удаляется предмет контракта продажи возвращаем товар на склад
            StockMovement.objects.create(
                sold_product=product,
                contract=instance.contract,
                operation_type=StockMovement.OperationTypeChoices.BUY,  # Возврат = BUY
                quantity=quantity,
                note=note
            )
            stock_balance.quantity += quantity
            stock_balance.last_received_date = timezone.now()
            logger.debug('Возврат %s единиц продукта %s на склад при удалении продажи', quantity, product)

        elif contract_type == Contract.ContractType.BUY:
            # Если удаляется предмет контракта закупки изымаем товар со склада
            if stock_balance.quantity >= quantity:
                StockMovement.objects.create(
                    sold_product=product,
                    contract=instance.contract,
                    operation_type=StockMovement.OperationTypeChoices.SELL,  # Изъятие = SELL
                    quantity=quantity,
                    note=note
                )
                stock_balance.quantity -= quantity
                stock_balance.last_departure_date = timezone.now()
                logger.debug('Удалено %s единиц продукта %s со склада при удалении закупки', quantity, product)
            else:
                logger.warning("Недостаточно товара на складе %s для удаления закупки. Нужно: %s, доступно: %s",
                               product, quantity, stock_balance.quantity)

        stock_balance.save()

    except StockBalance.DoesNotExist:
        logger.error("Не найден StockBalance для продукта %s при удалении SubjectContract ID=%s", product, instance.pk)

    logger.info("СИГНАЛ pre_delete SubjectContract ЗАВЕРШЕН: ID=%s", instance.pk)


@receiver(post_save, sender=Order)
def update_stock_on_order(sender, instance, created, **kwargs):
    """Обновление остатков склада при подтверждении заказа (статус DELIVERED)"""
    if instance.status != Order.Status.DELIVERED:
        return

    # Проходим по всем позициям заказа
    for item in instance.items.all():
        product = item.product
        
        # Для обратной совместимости: если продукт BOTTLE_20L, подменяем на BOTTLE
        PRODUCT_MAP = {
            Product.TypeProduct.BOTTLE_20L: Product.TypeProduct.BOTTLE,
        }

        mapped_product_type = PRODUCT_MAP.get(product.type_product)
        if mapped_product_type:
            try:
                product = Product.objects.get(type_product=mapped_product_type)
                logger.info("Продукт подменён: %s -> %s", product.type_product, mapped_product_type)
            except Product.DoesNotExist:
                logger.warning("Продукт для подмены не найден: type=%s", mapped_product_type)
                continue

        # Определяем количество для списания
        # Для BOTTLE_20L (вода с тарой): списываем exchange_qty (обмен) + sell_with_qty (продажа с тарой)
        # Так как мы больше не создаем отдельную позицию BOTTLE OrderItem,
        # мы должны списать всю тару, которая ушла клиенту (и по обмену, и проданную).
        # Для остальных продуктов: списываем quantity
        original_product = item.product
        if original_product.type_product == Product.TypeProduct.BOTTLE_20L:
            quantity_to_deduct = item.exchange_qty + item.sell_with_qty
        else:
            quantity_to_deduct = item.quantity
        
        try:
            stock_balance = StockBalance.objects.get(product=product)
            if stock_balance.quantity >= quantity_to_deduct:
                StockMovement.objects.create(
                    sold_product=product,
                    operation_type=StockMovement.OperationTypeChoices.SELL,
                    quantity=quantity_to_deduct,
                    note=f"Заказ #{instance.pk}, позиция #{item.id} ({product.get_type_product_display()})"
                )
                stock_balance.quantity -= quantity_to_deduct
                stock_balance.last_departure_date = timezone.now()
                stock_balance.save()
                logger.debug("Списано %s единиц продукта %s по заказу #%s", quantity_to_deduct, product, instance.pk)
            else:
                logger.warning("Недостаточно товара %s на складе для заказа #%s. Запрошено: %s, доступно: %s",
                               product, instance.pk, quantity_to_deduct, stock_balance.quantity)
        except StockBalance.DoesNotExist:
            logger.error("Не найден StockBalance для продукта %s", product)
        
        # Логируем операции с тарой для отладки (если это продукт WATER)
        if product.type_product == Product.TypeProduct.WATER:
            if item.exchange_qty > 0:
                logger.info("Заказ #%s, позиция #%s - обмен %s шт. тары (не списывается со склада)",
                            instance.pk, item.id, item.exchange_qty)
            if item.sell_with_qty > 0:
                logger.info("Заказ #%s, позиция #%s - продажа с тарой %s шт. (тара создана отдельной позицией)",
                            instance.pk, item.id, item.sell_with_qty)
            if item.defective_qty > 0:
                logger.info("Заказ #%s, позиция #%s - брак %s шт. (не списывается со склада)",
                            instance.pk, item.id, item.defective_qty)
