"""
Celery-задачи для модуля Dashboard.

Периодические задачи (Celery Beat):
- recalc_finance_for_date_task — пересчёт Finance за вчера (страховка от пропущенных сигналов)
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def recalc_finance_for_date_task(date_str: str = None):
    """Пересчёт дневной сводки Finance для указанной даты.

    date_str — дата в формате ГГГГ-ММ-ДД. По умолчанию — вчера.
    Страховка: если какой-то сигнал не сработал, сводка всё равно будет корректной.
    """
    from apps.accounting.utils import update_finance_record

    if date_str:
        from datetime import date
        target_date = date.fromisoformat(date_str)
    else:
        target_date = timezone.now().date() - timedelta(days=1)

    update_finance_record(target_date)
    logger.info("Пересчитана сводка Finance за %s", target_date)
    return str(target_date)