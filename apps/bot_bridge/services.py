"""
Сервисные функции для автоматического учёта событий WERP (apps/bot_bridge/services.py).

Здесь — логика, которая вызывается из бизнес-потоков (закрытие смены) и пишет
сопутствующие записи (расходы в финансы) с гарантией идемпотентности.
"""
import logging

from apps.accounting.models import FinancialTransactions
from apps.accounting.utils import update_finance_record

logger = logging.getLogger(__name__)

# Маркер в source финансовой транзакции расхода, чтобы отличать авто-расход смены.
EXPENSE_SOURCE_PREFIX = "Расход смены #"


def _expense_source(shift_id: int, reason: str) -> str:
    """Уникальный source для финансовой транзакции расхода.

    Содержит id смены + причину, чтобы одинаковые причины в одной смене
    не пересекались и повторная запись была идемпотентной.
    """
    return f"{EXPENSE_SOURCE_PREFIX}{shift_id} — {reason}"


def register_shift_expenses(shift, date=None) -> int:
    """Записать все расходы закрытой смены в финансовые транзакции как РАСХОД.

    Для каждой строки ShiftExpense создаётся FinancialTransactions с типом MINUS,
    причиной в description и source-маркером. Повторный вызов не дублирует записи
    (существующие по source пропускаются).

    Возвращает число созданных транзакций.
    """
    from apps.logistics.models import CourierShift

    if shift.status != CourierShift.Status.CLOSED:
        return 0

    date = date or (shift.closed_at.date() if shift.closed_at else shift.date)
    created = 0

    for expense in shift.expenses.all():
        source = _expense_source(shift.id, expense.reason)
        exists = FinancialTransactions.objects.filter(
            source=source,
            transaction_type=FinancialTransactions.TransactionsType.MINUS,
            date=date,
            amount=expense.amount,
        ).exists()
        # Повторная запись той же причины+суммы+даты — считается уже зафиксированной.
        if exists:
            continue
        FinancialTransactions.objects.create(
            date=date,
            transaction_type=FinancialTransactions.TransactionsType.MINUS,
            amount=expense.amount,
            card_amount=0,
            description=expense.reason,
            source=source,
        )
        created += 1

    if created:
        update_finance_record(date)

    return created