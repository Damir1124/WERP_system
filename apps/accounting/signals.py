from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import (
    PaymentsInstallment, Salary, SalaryPeriod, SalaryPayment,
    FinancialTransactions, Contract, Installment, InstallmentItem,
)
from . import utils
from apps.logistics import models as logistics
from apps.logistics.models import Order


# Installment и PaymentsInstallment
@receiver(pre_save, sender=PaymentsInstallment)
def calculate_installment_payment(sender, instance, **kwargs):
    """Пересчет суммы и статуса рассрочки перед сохранением платежа"""
    if instance.pk:  # Если объект уже существует
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.amount != instance.amount:
            # Обновляем рассрочку, если сумма платежа изменилась
            installment = instance.installment
            installment.paid_amount -= old_instance.amount  # Убираем старую сумму
            installment.paid_amount += instance.amount  # Добавляем новую сумму
            installment.check_status()  # Проверяем статус рассрочки
            installment.save()

        # Обновляем due_date если изменилась дата платежа
        if old_instance.payment_date != instance.payment_date:
            utils.update_due_date(instance.installment)


@receiver(post_save, sender=PaymentsInstallment)
def update_installment_on_payment(sender, instance, created, **kwargs):
    """Обновление рассрочки при добавлении или изменении платежа"""
    if created:
        installment = instance.installment
        installment.make_payment(instance.amount)  # Обновляем сумму и статус рассрочки
        utils.update_due_date(installment)  # Обновление даты след. платeжа


# Installment — рассрочка по заказу
@receiver(post_save, sender=Installment)
def generate_items_from_order(sender, instance, created, **kwargs):
    """Авто-генерация позиций рассрочки из заказа и удаление PLUS-транзакции заказа.

    Если рассрочка привязана к заказу (instance.order):
    1. Подставляем issued_by из курьера заказа (если не указан вручную);
    2. Создаём InstallmentItem из OrderItem (товар, количество, цена);
    3. Пересчитываем amount из позиций;
    4. Удаляем существующую PLUS-транзакцию заказа, чтобы не было двойного учёта
       (доход теперь фиксируется только по платежам PaymentsInstallment).
    """
    if not instance.order:
        return

    order = instance.order

    # 1. Подставляем курьера, если issued_by не указан
    # Используем queryset.update() — НЕ вызывает сигналы (защита от рекурсии)
    if not instance.issued_by and order.assigned_courier:
        Installment.objects.filter(pk=instance.pk).update(issued_by=order.assigned_courier)
        instance.issued_by = order.assigned_courier

    # 1.1 Авто-установка даты следующего платежа (сегодня + 1 месяц), если не указана
    if not instance.due_date:
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        new_due_date = timezone.now().date() + relativedelta(months=1)
        Installment.objects.filter(pk=instance.pk).update(due_date=new_due_date)
        instance.due_date = new_due_date

    # 2. Создаём позиции из заказа, если их ещё нет
    if not instance.items.exists():
        for order_item in order.items.select_related('product').all():
            InstallmentItem.objects.create(
                installment=instance,
                product=order_item.product,
                quantity=order_item.quantity,
                price_per_unit=order_item.product.price,
            )

    # 3. Пересчитываем сумму
    instance.recalc_amount()

    # 4. Удаляем PLUS-транзакцию заказа (доход только по платежам)
    FinancialTransactions.objects.filter(
        date=order.delivered_at.date() if order.delivered_at else None,
        source__startswith=f"Заказ #{order.pk}",
    ).delete()
    if order.delivered_at:
        utils.update_finance_record(order.delivered_at.date())


@receiver(post_delete, sender=Installment)
def restore_order_transaction_on_installment_delete(sender, instance, **kwargs):
    """Восстановление PLUS-транзакции заказа при удалении рассрочки.

    Если рассрочка была привязана к заказу и заказ доставлен —
    восстанавливаем доходную транзакцию заказа (деньги снова учитываются).
    """
    if not instance.order:
        return

    order = instance.order
    if order.status != Order.Status.DELIVERED or not order.delivered_at:
        return

    total_price = order.get_total_price()
    card_amount = total_price if order.payment_type == Order.PaymentType.CARD else 0

    FinancialTransactions.objects.create(
        date=order.delivered_at.date(),
        transaction_type=FinancialTransactions.TransactionsType.PLUS,
        amount=total_price,
        card_amount=card_amount,
        source=f"Заказ #{order.pk} — {order.client}"
    )
    utils.update_finance_record(order.delivered_at.date())


# =============================================================================
# Worker -> Salary (авто-создание карточки зарплаты)
# =============================================================================

@receiver(post_save, sender='workers.Worker')
def create_salary_for_worker(sender, instance, created, **kwargs):
    """Авто-создание записи Salary при создании сотрудника."""
    if created:
        Salary.objects.get_or_create(worker=instance)


# =============================================================================
# Salary и SalaryPayment (учёт по календарным месяцам)
# =============================================================================

def get_or_create_period(salary, date):
    """Возвращает зарплатный период для указанной даты (первый день месяца)."""
    month = date.replace(day=1)
    period, _ = SalaryPeriod.objects.get_or_create(
        worker=salary.worker,
        month=month,
        defaults={'salary_amount': salary.worker.salary_amount or 0},
    )
    return period


@receiver(pre_save, sender=SalaryPayment)
def calculate_salary_payment(sender, instance, **kwargs):
    """Пересчёт баланса и даты последней выплаты перед сохранением платежа."""
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        salary = instance.salary

        # Убираем старую сумму из баланса
        if old_instance.payment_type in [SalaryPayment.PaymentType.SALARY,
                                         SalaryPayment.PaymentType.BONUS,
                                         SalaryPayment.PaymentType.ADVANCE]:
            salary.balance -= old_instance.amount
        elif old_instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance += old_instance.amount

        # Добавляем новую сумму в баланс
        if instance.payment_type in [SalaryPayment.PaymentType.SALARY,
                                     SalaryPayment.PaymentType.BONUS,
                                     SalaryPayment.PaymentType.ADVANCE]:
            salary.balance += instance.amount
        elif instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance -= instance.amount

        # Обновляем дату последней выплаты, если это зарплата
        if instance.payment_type == SalaryPayment.PaymentType.SALARY:
            salary.last_payment = instance.date

        salary.save()


@receiver(post_save, sender=SalaryPayment)
def update_salary_on_payment(sender, instance, created, **kwargs):
    """Обновление баланса, периода и даты последней выплаты при добавлении платежа."""
    salary = instance.salary

    # Авто-привязка платежа к зарплатному периоду
    if not instance.period_id:
        period = get_or_create_period(salary, instance.date)
        SalaryPayment.objects.filter(pk=instance.pk).update(period=period)
        instance.period = period

    if created:
        utils.reset_balance_if_expired(salary)

        # Обновляем баланс в зависимости от типа платежа
        if instance.payment_type in [SalaryPayment.PaymentType.SALARY,
                                     SalaryPayment.PaymentType.BONUS,
                                     SalaryPayment.PaymentType.ADVANCE]:
            salary.balance += instance.amount
        elif instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance -= instance.amount

        # Обновляем дату последней выплаты, если это зарплата
        if instance.payment_type == SalaryPayment.PaymentType.SALARY:
            salary.last_payment = instance.date

        salary.save()

    # Пересчитываем итоги зарплатного периода
    if instance.period_id:
        instance.period.recalc()


# Contract
@receiver(pre_save, sender=Contract)
def update_transactions_on_contract_update(sender, instance, **kwargs):
    """Сохранение данных перед обновлением"""
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.amount != instance.amount or old_instance.contract_type != instance.contract_type:
            FinancialTransactions.objects.filter(
                date=old_instance.date,
                source=f"Пополнение за: {old_instance.__str__()[:200]}"
            ).delete()
            update_transactions_on_contract(sender, instance, created=True)


@receiver(post_save, sender=Contract)
def update_transactions_on_contract(sender, instance, created, **kwargs):
    """Создание или обновление данных"""
    if created:
        if instance.contract_type == Contract.ContractType.BUY:
            source = f"Пополнение за: {instance.__str__()[:200]}"
            FinancialTransactions.objects.create(
                date=instance.date,
                transaction_type=FinancialTransactions.TransactionsType.PLUS,
                amount=instance.amount or 0,
                description=instance.note,
                source=source
            )
        else:
            source = f"Списание за: {instance.__str__()[:200]}"
            FinancialTransactions.objects.create(
                date=instance.date,
                transaction_type=FinancialTransactions.TransactionsType.MINUS,
                amount=instance.amount or 0,
                source=source
            )
    utils.update_finance_record(instance.date)


@receiver(post_delete, sender=Contract)
def delete_transactions_on_contract_delete(sender, instance, **kwargs):
    """Обновление данных после удаления"""
    FinancialTransactions.objects.filter(
        date=instance.date,
        source__startswith=f"Пополнение за: {instance.__str__()[:200]}"
    ).delete()
    utils.update_finance_record(instance.date)


# DeliveryJournal — сигналы удалены, т.к. модель DeliveryJournal устарела (P0 архитектура).
# Финансовые транзакции теперь создаются через сигнал на Order (см. ниже).


# SalaryPayment
@receiver(pre_save, sender=SalaryPayment)
def update_transactions_on_salary_update(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.amount != instance.amount or old_instance.payment_type != instance.payment_type:
            FinancialTransactions.objects.filter(
                date=old_instance.date,
                source=f"Списание за: {old_instance.__str__()[:200]}"
            ).delete()
            update_transactions_on_salary(sender, instance, created=True)


@receiver(post_save, sender=SalaryPayment)
def update_transactions_on_salary(sender, instance, created, **kwargs):
    if created:
        if instance.payment_type == SalaryPayment.PaymentType.FINE:
            source = f"Пополнение за: {instance.__str__()[:200]}"
            FinancialTransactions.objects.create(
                date=instance.date,
                transaction_type=FinancialTransactions.TransactionsType.PLUS,
                amount=instance.amount or 0,
                source=source
            )
        else:
            source = f"Списание за: {instance.__str__()[:200]}"
            FinancialTransactions.objects.create(
                date=instance.date,
                transaction_type=FinancialTransactions.TransactionsType.MINUS,
                amount=instance.amount or 0,
                source=source
            )
    utils.update_finance_record(instance.date)


@receiver(post_delete, sender=SalaryPayment)
def delete_transactions_on_salary_delete(sender, instance, **kwargs):
    FinancialTransactions.objects.filter(
        date=instance.date,
        source__startswith=f"Списание за: {instance.__str__()[:200]}"
    ).delete()
    utils.update_finance_record(instance.date)


# PaymentsInstallment
@receiver(pre_save, sender=PaymentsInstallment)
def update_transactions_on_installment_update(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.amount != instance.amount:
            FinancialTransactions.objects.filter(
                date=old_instance.payment_date,
                source=f"Пополнение за: {old_instance.__str__()[:200]}"
            ).delete()
            update_transactions_on_installment(sender, instance, created=True)


@receiver(post_save, sender=PaymentsInstallment)
def update_transactions_on_installment(sender, instance, created, **kwargs):
    if created:
        source = f"Пополнение за: {instance.__str__()[:200]}"
        FinancialTransactions.objects.create(
            date=instance.payment_date,
            transaction_type=FinancialTransactions.TransactionsType.PLUS,
            amount=instance.amount or 0,
            source=source
        )
    utils.update_finance_record(instance.payment_date)


@receiver(post_delete, sender=PaymentsInstallment)
def delete_transactions_on_installment_delete(sender, instance, **kwargs):
    FinancialTransactions.objects.filter(
        date=instance.payment_date,
        source__startswith=f"Пополнение за: {instance.__str__()[:200]}"
    ).delete()
    utils.update_finance_record(instance.payment_date)


@receiver(pre_save, sender=FinancialTransactions)
def update_finance_on_transaction_update(sender, instance, **kwargs):
    """Обновляет запись в Finance перед изменением FinancialTransactions"""
    if instance.pk:  # Проверяем, существует ли объект, это обновление, а не создание
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.date != instance.date:
            # если дата изменилась, обновляем записи для обеих дат
            utils.update_finance_record(old_instance.date)
            utils.update_finance_record(instance.date)
        else:
            # если дата не изменилась, обновляем запись для текущей даты
            utils.update_finance_record(instance.date)


@receiver(post_save, sender=FinancialTransactions)
def update_finance_on_transaction_create(sender, instance, created, **kwargs):
    """Обновляет запись в Finance при создании FinancialTransactions"""
    utils.update_finance_record(instance.date)


@receiver(post_save, sender=Order)
def create_transaction_on_order(sender, instance, created, **kwargs):
    """Создание финансовой транзакции при подтверждении заказа (статус DELIVERED)"""
    if instance.status != Order.Status.DELIVERED:
        return

    # Если заказ переведён в рассрочку — доход фиксируется только по платежам,
    # PLUS-транзакцию на полную сумму не создаём (страховка от двойного учёта)
    if Installment.objects.filter(order=instance).exists():
        return

    # Если заказ не привязан к рейсу — нет смены, нет даты → пропускаем
    if not instance.trip or not instance.trip.shift:
        return

    # Определяем тип транзакции (PLUS - доход)
    from .models import FinancialTransactions
    transaction_type = FinancialTransactions.TransactionsType.PLUS

    # Определяем сумму через OrderItem (поля price/quantity перенесены туда)
    total_price = instance.get_total_price()
    card_amount = total_price if instance.payment_type == Order.PaymentType.CARD else 0

    # Создаем транзакцию
    FinancialTransactions.objects.create(
        date=instance.trip.shift.date,
        transaction_type=transaction_type,
        amount=total_price,
        card_amount=card_amount,
        source=f"Заказ #{instance.pk} — {instance.client}"
    )

    # Обновляем сводку по финансам
    utils.update_finance_record(instance.trip.shift.date)
