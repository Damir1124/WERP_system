from django.contrib import admin
from .models import Contract

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
