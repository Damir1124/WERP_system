from dateutil.relativedelta import relativedelta
from django.utils import timezone

def update_due_date(installment):
    """Обновление даты следующего платежа по последнему взносу"""
    last_payment = installment.paymentsinstallment_set.order_by('-payment_date').first()
    if last_payment:
        installment.due_date = last_payment.payment_date + relativedelta(months=1)
        installment.save()

def reset_balance_if_expired(salary):
    """Обнуляет баланс если с последней зарплаты прошёл месяц"""
    if salary.last_payment is None:
        return

    now = timezone.now().date()
    delta = now - salary.last_payment

    if delta.days >= 30:
        salary.balance = 0
        salary.save()