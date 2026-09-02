"""
Celery-задачи для модуля Accounting (финансы).

Периодические задачи (Celery Beat):
- send_installment_reminders_task — напоминания о взносах по рассрочкам (ежедневно 09:00)
- reset_expired_salaries_task     — сброс просроченных балансов зарплат (ежедневно 00:30)
- accrue_salaries_task            — начисление окладов (1-го числа каждого месяца)
"""
import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_installment_reminders_task():
    """Напоминания владельцу о взносах по рассрочкам (due_date = сегодня).

    Заменяет management-команду send_installment_reminders.
    """
    from apps.accounting.models import Installment
    from apps.bot_bridge.notify import notify_owner_installment_reminder

    today = timezone.now().date()

    installments = Installment.objects.filter(
        due_date=today,
        status=Installment.InstallmentStatus.ACTIVE,
    )

    # Оставляем только те, где остаток долга > 0
    installments = [
        inst for inst in installments
        if (inst.amount or 0) - (inst.paid_amount or 0) > 0
    ]

    sent_count = 0
    for installment in installments:
        try:
            if notify_owner_installment_reminder(installment):
                sent_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка напоминания по рассрочке %s: %s", installment.id, exc)

    logger.info("Напоминания отправлены по %s из %s рассрочек", sent_count, len(installments))
    return sent_count


@shared_task
def reset_expired_salaries_task():
    """Сброс балансов зарплат, если последняя выплата была в прошлом месяце.

    Заменяет ручной вызов reset_balance_if_expired для всех зарплат.
    """
    from apps.accounting.models import Salary
    from apps.accounting.utils import reset_balance_if_expired

    reset_count = 0
    for salary in Salary.objects.all():
        try:
            if salary.last_payment is not None:
                reset_balance_if_expired(salary)
                reset_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка сброса баланса зарплаты %s: %s", salary.id, exc)

    logger.info("Проверено %s зарплат на сброс баланса", reset_count)
    return reset_count


@shared_task
def accrue_salaries_task(month_str: str = None):
    """Начисление фиксированного оклада всем сотрудникам за месяц.

    month_str — первый день расчётного месяца в формате ГГГГ-ММ-ДД.
    По умолчанию — текущий месяц.
    """
    from apps.accounting.utils import accrue_salary_for_period
    from apps.workers.models import Worker

    if month_str:
        month = date.fromisoformat(month_str).replace(day=1)
    else:
        today = date.today()
        month = today.replace(day=1)

    workers = Worker.objects.all()
    created_count = 0
    updated_count = 0

    for worker in workers:
        try:
            period = accrue_salary_for_period(worker, month)
            if period.salary_amount > 0:
                if period.pk and period.status == period.PeriodStatus.OPEN:
                    updated_count += 1
                else:
                    created_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка начисления зарплаты сотруднику %s: %s", worker.id, exc)

    logger.info(
        "Начисление за %s завершено: создано %s, обновлено %s (всего %s сотрудников)",
        month.strftime("%B %Y"), created_count, updated_count, workers.count(),
    )
    return {'created': created_count, 'updated': updated_count}