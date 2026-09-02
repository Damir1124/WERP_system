from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounting.models import Installment
from apps.bot_bridge.notify import notify_owner_installment_reminder


class Command(BaseCommand):
    """Ежедневная отправка напоминаний владельцу о взносах по рассрочкам.

    Находит все активные рассрочки, у которых due_date == сегодня и остаток долга > 0,
    и отправляет напоминание всем владельцам (worker_type=OWNER) с tg_id.

    Запуск (например, по cron каждый день утром):
        python manage.py send_installment_reminders
    """

    help = 'Отправляет напоминания владельцу о взносах по рассрочкам (due_date = сегодня)'

    def handle(self, *args, **options):
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
            if notify_owner_installment_reminder(installment):
                sent_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Напоминания отправлены по {sent_count} из {len(installments)} рассрочек'
            )
        )