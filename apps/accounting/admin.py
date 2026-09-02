from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import (
    Contract, SubjectContract, Installment, InstallmentItem, PaymentsInstallment,
    Salary, SalaryPeriod, SalaryPayment, FinancialTransactions, Finance,
    HistoricalStats,
)
from apps.dashboard.services.export_placeholder import ExportPlaceholderMixin


# =============================================================================
# Контракты
# =============================================================================

class SubjectContractInline(admin.TabularInline):
    """Предметы контракта (товары, количество)"""
    model = SubjectContract
    extra = 1
    fields = ('product', 'warehouse_product', 'quantity', 'note')
    verbose_name = 'Предмет контракта'
    verbose_name_plural = 'Предметы контракта'


@admin.register(SubjectContract)
class SubjectContractAdmin(admin.ModelAdmin):
    list_display = ['contract', 'product', 'warehouse_product', 'quantity', 'note']
    list_filter = ['contract__contract_type', 'product', 'warehouse_product']
    search_fields = ['contract__description', 'product__name', 'warehouse_product__name', 'note']
    autocomplete_fields = ['contract', 'product', 'warehouse_product']
    list_select_related = ('contract', 'product', 'warehouse_product')
    list_per_page = 20


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """Контракты и сделки (доход/расход)"""
    list_display = ['description', 'client', 'date', 'contract_type_badge', 'amount_display', 'file_link']
    list_filter = ['contract_type', 'date', 'client']
    search_fields = ['description', 'client__name', 'client__phone', 'note']
    autocomplete_fields = ['client']
    list_select_related = ('client',)
    list_per_page = 20
    ordering = ['-date']
    date_hierarchy = 'date'
    inlines = [SubjectContractInline]
    save_on_top = True

    fieldsets = [
        ('Основная информация', {
            'fields': ['description', 'client', 'date', 'contract_type', 'amount'],
        }),
        ('Документы и примечания', {
            'fields': ['file', 'note'],
        }),
    ]

    @admin.display(description='Тип')
    def contract_type_badge(self, obj):
        if obj.contract_type == Contract.ContractType.SELL:
            return format_html('<span class="badge-dl">Доход</span>')
        return format_html('<span class="badge-cn">Расход</span>')

    @admin.display(description='Сумма')
    def amount_display(self, obj):
        return f'{obj.amount:,} сум'.replace(',', ' ')

    @admin.display(description='Файл')
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📎 Открыть</a>', obj.file.url)
        return '—'


# =============================================================================
# Рассрочки
# =============================================================================

class PaymentsInstallmentInline(admin.TabularInline):
    """Платежи по рассрочке"""
    model = PaymentsInstallment
    extra = 1
    fields = ('amount', 'payment_date')
    verbose_name = 'Платёж'
    verbose_name_plural = 'Платежи по рассрочке'


@admin.register(PaymentsInstallment)
class PaymentsInstallmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'installment', 'amount', 'payment_date', 'created_at')
    list_filter = ('installment', 'payment_date')
    search_fields = ('installment__client__name', 'installment__client__phone')
    autocomplete_fields = ('installment',)
    list_select_related = ('installment__client',)
    ordering = ('-payment_date',)
    date_hierarchy = 'payment_date'


class InstallmentItemInline(admin.TabularInline):
    """Позиции рассрочки (товары, количество, цена)"""
    model = InstallmentItem
    extra = 1
    fields = ('product', 'quantity', 'price_per_unit', 'subtotal')
    readonly_fields = ('subtotal',)
    verbose_name = 'Позиция рассрочки'
    verbose_name_plural = 'Позиции рассрочки'


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    """Рассрочка для клиентов (шапка + позиции)"""
    list_display = ('id', 'client', 'order', 'issued_by', 'amount', 'paid_amount', 'debt', 'due_date', 'status_badge', 'created_at')
    list_filter = ('status', 'due_date', 'client')
    search_fields = ('client__name', 'client__phone', 'items__product__name', 'order__id')
    autocomplete_fields = ('client', 'order', 'issued_by')
    list_select_related = ('client', 'order', 'issued_by')
    ordering = ('-due_date',)
    date_hierarchy = 'due_date'
    inlines = [InstallmentItemInline, PaymentsInstallmentInline]
    readonly_fields = ['created_at', 'updated_at', 'amount']
    list_per_page = 20
    save_on_top = True

    fieldsets = [
        ('Информация о рассрочке', {
            'fields': ['client', 'order', 'issued_by', 'amount', 'paid_amount', 'due_date', 'status'],
        }),
        ('Служебное', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Статус')
    def status_badge(self, obj):
        if obj.status == Installment.InstallmentStatus.CLOSED:
            return format_html('<span class="badge-dl">Погашен</span>')
        elif obj.status == Installment.InstallmentStatus.OVERDUE:
            return format_html('<span class="badge-cn">Просрочен</span>')
        return format_html('<span class="badge-pd">Активен</span>')

    @admin.display(description='Остаток долга')
    def debt(self, obj):
        debt_amount = (obj.amount or 0) - (obj.paid_amount or 0)
        return f'{debt_amount:,} сум'.replace(',', ' ')


# =============================================================================
# Зарплаты
# =============================================================================

class SalaryPaymentInline(admin.TabularInline):
    """Платежи по зарплате внутри карточки сотрудника"""
    model = SalaryPayment
    extra = 0
    fields = ('payment_type', 'amount', 'date', 'note')
    verbose_name = 'Платёж'
    verbose_name_plural = 'Платежи по зарплате'


class SalaryPeriodPaymentInline(admin.TabularInline):
    """Платежи по зарплате внутри зарплатного периода"""
    model = SalaryPayment
    extra = 0
    fields = ('payment_type', 'amount', 'date', 'note')
    readonly_fields = ('period',)
    verbose_name = 'Платёж'
    verbose_name_plural = 'Платежи за период'


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('salary', 'period', 'payment_type', 'amount', 'date', 'note')
    list_filter = ('payment_type', 'date', 'period__month', 'salary__worker__worker_type')
    search_fields = ('salary__worker__full_name', 'salary__worker__phone', 'note')
    autocomplete_fields = ('salary', 'period')
    list_select_related = ('salary__worker', 'period')
    list_per_page = 20
    date_hierarchy = 'date'


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    """Баланс зарплаты сотрудников"""
    list_display = ('worker', 'worker_type', 'balance_display', 'last_payment')
    search_fields = ('worker__full_name', 'worker__phone')
    autocomplete_fields = ('worker',)
    list_select_related = ('worker',)
    readonly_fields = ('balance',)
    inlines = [SalaryPaymentInline]
    list_per_page = 20

    fieldsets = [
        ('Информация', {
            'fields': ['worker', 'balance', 'last_payment'],
        }),
    ]

    @admin.display(description='Тип сотрудника')
    def worker_type(self, obj):
        return obj.worker.get_worker_type_display()

    @admin.display(description='Баланс')
    def balance_display(self, obj):
        return f'{obj.balance:,} сум'.replace(',', ' ')


@admin.register(SalaryPeriod)
class SalaryPeriodAdmin(admin.ModelAdmin):
    """Зарплатный период (месяц) сотрудника с итогами."""
    list_display = (
        'worker', 'month', 'salary_amount_display', 'bonuses_display',
        'fines_display', 'advances_display', 'paid_salary_display',
        'remaining_display', 'salary_date', 'status_badge',
    )
    list_filter = ('status', 'month', 'worker__worker_type')
    search_fields = ('worker__full_name', 'worker__phone')
    autocomplete_fields = ('worker',)
    list_select_related = ('worker',)
    readonly_fields = (
        'salary_amount', 'bonuses', 'fines', 'advances', 'paid_salary',
        'accrued_display', 'paid_total_display', 'remaining_display',
        'created_at', 'updated_at',
    )
    inlines = [SalaryPeriodPaymentInline]
    list_per_page = 20
    save_on_top = True

    fieldsets = [
        ('Период', {
            'fields': ['worker', 'month', 'status', 'salary_date'],
        }),
        ('Начислено', {
            'fields': ['salary_amount', 'bonuses', 'fines', 'accrued_display'],
        }),
        ('Выплачено', {
            'fields': ['advances', 'paid_salary', 'paid_total_display', 'remaining_display'],
        }),
        ('Служебное', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Оклад')
    def salary_amount_display(self, obj):
        return f'{obj.salary_amount:,} сум'.replace(',', ' ')

    @admin.display(description='Бонусы')
    def bonuses_display(self, obj):
        return f'{obj.bonuses:,} сум'.replace(',', ' ')

    @admin.display(description='Штрафы')
    def fines_display(self, obj):
        return f'{obj.fines:,} сум'.replace(',', ' ')

    @admin.display(description='Авансы')
    def advances_display(self, obj):
        return f'{obj.advances:,} сум'.replace(',', ' ')

    @admin.display(description='Зарплата')
    def paid_salary_display(self, obj):
        return f'{obj.paid_salary:,} сум'.replace(',', ' ')

    @admin.display(description='Начислено')
    def accrued_display(self, obj):
        return f'{obj.accrued:,} сум'.replace(',', ' ')

    @admin.display(description='Выплачено')
    def paid_total_display(self, obj):
        return f'{obj.paid_total:,} сум'.replace(',', ' ')

    @admin.display(description='Остаток к выдаче')
    def remaining_display(self, obj):
        color = '#00b894' if obj.remaining >= 0 else '#d63031'
        formatted = f'{obj.remaining:,}'.replace(',', ' ')
        return format_html(
            '<span style="color:{}; font-weight:bold">{} сум</span>',
            color, formatted
        )

    @admin.display(description='Статус')
    def status_badge(self, obj):
        if obj.status == SalaryPeriod.PeriodStatus.PAID:
            return format_html('<span class="badge-dl">Выплачен</span>')
        elif obj.status == SalaryPeriod.PeriodStatus.CLOSED:
            return format_html('<span class="badge-cn">Закрыт</span>')
        return format_html('<span class="badge-pd">Открыт</span>')


# =============================================================================
# Финансовые транзакции
# =============================================================================

@admin.register(FinancialTransactions)
class FinancialTransactionsAdmin(ExportPlaceholderMixin, admin.ModelAdmin):
    """Лог всех денежных операций (только просмотр)"""
    list_display = ('date', 'transaction_type_badge', 'amount_display', 'card_amount_display', 'source', 'description')
    list_filter = ('transaction_type', 'date', 'source')
    search_fields = ('source', 'description')
    date_hierarchy = 'date'
    readonly_fields = ('date', 'transaction_type', 'amount', 'card_amount', 'source', 'description')
    list_per_page = 30
    ordering = ('-date',)

    def has_add_permission(self, request):
        """Запрещаем ручное создание транзакций (создаются бизнес-логикой)"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление транзакций"""
        return False

    fieldsets = [
        ('Информация о транзакции', {
            'fields': ['date', 'transaction_type', 'source'],
        }),
        ('Суммы', {
            'fields': ['amount', 'card_amount'],
        }),
        ('Примечание', {
            'fields': ['description'],
            'classes': ['collapse'],
        }),
    ]

    @admin.display(description='Тип')
    def transaction_type_badge(self, obj):
        if obj.transaction_type == FinancialTransactions.TransactionsType.PLUS:
            return format_html('<span class="badge-dl">Доход</span>')
        return format_html('<span class="badge-cn">Расход</span>')

    @admin.display(description='Сумма')
    def amount_display(self, obj):
        if obj.amount:
            return f'{obj.amount:,} сум'.replace(',', ' ')
        return '—'

    @admin.display(description='Карта')
    def card_amount_display(self, obj):
        if obj.card_amount:
            return f'{obj.card_amount:,} сум'.replace(',', ' ')
        return '—'


# =============================================================================
# Дневная сводка Finance
# =============================================================================

@admin.register(Finance)
class FinanceAdmin(admin.ModelAdmin):
    """Дневная финансовая сводка"""
    list_display = ('date', 'income_display', 'consumption_display', 'profit_display', 'card_profit_display')
    list_filter = ('date',)
    date_hierarchy = 'date'
    readonly_fields = ('income', 'consumption', 'profit', 'card_profit', 'date')
    ordering = ('-date',)

    fieldsets = [
        ('Финансовая сводка', {
            'fields': ['date', 'income', 'consumption', 'profit', 'card_profit'],
        }),
    ]

    @admin.display(description='Доход')
    def income_display(self, obj):
        return f'{obj.income:,} сум'.replace(',', ' ')

    @admin.display(description='Расход')
    def consumption_display(self, obj):
        return f'{obj.consumption:,} сум'.replace(',', ' ')

    @admin.display(description='Прибыль')
    def profit_display(self, obj):
        color = '#00b894' if obj.profit >= 0 else '#d63031'
        formatted = f'{obj.profit:,}'.replace(',', ' ')
        return format_html(
            '<span style="color:{}; font-weight:bold">{} сум</span>',
            color, formatted
        )

    @admin.display(description='Безнал')
    def card_profit_display(self, obj):
        return f'{obj.card_profit:,} сум'.replace(',', ' ')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# Историческая база (до запуска WERP)
# =============================================================================

@admin.register(HistoricalStats)
class HistoricalStatsAdmin(admin.ModelAdmin):
    """
    Единственная запись стартовых исторических показателей.

    Доступ к изменению — только Owner / superuser.
    Обычный Dispatcher (is_staff без is_superuser) не может изменять/удалять.
    """
    list_display = [
        'historical_orders_created_total',
        'historical_water_sold_total',
        'werp_start_date',
        'source',
        'updated_at',
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']

    fieldsets = [
        ('Исторические показатели «За всё время»', {
            'fields': [
                'historical_orders_created_total',
                'historical_water_sold_total',
            ],
            'description': (
                '⚠️ <b>Внимание!</b> Изменение этих значений повлияет на показатели '
                '«За всё время» на Dashboard и в Admin Mini App. '
                'Исторические данные прибавляются ТОЛЬКО к итогам «За всё время» '
                'и не влияют на сегодня / неделю / месяц / смены / рейсы / кассу / финансы / склад.'
            ),
        }),
        ('Параметры запуска', {
            'fields': ['werp_start_date', 'source'],
        }),
        ('Служебная информация', {
            'fields': ['created_at', 'updated_at', 'created_by', 'updated_by'],
            'classes': ['collapse'],
        }),
    ]

    def has_view_permission(self, request, obj=None):
        # Видеть запись могут только Owner / superuser
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        # Создание второй записи запрещено (singleton). Только superuser.
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        # Удаление запрещено без отдельного привилегированного действия.
        return False

    def save_model(self, request, obj, form, change):
        # Автофиксация автора изменения
        if not obj.pk:
            obj.created_by = getattr(request.user, 'worker', None)
        obj.updated_by = getattr(request.user, 'worker', None)
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        # Singleton: если запись уже есть — сразу открываем её на редактирование.
        obj = HistoricalStats.objects.first()
        if obj:
            return HttpResponseRedirect(
                reverse('admin:accounting_historicalstats_change', args=[obj.pk])
            )
        return super().changelist_view(request, extra_context=extra_context)