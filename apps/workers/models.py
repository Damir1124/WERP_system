from django.db import models
from datetime import date
from apps.warehouse.models import Garage

class WorkerType(models.TextChoices):
    PACKER = "packer", "Упаковщик"
    COURIER = "courier", "Курьер"
    OTHER = "other", "Прочие"

class Worker(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    worker_type = models.CharField(
        max_length=10,
        choices=WorkerType.choices,
        verbose_name="Тип сотрудника"
    )
    date_for_payed = models.DateField(blank=True, null=False, verbose_name='Начисление зарплаты', default=date.today)
    note = models.TextField(blank=True, verbose_name="Примечание")

    created_at = models.DateField(auto_now_add=True, verbose_name='Созданно')
    updated_at = models.DateField(auto_now=True, verbose_name='Обнавлено')

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return self.full_name

