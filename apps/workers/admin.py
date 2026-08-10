from django.contrib import admin
from .models import Worker
from apps.warehouse.models import Garage


class GarageInline(admin.TabularInline):
    """Inline для отображения автомобиля курьера в карточке сотрудника"""
    model = Garage
    extra = 0
    max_num = 1
    fields = ['vehicle_name', 'plate_number', 'milage', 'year']
    verbose_name = 'Автомобиль'
    verbose_name_plural = 'Автомобиль курьера'


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    """Удобное управление сотрудниками"""
    list_display = ('full_name', 'phone', 'worker_type', 'tg_id', 'is_admin', 'date_for_payed', 'created_at')
    list_filter = ('worker_type', 'is_admin', 'created_at')
    search_fields = ('full_name', 'phone', 'tg_id')
    ordering = ('-created_at',)
    list_per_page = 20
    save_on_top = True
    inlines = [GarageInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = [
        ('Основная информация', {
            'fields': ['full_name', 'phone', 'worker_type'],
        }),
        ('Зарплата', {
            'fields': ['date_for_payed', 'note'],
        }),
        ('Telegram', {
            'fields': ['tg_id', 'is_admin'],
            'classes': ['collapse'],
        }),
        ('Служебное', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Фильтруем типы сотрудников для удобства"""
        if db_field.name == 'worker_type':
            kwargs['choices'] = [
                (Worker.WorkerType.COURIER, 'Курьер'),
                (Worker.WorkerType.PACKER, 'Упаковщик'),
                (Worker.WorkerType.OPERATOR, 'Оператор'),
                (Worker.WorkerType.OTHER, 'Прочие'),
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)
