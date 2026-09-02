from datetime import date

from django.core.management.base import BaseCommand

from apps.accounting.utils import accrue_salary_for_period
from apps.workers.models import Worker


class Command(BaseCommand):
    """Авто-начисление оклада сотрудникам за указанный месяц.

    Запуск в начале каждого месяца (например, по cron 1-го числа):
        python manage.py accrue_salaries
        python manage.py accrue_salaries --month 2026-08-01
    """

    help = 'Начисляет фиксированный оклад всем сотрудникам за месяц.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            default=None,
            help='Первый день расчётного месяца в формате ГГГГ-ММ-ДД. По умолчанию — текущий месяц.',
        )

    def handle(self, *args, **options):
        month_str = options.get('month')
        if month_str:
            month = date.fromisoformat(month_str).replace(day=1)
        else:
            today = date.today()
            month = today.replace(day=1)

        workers = Worker.objects.all()
        created_count = 0
        updated_count = 0

        for worker in workers:
            period = accrue_salary_for_period(worker, month)
            if period.salary_amount > 0:
                if period.pk and period.status == period.PeriodStatus.OPEN:
                    updated_count += 1
                else:
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Начисление за {month.strftime("%B %Y")} завершено: '
                f'обработано {workers.count()} сотрудников.'
            )
        )