"""
Сервис для страницы «Финансы» (/dashboard/finance/).

Содержит функции для таблицы Finance по дням и детализации транзакций.
"""
import logging
from dataclasses import dataclass, field

from django.core.paginator import Paginator, Page
from django.db.models import Sum

from apps.accounting.models import Finance, FinancialTransactions
from apps.dashboard.services.filters import Period

logger = logging.getLogger(__name__)


@dataclass
class FinanceDayRow:
    """Строка таблицы Finance по дням."""
    date: str
    income: int = 0
    consumption: int = 0
    profit: int = 0
    card_profit: int = 0


@dataclass
class FinanceTotals:
    """Итоги по выбранному периоду."""
    income: int = 0
    consumption: int = 0
    profit: int = 0
    card_profit: int = 0


def get_finance_by_day(period: Period) -> (list, FinanceTotals):
    """Таблица Finance по дням + итоги за период."""
    totals = FinanceTotals()

    if period.is_empty:
        return [], totals

    qs = Finance.objects.filter(
        date__gte=period.date_from,
        date__lte=period.date_to,
    ).order_by('-date')

    rows = []
    for f in qs:
        rows.append(FinanceDayRow(
            date=f.date.isoformat(),
            income=f.income or 0,
            consumption=f.consumption or 0,
            profit=f.profit or 0,
            card_profit=f.card_profit or 0,
        ))

    agg = qs.aggregate(
        total_income=Sum('income'),
        total_consumption=Sum('consumption'),
        total_profit=Sum('profit'),
        total_card=Sum('card_profit'),
    )
    totals.income = agg['total_income'] or 0
    totals.consumption = agg['total_consumption'] or 0
    totals.profit = agg['total_profit'] or 0
    totals.card_profit = agg['total_card'] or 0

    return rows, totals


@dataclass
class TransactionRow:
    """Строка детализации операций."""
    id: int
    date: str
    txn_type: str
    type_display: str
    amount: int = 0
    card_amount: int = 0
    source: str = '—'
    description: str = '—'


def get_transactions(period: Period, filters: dict, page_num: int = 1, per_page: int = 25) -> Page:
    """Детализация операций с фильтрами и пагинацией."""
    if period.is_empty:
        return Paginator([], per_page).get_page(1)

    qs = FinancialTransactions.objects.filter(
        date__gte=period.date_from,
        date__lte=period.date_to,
    )

    txn_type = filters.get('type', '')
    if txn_type:
        qs = qs.filter(transaction_type=txn_type)

    source = filters.get('source', '')
    if source:
        qs = qs.filter(source__icontains=source)

    payment = filters.get('payment', '')
    if payment == 'card':
        qs = qs.filter(card_amount__gt=0)
    elif payment == 'cash':
        qs = qs.filter(amount__gt=0).exclude(card_amount__gt=0)

    qs = qs.order_by('-date', '-id')

    paginator = Paginator(qs, per_page)
    page = paginator.get_page(page_num)

    # Преобразуем объекты страницы в строки
    items = []
    for t in page.object_list:
        items.append(TransactionRow(
            id=t.id,
            date=t.date.isoformat(),
            txn_type=t.transaction_type,
            type_display=t.get_transaction_type_display(),
            amount=t.amount or 0,
            card_amount=t.card_amount or 0,
            source=t.source or '—',
            description=t.description or '—',
        ))
    page.object_list = items
    return page