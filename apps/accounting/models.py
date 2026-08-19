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
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', blank=True, null=True)
    date = models.DateField(verbose_name='Дата заключения')
    file = models.FileField(upload_to=contract_upload_path, verbose_name='Документ',
                            validators=[validate_contract_file], null=True, blank=True)
    contract_type = models.CharField(choices=ContractType.choices, verbose_name='Тип контрака', max_length=2)
    amount = models.IntegerField(verbose_name='Сумма')
    note = models.CharField(verbose_name='Примечание', max_length=255)

    def __str__(self):
        return f"Контракт от {self.date}: {self.description}; Сумма: {self.amount}"



class SubjectContract(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    note = models.CharField(max_length=255, verbose_name='Описание предмета')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар", blank=True, null=True)
    quantity = models.IntegerField(verbose_name="Количество")

    def __str__(self):
        return f'C Контракта: {self.contract.note}'


class Installment(models.Model):
    """Таблица учета Рассрочки по клиентам"""

    class InstallmentStatus(models.TextChoices):
        ACTIVE = 'AC', 'Активный'
        OVERDUE = 'OV', 'Просроченый'
        CLOSED = 'CL', 'Погашенный'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клиент")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    amount = models.IntegerField(verbose_name='Сумма рассрочки', null=True, blank=True, default=0)
    paid_amount = models.IntegerField(verbose_name='Оплаченно', null=True, blank=True)
    due_date = models.DateField(verbose_name='Дата след платежа',  null=True, blank=True)
    status = models.CharField(choices=InstallmentStatus.choices, verbose_name="Статус рассрочки", max_length=2)
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return self.client.name

    def make_payment(self, amount):
        """Обновляет общую сумму оплаченных средств и статус рассрочки"""
        # Обновляем общую сумму оплаченных средств
        self.paid_amount = (self.paid_amount or 0) + amount

        # Обновляем статус рассрочки
        if self.paid_amount >= self.amount:
            self.status = Installment.InstallmentStatus.CLOSED
        elif self.due_date and self.due_date < now().date():
            self.status = Installment.InstallmentStatus.OVERDUE
        else:
            self.status = Installment.InstallmentStatus.ACTIVE

        self.save()

    def check_status(self):
        """Обновляет статус рассрочки в зависимости от оплаченной суммы"""
        if self.paid_amount >= self.amount:
            self.status = Installment.InstallmentStatus.CLOSED
        elif self.due_date and self.due_date < now().date():
            self.status = Installment.InstallmentStatus.OVERDUE
        else:
            self.status = Installment.InstallmentStatus.ACTIVE


class PaymentsInstallment(models.Model):
    """Таблица платежей по рассрочкам"""
    installment = models.ForeignKey(Installment, on_delete=models.CASCADE)
    amount = models.IntegerField(verbose_name='Сумма взноса', null=True, blank=True, default=0)
    payment_date = models.DateField(verbose_name='Дата взноса')
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Рассрочка клиента: {self.installment.client.name} на {self.installment.product.name}; Сумма: {self.amount}"


class Salary(models.Model):
    """Учет выплат сотрудникам"""

    class PaymentType(models.TextChoices):
        SALARY = 'SA', 'Зарплата'
        FINE = "FI", "Штраф"
        BONUS = "BO", "Бонус"

    worker = models.ForeignKey('workers.Worker',
                               on_delete=models.CASCADE,
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
                               on_delete=models.CASCADE,)
    note = models.CharField(max_length=120, verbose_name='Примечание', null=True, blank=True)
    amount = models.IntegerField(verbose_name='Сумма', null=True, blank=True, default=0)
    payment_type = models.CharField(choices=PaymentType.choices, verbose_name='Тип платежа', max_length=2)
    date = models.DateField(verbose_name='Дата')

    def __str__(self):
        return f'{self.payment_type[1]}; Сотрудник: {self.salary.worker.full_name}; Сумма: {self.amount}'


class FinancialTransactions(models.Model):
    """Лог движения денежных средств"""

    class TransactionsType(models.TextChoices):
        PLUS = 'PL', 'Доход'
        MINUS = 'MI', 'Расход'

    date = models.DateField(verbose_name="Дата операции")
    transaction_type = models.CharField(choices=TransactionsType.choices, verbose_name='Тип трансакции', max_length=2)
    amount = models.IntegerField(verbose_name=' Общая сумма', null=True, blank=True, default=0)
    card_amount = models.IntegerField(verbose_name='Сумма картой', null=True, blank=True, default=0)
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Примечание')
    source = models.CharField(verbose_name="Источник операции", max_length=100)

    pass

class Finance(models.Model):
    income = models.IntegerField(verbose_name='Доход', null=True, blank=True, default=0)
    consumption = models.IntegerField(verbose_name="Расход", null=True, blank=True, default=0)
    profit = models.IntegerField(verbose_name="Прибыль", null=True, blank=True, default=0)
    card_profit = models.IntegerField(verbose_name="Прибыль на карту", null=True, blank=True, default=0)
    date = models.DateField(verbose_name='Дата сводки')

    pass


class HistoricalStats(models.Model):
    """
    Единственная запись стартовых исторических показателей «до запуска WERP».

    Хранит два итога из старой системы:
    - historical_orders_created_total — общее количество созданных заказов;
    - historical_water_sold_total — общее количество проданной основной воды.

    Эти значения прибавляются ТОЛЬКО к показателям «За всё время»
    и НЕ влияют на today / week / month / custom / смены / рейсы / кассу / финансы / склад.

    Singleton: в системе может быть только одна активная запись.
    """
    historical_orders_created_total = models.PositiveIntegerField(
        default=0,
        verbose_name='Заказов создано (история)',
        help_text='Общее количество заказов, созданных в старой системе до запуска WERP.'
    )
    historical_water_sold_total = models.PositiveIntegerField(
        default=0,
        verbose_name='Продано основной воды (история)',
        help_text='Общее количество проданной основной воды (в штуках) в старой системе до запуска WERP.'
    )
    werp_start_date = models.DateField(
        verbose_name='Дата запуска WERP',
        help_text='Дата, с которой начат учёт в WERP. Используется для подписи «Включая данные до запуска WERP».',
        null=True, blank=True,
    )
    source = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name='Источник / комментарий',
        help_text='Откуда взяты исторические данные (например, «Перенос из 1С, акт №...»)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменено')
    created_by = models.ForeignKey(
        'workers.Worker', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Кто создал', related_name='historical_stats_created'
    )
    updated_by = models.ForeignKey(
        'workers.Worker', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Кто изменил', related_name='historical_stats_updated'
    )

    class Meta:
        verbose_name = 'Историческая база (до WERP)'
        verbose_name_plural = 'Историческая база (до WERP)'
        constraints = [
            models.CheckConstraint(
                check=models.Q(historical_orders_created_total__gte=0),
                name='historical_orders_created_total_gte_0',
            ),
            models.CheckConstraint(
                check=models.Q(historical_water_sold_total__gte=0),
                name='historical_water_sold_total_gte_0',
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.pk is None and HistoricalStats.objects.exists():
            raise ValidationError(
                'Запись исторической базы уже существует. '
                'Нельзя создать вторую. Отредактируйте существующую.'
            )

    def save(self, *args, **kwargs):
        if self.pk is None and HistoricalStats.objects.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError(
                'Запись исторической базы уже существует. '
                'Нельзя создать вторую. Отредактируйте существующую.'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'Историческая база: заказов {self.historical_orders_created_total}, '
            f'воды {self.historical_water_sold_total}'
            f'{" с " + self.werp_start_date.isoformat() if self.werp_start_date else ""}'
        )
