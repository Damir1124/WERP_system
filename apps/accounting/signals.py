from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Installment, PaymentsInstallment, Salary, SalaryPayment
from . import utils


@receiver(pre_save, sender=PaymentsInstallment)
def calculate_installment_payment(sender, instance, **kwargs):
    """Пересчет суммы и статуса рассрочки перед сохранением платежа."""
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
    """Обновление рассрочки при добавлении или изменении платежа."""
    if created:
        installment = instance.installment
        installment.make_payment(instance.amount)  # Обновляем сумму и статус рассрочки
        utils.update_due_date(installment) # Обновление даты след. платежа

#### 2. Salary и SalaryPayment

@receiver(pre_save, sender=SalaryPayment)
def calculate_salary_payment(sender, instance, **kwargs):
    """Пересчет баланса и даты последней выплаты перед сохранением платежа."""
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

@receiver(post_save, sender=SalaryPayment)
def update_salary_on_payment(sender, instance, created, **kwargs):
    """Обновление баланса и даты последней выплаты при добавлении платежа."""
    if created:
        salary = instance.salary

        utils.reset_balance_if_expired(salary)  # проверяем и обнуляем, если нужно

        # Обновляем баланс в зависимости от типа платежа
        if instance.payment_type in [SalaryPayment.PaymentType.SALARY, SalaryPayment.PaymentType.BONUS]:
            salary.balance += instance.amount
        elif instance.payment_type == SalaryPayment.PaymentType.FINE:
            salary.balance -= instance.amount

        # Обновляем дату последней выплаты, если это зарплата
        if instance.payment_type == SalaryPayment.PaymentType.SALARY:
            salary.last_payment = instance.date

        salary.save()
