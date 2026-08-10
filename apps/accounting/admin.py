from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Contract, SubjectContract, Installment, PaymentsInstallment,
    Salary, SalaryPayment, FinancialTransactions, Finance,
)
from apps.dashboard.services.export_placeholder import ExportPlaceholderMixin


# =============================================================================
# Контракты
# =============================================================================

class SubjectContractInline(admin.TabularInline):
    """Предметы контракта (товары, количество)"""
    model = SubjectContract
    extra = 1
    fields = ('product', 'quantity', 'note')
    verbose_name = 'Предмет контракта'
    verbose_name_plural = 'Предметы контракта'


@admin.register(SubjectContract)
class SubjectContractAdmin(admin.ModelAdmin):
    list_display = ['contract', 'product', 'quantity', 'note']
    list_filter = ['contract__contract_type', 'product']
    search_fields = ['contract__description', 'product__name', 'note']
    list_per_page = 20


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """Контракты и сделки (доход/расход)"""
    list_display = ['description', 'client', 'date', 'contract_type_badge', 'amount_display', 'file_link']
    list_filter = ['contract_type', 'date', 'client']
    search_fields = ['description', 'client__name', 'note']
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
    search_fields = ('installment__client__name',)
    ordering = ('-payment_date',)
    date_hierarchy = 'payment_date'


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    """Рассрочка для клиентов"""
    list_display = ('id', 'client', 'product', 'amount', 'paid_amount', 'debt', 'due_date', 'status_badge', 'created_at')
    list_filter = ('status', 'due_date', 'client')
    search_fields = ('client__name', 'product__name')
    ordering = ('-due_date',)
    date_hierarchy = 'due_date'
    inlines = [PaymentsInstallmentInline]
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    save_on_top = True

    fieldsets = [
        ('Информация о рассрочке', {
            'fields': ['client', 'product', 'amount', 'paid_amount', 'due_date', 'status'],
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


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('salary', 'payment_type', 'amount', 'date', 'note')
    list_filter = ('payment_type', 'date')
    search_fields = ('salary__worker__full_name', 'note')
    list_per_page = 20
    date_hierarchy = 'date'


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    """Баланс зарплаты сотрудников"""
    list_display = ('worker', 'worker_type', 'balance_display', 'last_payment')
    search_fields = ('worker__full_name',)
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