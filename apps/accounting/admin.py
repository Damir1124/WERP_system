from django.contrib import admin
from .models import Contract, Installment, PaymentsInstallment, Salary, SalaryPayment, SubjectContract, \
    FinancialTransactions, Finance


class SubjectContractInline(admin.TabularInline):
    """Инлайн для отображения SubjectContract в Contract"""
    model = SubjectContract
    extra = 1  # Количество пустых форм для добавления новых записей
    fields = ('product', 'quantity', 'note')  # Поля, которые будут отображаться в инлай

@admin.register(SubjectContract)
class SubjectContractAdmin(admin.ModelAdmin):
    list_display = ["contract", 'product', 'quantity', 'quantity']

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    # Поля, которые будут отображаться в списке
    list_display = ['description', 'client', 'date', 'contract_type', 'amount', 'file']
    # Поля, по которым можно будет фильтровать
    list_filter = ['contract_type', 'date']
    # Поля, по которым можно будет искать
    search_fields = ['description', 'client']
    # Поля, которые будут доступны для редактирования
    fields = ['description','client', 'date', 'file', 'contract_type', 'amount', 'note', ]
    # Количество объектов на странице
    list_per_page = 20
    # Сортировка по умолчанию
    ordering = ['date']
    inlines = [SubjectContractInline]


class PaymentsInstallmentInline(admin.TabularInline):
    """Позвалаяем отображатся инлайном в других тб"""
    model = PaymentsInstallment
    extra = 1

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'product', 'amount', 'paid_amount', 'due_date', 'status', 'created_at')
    list_filter = ('client', 'product', 'status', 'due_date')
    search_fields = ('client__name', 'product__name')
    ordering = ('-due_date',)
    date_hierarchy = 'due_date'
    inlines = [PaymentsInstallmentInline]  #Кладем инлайн для платежей

@admin.register(PaymentsInstallment)
class PaymentsInstallmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'installment', 'amount', 'payment_date', 'created_at')
    list_filter = ('installment', 'payment_date')
    search_fields = ('installment__client__name',)
    ordering = ('-payment_date',)
    date_hierarchy = 'payment_date'


class SalaryPaymentInline(admin.TabularInline):
    """Инлайн-отображение платежей внутри карточки учета зарплаты
       Позволяет видеть историю платежей непосредственно при просмотре Salary"""
    model = SalaryPayment
    extra = 0
    fields = ('salary', 'payment_type', 'amount', 'date', 'note')
    # Если необходимо, можно добавить readonly_fields для отображения полей без возможности редактирования.
    readonly_fields = ()

@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ('worker', 'balance', 'last_payment')
    search_fields = ('worker__name',)
    inlines = [SalaryPaymentInline]

@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('salary', 'payment_type', 'amount', 'date', 'note')
    list_filter = ('payment_type', 'date')
    search_fields = ('salary' ,'note',)


@admin.register(FinancialTransactions)
class FinancialTransactionsAdmin(admin.ModelAdmin):
    list_display = ('date', 'transaction_type', 'amount', 'card_amount', 'source')
    list_filter = ('transaction_type', 'date')
    search_fields = ('source',)

@admin.register(Finance)
class FinanceAdmin(admin.ModelAdmin):
    list_display = ('date', 'income', 'consumption', 'profit', 'card_profit')
    list_filter = ('date',)