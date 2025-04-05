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
    if hasattr(value, 'content_type') and value.content_type not in allowed_types:
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



class SubjectContract(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    note = models.CharField(max_length=255, verbose_name='Описание предмета')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, verbose_name="Товар", blank=True, null=True)
    quantity = models.IntegerField(verbose_name="Количество")

    def __str__(self):
        return f'C Контракта: {self.contract.note}'


class Installment(models.Model):
    """Таблица учета Рассрочки по клиентам"""

    class InstallmentStatus(models.TextChoices):
        ACTIVE = 'AC', 'Активный'
        OVERDUE = 'OV', 'Просроченый'
        CLOSED = 'CL', 'Погашенный'

    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, verbose_name='Продукт')
    total_amount = models.IntegerField(verbose_name='Сумма рассрочки')
    paid_amount = models.IntegerField(verbose_name='Оплаченно', null=True, blank=True)
    due_date = models.DateField(verbose_name='Дата след платежа',  null=True, blank=True)
    status = models.CharField(choices=InstallmentStatus.choices, verbose_name="Статус рассрочки")
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return self.client.name

    def make_payment(self, amount):
        """Обновляет общую сумму оплаченных средств и статус рассрочки."""
        # Обновляем общую сумму оплаченных средств
        self.paid_amount = (self.paid_amount or 0) + amount

        # Обновляем статус рассрочки
        if self.paid_amount >= self.total_amount:
            self.status = Installment.InstallmentStatus.CLOSED
        elif self.due_date and self.due_date < now().date():
            self.status = Installment.InstallmentStatus.OVERDUE
        else:
            self.status = Installment.InstallmentStatus.ACTIVE

        self.save()

    def check_status(self):
        """Обновляет статус рассрочки в зависимости от оплаченной суммы."""
        if self.paid_amount >= self.total_amount:
            self.status = Installment.InstallmentStatus.CLOSED
        elif self.due_date and self.due_date < now().date():
            self.status = Installment.InstallmentStatus.OVERDUE
        else:
            self.status = Installment.InstallmentStatus.ACTIVE


class PaymentsInstallment(models.Model):
    """Таблица платежей по рассрочкам"""
    installment = models.ForeignKey(Installment, on_delete=models.CASCADE)
    amount = models.IntegerField(verbose_name='Сумма взноса')
    payment_date = models.DateField(verbose_name='Дата взноса')
    created_at = models.DateField(auto_now_add=True)


class Salary(models.Model):
    """Учет выплат сотрудникам"""

    class PaymentType(models.TextChoices):
        SALARY = 'SA', 'Зарплата'
        FINE = "FI", "Штраф"
        BONUS = "BO", "Бонус"

    worker = models.ForeignKey('workers.Worker',
                               on_delete=models.DO_NOTHING,
                               related_name='workewrs',
                               verbose_name='Работник')
    last_payment = models.DateField(verbose_name='Дата последней выплаты', null=True, blank=True)
    balance = models.IntegerField(verbose_name='Баланс', null=False, blank=True, default=0)

    def __str__(self):
        return self.worker.full_name


class SalaryPayment(models.Model):
    """Лог платежей"""

    class PaymentType(models.TextChoices):
        SALARY = 'SA', 'Зарплата'
        FINE = "FI", "Штраф"
        BONUS = "BO", "Бонус"

    salary = models.ForeignKey(Salary,
                               on_delete=models.CASCADE,
                               related_name='payments'
                              ,verbose_name="Зарплата рабоника")
    note = models.CharField(max_length=120, verbose_name='Примечание', null=True, blank=True)
    amount = models.IntegerField(verbose_name='Сумма')
    payment_type = models.CharField(choices=PaymentType.choices, verbose_name='Тип платежа')
    date = models.DateField(verbose_name='Дата')


class FinancialTransactions(models.Model):
    """Лог движения денежных средств"""

    class TransactionsType(models.TextChoices):
        PLUS = 'PL', 'Доход'
        MINUS = 'MI', 'Расход'

    date = models.DateField(verbose_name="Дата операции")
    transaction_type = models.CharField(choices=TransactionsType.choices, verbose_name='Тип трансакции')
    amount = models.CharField(verbose_name='Сумма')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Примечание')
    related_object = models.CharField(max_length=255, verbose_name="Источник операции")

    pass

class Finance(models.Model):
    income = models.IntegerField(verbose_name='Доход')
    consumption = models.IntegerField(verbose_name="Расход")
    profit = models.IntegerField(verbose_name="Расход")
    date = models.DateField(verbose_name='Дата сводки')

    pass


