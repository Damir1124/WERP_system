from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import PaymentsInstallment, SalaryPayment, FinancialTransactions, Contract
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


# Salary и SalaryPayment
@receiver(pre_save, sender=SalaryPayment)
def calculate_salary_payment(sender, instance, **kwargs):
    """Пересчет баланса и даты последней выплаты перед сохранением платежа"""
    if instance.pk:  # Если объект уже существует
        old_instance = sender.objects.get(pk=instance.pk)
        salary = instance.salary

        # Убираем старую сумму из баланса
        if old_instance.payment_type in [SalaryPayment.PaymentType.SALARY, SalaryPayment.PaymentType.BONUS]:
            salary.balance -= old_instance.amount
        elif old_instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance += old_instance.amount

        # Добавляем новую сумму в баланс
        if instance.payment_type in [SalaryPayment.PaymentType.SALARY, SalaryPayment.PaymentType.BONUS]:
            salary.balance += instance.amount
        elif instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance -= instance.amount

        # Обновляем дату последней выплаты, если это зарплата
        if instance.payment_type == SalaryPayment.PaymentType.SALARY:
            salary.last_payment = instance.date

        salary.save()


# Salary и SalaryPayment
@receiver(post_save, sender=SalaryPayment)
def update_salary_on_payment(sender, instance, created, **kwargs):
    """Обновление баланса и даты последней выплаты при добавлении платежа"""
    if created:
        salary = instance.salary

        utils.reset_balance_if_expired(salary)  # проверяем и обнуляем если нужно

        # обновляем баланс в зависимости от типа платежа
        if instance.payment_type in [SalaryPayment.PaymentType.SALARY, SalaryPayment.PaymentType.BONUS]:
            salary.balance += instance.amount
        elif instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance -= instance.amount

        # обновляем дату последней выплаты, если это зарплата
        if instance.payment_type == SalaryPayment.PaymentType.SALARY:
            salary.last_payment = instance.date

        salary.save()


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
