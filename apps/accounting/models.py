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
    contract_type = models.CharField(choices=ContractType.choices, verbose_name='Тип контракта', max_length=2)
    amount = models.IntegerField(verbose_name='Сумма')
    note = models.CharField(verbose_name='Примечание', max_length=255)

    class Meta:
        verbose_name = 'Контракт'
        verbose_name_plural = 'Контракты'
        ordering = ['-date']

    def __str__(self):
        return f"Контракт от {self.date}: {self.description}; Сумма: {self.amount}"



class SubjectContract(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, verbose_name='Контракт')
    note = models.CharField(max_length=255, verbose_name='Описание предмета')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар", blank=True, null=True)
    warehouse_product = models.ForeignKey(
        'warehouse.WarehouseProduct',
        on_delete=models.CASCADE,
        verbose_name="Складской продукт (комплектующие)",
        blank=True,
        null=True,
        help_text="Для закупки комплектующих (пакеты, тара, крышки). Либо товар ассортимента, либо складской продукт."
    )
    quantity = models.IntegerField(verbose_name="Количество")

    class Meta:
        verbose_name = 'Предмет контракта'
        verbose_name_plural = 'Предметы контракта'

    def __str__(self):
        return f'C Контракта: {self.contract.note}'


class Installment(models.Model):
    """Таблица учета Рассрочки по клиентам (шапка)"""

    class InstallmentStatus(models.TextChoices):
        ACTIVE = 'AC', 'Активный'
        OVERDUE = 'OV', 'Просроченый'
        CLOSED = 'CL', 'Погашенный'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клиент")
    order = models.OneToOneField(
        'logistics.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installment',
        verbose_name='Заказ',
        help_text='Если рассрочка оформлена по заказу — укажите заказ. Позиции подтянутся автоматически.'
    )
    issued_by = models.ForeignKey(
        'workers.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_installments',
        verbose_name='Кто оформил',
        help_text='Сотрудник/курьер, который оформил рассрочку. Для заказа подставляется автоматически.'
    )
    amount = models.IntegerField(verbose_name='Сумма рассрочки', null=True, blank=True, default=0)
    paid_amount = models.IntegerField(verbose_name='Оплаченно', null=True, blank=True, default=0)
    due_date = models.DateField(verbose_name='Дата след платежа',  null=True, blank=True)
    status = models.CharField(choices=InstallmentStatus.choices, verbose_name="Статус рассрочки", max_length=2)
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Рассрочка'
        verbose_name_plural = 'Рассрочки'
        ordering = ['-created_at']

    def __str__(self):
        return f'Рассрочка клиента {self.client.name} на {self.amount} сум'

    @property
    def debt(self):
        """Остаток долга по рассрочке"""
        return (self.amount or 0) - (self.paid_amount or 0)

    def recalc_amount(self):
        """Пересчитывает общую сумму рассрочки из позиций.

        Использует queryset.update() — НЕ вызывает сигналы,
        чтобы не спровоцировать рекурсию (post_save → recalc_amount → ...).
        """
        total = sum(item.subtotal for item in self.items.all())
        Installment.objects.filter(pk=self.pk).update(amount=total)
        self.amount = total

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


class InstallmentItem(models.Model):
    """Позиция рассрочки (товар + количество + цена)"""

    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Рассрочка'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    quantity = models.IntegerField(verbose_name='Количество', default=1)
    price_per_unit = models.IntegerField(verbose_name='Цена за единицу', null=True, blank=True)
    subtotal = models.IntegerField(verbose_name='Сумма позиции', null=True, blank=True, default=0)

    class Meta:
        verbose_name = 'Позиция рассрочки'
        verbose_name_plural = 'Позиции рассрочки'

    def __str__(self):
        return f'{self.product.name} × {self.quantity}'

    def save(self, *args, **kwargs):
        """Авто-расчёт цены и суммы позиции"""
        if self.price_per_unit is None:
            self.price_per_unit = self.product.price
        self.subtotal = (self.price_per_unit or 0) * (self.quantity or 0)
        super().save(*args, **kwargs)
        # Пересчитываем общую сумму рассрочки
        self.installment.recalc_amount()


class PaymentsInstallment(models.Model):
    """Таблица платежей по рассрочкам"""
    installment = models.ForeignKey(Installment, on_delete=models.CASCADE, verbose_name='Рассрочка')
    amount = models.IntegerField(verbose_name='Сумма взноса', null=True, blank=True, default=0)
    payment_date = models.DateField(verbose_name='Дата взноса')
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Платёж по рассрочке'
        verbose_name_plural = 'Платежи по рассрочкам'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Платёж по рассрочке клиента {self.installment.client.name}; Сумма: {self.amount}"


class Salary(models.Model):
    """Учет выплат сотрудникам"""

    worker = models.ForeignKey('workers.Worker',
                               on_delete=models.CASCADE,
                               related_name='salaries',
                               verbose_name='Работник')
    last_payment = models.DateField(verbose_name='Дата последней выплаты', null=True, blank=True)
    balance = models.IntegerField(verbose_name='Баланс', null=False, blank=True, default=0)

    class Meta:
        verbose_name = 'Зарплата'
        verbose_name_plural = 'Зарплаты'

    def __str__(self):
        return self.worker.full_name


class SalaryPeriod(models.Model):
    """Зарплатный период (календарный месяц) сотрудника.

    Агрегирует все начисления и выплаты за один месяц, чтобы владелец
    не держал в голове: сколько выдан аванс, сколько осталось к выдаче,
    в какую дату зарплата.
    """

    class PeriodStatus(models.TextChoices):
        OPEN = 'OP', 'Открыт'
        PAID = 'PD', 'Выплачен'
        CLOSED = 'CL', 'Закрыт'

    worker = models.ForeignKey(
        'workers.Worker',
        on_delete=models.CASCADE,
        related_name='salary_periods',
        verbose_name='Работник'
    )
    month = models.DateField(
        verbose_name='Месяц',
        help_text='Первый день расчётного месяца (например, 2026-08-01).'
    )
    salary_amount = models.IntegerField(
        default=0,
        verbose_name='Оклад за месяц',
        help_text='Фиксированный оклад, начисленный за этот месяц.'
    )
    bonuses = models.IntegerField(default=0, verbose_name='Бонусы')
    fines = models.IntegerField(default=0, verbose_name='Штрафы')
    advances = models.IntegerField(default=0, verbose_name='Выдано авансов')
    paid_salary = models.IntegerField(default=0, verbose_name='Выплачено зарплаты')
    salary_date = models.DateField(
        verbose_name='Дата зарплаты',
        null=True, blank=True,
        help_text='Дата, когда должна быть выплачена зарплата за этот месяц.'
    )
    status = models.CharField(
        choices=PeriodStatus.choices,
        default=PeriodStatus.OPEN,
        max_length=2,
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Зарплатный период'
        verbose_name_plural = 'Зарплатные периоды'
        ordering = ['-month']
        constraints = [
            models.UniqueConstraint(
                fields=['worker', 'month'],
                name='unique_worker_month'
            ),
        ]

    def __str__(self):
        return f'{self.worker.full_name} — {self.month.strftime("%B %Y")}'

    @property
    def accrued(self):
        """Начислено за месяц: оклад + бонусы - штрафы."""
        return (self.salary_amount or 0) + (self.bonuses or 0) - (self.fines or 0)

    @property
    def paid_total(self):
        """Всего выплачено: авансы + зарплата."""
        return (self.advances or 0) + (self.paid_salary or 0)

    @property
    def remaining(self):
        """Остаток к выдаче: начислено - выплачено."""
        return self.accrued - self.paid_total

    def recalc(self):
        """Пересчитывает итоги периода из платежей.

        Использует queryset.update() - НЕ вызывает сигналы (защита от рекурсии).
        """
        payments = self.payments.all()
        bonuses = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.BONUS)
        fines = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.FINE)
        advances = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.ADVANCE)
        paid_salary = sum(p.amount for p in payments if p.payment_type == SalaryPayment.PaymentType.SALARY)

        SalaryPeriod.objects.filter(pk=self.pk).update(
            bonuses=bonuses,
            fines=fines,
            advances=advances,
            paid_salary=paid_salary,
        )
        self.bonuses, self.fines = bonuses, fines
        self.advances, self.paid_salary = advances, paid_salary

        # Если зарплата полностью выплачена - помечаем период выплаченным
        if self.remaining <= 0 and self.status != SalaryPeriod.PeriodStatus.CLOSED:
            SalaryPeriod.objects.filter(pk=self.pk).update(
                status=SalaryPeriod.PeriodStatus.PAID
            )
            self.status = SalaryPeriod.PeriodStatus.PAID


class SalaryPayment(models.Model):
    """Лог платежей по зарплате (аванс, зарплата, бонус, штраф)."""

    class PaymentType(models.TextChoices):
        SALARY = 'SA', 'Зарплата'
        ADVANCE = 'AD', 'Аванс'
        FINE = "FI", "Штраф"
        BONUS = "BO", "Бонус"

    salary = models.ForeignKey(Salary, on_delete=models.CASCADE, related_name='payments')
    period = models.ForeignKey(
        SalaryPeriod,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Период',
        null=True, blank=True,
        help_text='Зарплатный месяц, к которому относится платёж. Подставляется автоматически.'
    )
    note = models.CharField(max_length=120, verbose_name='Примечание', null=True, blank=True)
    amount = models.IntegerField(verbose_name='Сумма', null=True, blank=True, default=0)
    payment_type = models.CharField(choices=PaymentType.choices, verbose_name='Тип платежа', max_length=2)
    date = models.DateField(verbose_name='Дата')

    class Meta:
        verbose_name = 'Платёж по зарплате'
        verbose_name_plural = 'Платежи по зарплате'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_payment_type_display()}; Сотрудник: {self.salary.worker.full_name}; Сумма: {self.amount}'


class FinancialTransactions(models.Model):
    """Лог движения денежных средств"""

    class TransactionsType(models.TextChoices):
        PLUS = 'PL', 'Доход'
        MINUS = 'MI', 'Расход'

    date = models.DateField(verbose_name="Дата операции")
    transaction_type = models.CharField(choices=TransactionsType.choices, verbose_name='Тип транзакции', max_length=2)
    amount = models.IntegerField(verbose_name='Общая сумма', null=True, blank=True, default=0)
    card_amount = models.IntegerField(verbose_name='Сумма картой', null=True, blank=True, default=0)
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Примечание')
    source = models.CharField(verbose_name="Источник операции", max_length=100)

    class Meta:
        verbose_name = 'Финансовая транзакция'
        verbose_name_plural = 'Финансовые транзакции'
        ordering = ['-date']

class Finance(models.Model):
    income = models.IntegerField(verbose_name='Доход', null=True, blank=True, default=0)
    consumption = models.IntegerField(verbose_name="Расход", null=True, blank=True, default=0)
    profit = models.IntegerField(verbose_name="Прибыль", null=True, blank=True, default=0)
    card_profit = models.IntegerField(verbose_name="Прибыль на карту", null=True, blank=True, default=0)
    date = models.DateField(verbose_name='Дата сводки')

    class Meta:
        verbose_name = 'Дневная сводка'
        verbose_name_plural = 'Дневные сводки'
        ordering = ['-date']


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
