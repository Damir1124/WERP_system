from django.db import models
from django.core.exceptions import ValidationError

from apps.clients.models import Client


def contract_upload_path(instance, filename):
    """Генерация пути для загрузки файлов контрактов"""
    return f'contracts/{instance.id}/{filename}'


def validate_contract_file(value):
    """Валидация форматов файлов"""
    allowed_types = [
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'image/jpeg', 'image/png'
    ]
    if hasattr(value, 'content_type') and value.content_type not in  allowed_types:
        raise ValidationError('Рарешены только PDF, Word, Exel, JPEG, PNG')


class Contract(models.Model):
    class ContractType(models.TextChoices):
        BUY = 'BY', 'В минус'
        SELL = 'SL', 'В плюс'

    description = models.CharField(max_length=255, verbose_name='Описание')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, verbose_name='Клиент', blank=True, null=True)
    date = models.DateField(verbose_name='Дата заключения')
    file = models.FileField(upload_to=contract_upload_path, verbose_name='Документ',
                            validators=[validate_contract_file], null=True, blank=True)
    contract_type = models.CharField(choices=ContractType.choices, verbose_name='Тип контрака')
    amount = models.IntegerField(verbose_name='Сумма')
    note = models.CharField(verbose_name='Примечание', max_length=255)

