from dateutil.relativedelta import relativedelta
from django.utils import timezone
from .models import FinancialTransactions, Finance


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


def update_finance_record(date):
    """Обновляет или создает запись в Finance для указанной даты"""
    transactions = FinancialTransactions.objects.filter(date=date)
    income = sum(t.amount for t in transactions if t.transaction_type == FinancialTransactions.TransactionsType.PLUS)
    consumption = sum(
        t.amount for t in transactions if t.transaction_type == FinancialTransactions.TransactionsType.MINUS)
    # card_profit считаем ТОЛЬКО по PLUS-транзакциям (доходным операциям),
    # чтобы расходные MINUS-операции с card_amount не искажали безналичную прибыль.
    card_profit = sum(
        t.card_amount for t in transactions
        if t.transaction_type == FinancialTransactions.TransactionsType.PLUS
    )

    finance, created = Finance.objects.get_or_create(date=date)
    finance.income = income
    finance.consumption = consumption
    finance.profit = income - consumption
    finance.card_profit = card_profit
    finance.save()
