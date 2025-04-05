from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Installment, PaymentsInstallment, Salary, SalaryPayment

@receiver(post_save, sender=PaymentsInstallment)
def update_installment_on_payment(sender, instance, **kwargs):
    """Обновление рассрочки при добавлении платежа."""
    installment = instance.installment
    installment.make_payment(instance.amount)  # Обновляем сумму и статус рассрочки

@receiver(post_save, sender=SalaryPayment)
def update_salary_on_payment(sender, instance, **kwargs):
    """Обновление баланса и даты последней выплаты при добавлении платежа."""
    salary = instance.salary

    # Обновляем баланс в зависимости от типа платежа
    if instance.payment_type in [SalaryPayment.PaymentType.SALARY, SalaryPayment.PaymentType.BONUS]:
        salary.balance += instance.amount
    elif instance.payment_type == SalaryPayment.PaymentType.FINE:
        salary.balance -= instance.amount

    # Обновляем дату последней выплаты, если это зарплата
    if instance.payment_type == SalaryPayment.PaymentType.SALARY:
        salary.last_payment = instance.date

    salary.save()