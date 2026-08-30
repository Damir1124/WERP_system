from django.db import models
from datetime import date
from apps.warehouse.models import Garage


class Worker(models.Model):
    class WorkerType(models.TextChoices):
        PACKER = "packer", "Упаковщик"
        COURIER = "courier", "Курьер"
        OPERATOR = "operator", "Оператор"
        OWNER = "owner", "Владелец"
        OTHER = "other", "Прочие"

    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон',
        help_text='Номер телефона сотрудника'
    )
    worker_type = models.CharField(
        max_length=10,
        choices=WorkerType.choices,
        verbose_name="Тип сотрудника"
    )
    date_for_payed = models.DateField(blank=True, null=False, verbose_name='Дата начисления зарплаты', default=date.today)
    salary_amount = models.IntegerField(
        default=0,
        verbose_name='Оклад (сум)',
        help_text='Фиксированный месячный оклад сотрудника. Используется при авто-начислении зарплаты.'
    )
    note = models.TextField(blank=True, verbose_name="Примечание")
    tg_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name='Telegram ID',
        help_text='ID пользователя в Telegram для авторизации в боте'
    )
    is_admin = models.BooleanField(
        default=False,
        verbose_name='Администратор бота',
        help_text='Даёт доступ к командам администратора в Telegram-боте'
    )

    created_at = models.DateField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return self.full_name
