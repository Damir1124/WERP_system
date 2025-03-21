from django.contrib import admin
from .models import DeliveryJournal, DeliveryJournalProducts, DeliveryLogMove, DeliveryLog


class DeliveryLogMoveInline(admin.TabularInline):
    model = DeliveryLogMove
    extra = 1  # Количество пустых форм для добавления новых записей
    verbose_name = "Движение доставки"  # Отображаемое имя для инлайна
    verbose_name_plural = "Движения доставки"  # Множественное имя для инлайна


class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('courier', 'total_quantity', 'date')
    list_filter = ('courier', 'date')
    search_fields = ('courier__full_name',)
    ordering = ('-date',)
    date_hierarchy = 'date'
    inlines = [DeliveryLogMoveInline]  # Добавляем инлайн для DeliveryLogMove


class DeliveryLogMoveAdmin(admin.ModelAdmin):
    list_display = ('delivery_log', 'action', 'quantity', 'date')
    list_filter = ('action', 'delivery_log__courier', 'date')
    search_fields = ('delivery_log__courier__full_name',)
    ordering = ('-date',)
    date_hierarchy = 'date'


class DeliveryJournalProductsInline(admin.TabularInline):
    model = DeliveryJournalProducts
    extra = 1  # Количество пустых форм для добавления новых продуктов


class DeliveryJournalAdmin(admin.ModelAdmin):
    list_display = ('courier', 'date', 'total_price', 'payment_type')  # Поля, которые будут отображаться в списке
    list_filter = ('courier', 'date', 'payment_type')  # Фильтры по полям
    inlines = [DeliveryJournalProductsInline]  # Встраиваемые продукты в журнале


class DeliveryJournalProductsAdmin(admin.ModelAdmin):
    list_display = ('delivery_journal', 'product', 'quantity', 'note')  # Добавлено поле note
    list_filter = ('product',)  # Фильтры по полям
    search_fields = ('product__name', 'note')  # Поиск по имени продукта и заметке


# Регистрация моделей в админке
admin.site.register(DeliveryLog, DeliveryLogAdmin)
admin.site.register(DeliveryLogMove, DeliveryLogMoveAdmin)
admin.site.register(DeliveryJournal, DeliveryJournalAdmin)
admin.site.register(DeliveryJournalProducts, DeliveryJournalProductsAdmin)
