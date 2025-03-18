from random import choices

from django.db import models
from django.core.exceptions import ValidationError
from apps.clients.models import Client
from apps.products.models import Product
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta

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
    """Таблица контрактов, сделок"""
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


class Installment(models.Model):
    """Таблица учета Рассрочки по клиентам"""
    class InstallmentStatus(models.TextChoices):
        ACTIVE = 'AC', 'Активный'
        OVERDUE = 'OV', 'Просроченый'
        CLOSED = 'CL', 'Погашенный'

    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Продукт')
    total_amount = models.IntegerField(verbose_name='Сумма рассрочки')
    paid_amount = models.IntegerField(verbose_name='Оплаченно')
    due_date = models.DateField(verbose_name='Дата след платежа')
    status = models.CharField(choices=InstallmentStatus.choices, verbose_name="Статус рассрочки")
    created_at = models.DateField(auto_now_add=True ,verbose_name='Дата создания')
    updated_at = models.DateField(auto_now=True ,verbose_name='Дата обновления')

    def __str__(self):
        return self.client.name

    def make_payment(self, amount):
        """Внесение платежа и обновление даты слудующего платежа"""
        self.paid_amount += amount

        # Если вся сумма выплачена кроем рассрочку
        if self.paid_amount >= self.total_amount:
            self.status = 'CL'
        else:
            # Сдвигаем due_date на след месяц
            self.due_date = self.due_date + relativedelta(months=1)
        self.save()

    def check_status(self):
        """Проверка статуса рассрочки"""
        if self.paid_amount < self.total_amount and self.due_date < now().date():
            self.status = 'OV' # Если платеж просрочен
        elif self.paid_amount >= self.total_amount:
            self.status = 'CL' # Если все погашено
        else:
            self.status = 'AC'
        self.save()

class PaymentsInstallment(models.Model):
    """Таблица платежей по рассрочкам"""
    installment = models.ForeignKey(Installment, on_delete=models.DO_NOTHING, related_name='Платежи')
    amount = models.IntegerField(verbose_name='Сумма взноса')
    payment_date = models.DateField(verbose_name='Дата взноса')
    created_at = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """При сейве платежа обнавляем данные по рассроку"""
        super().save(*args, **kwargs)
        self.installment.make_payment(self.amount) # Автообнова суммы




