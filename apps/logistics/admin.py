from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DeliveryLog, DeliveryLogMove,
    CourierShift, CourierTrip, Order, OrderItem,
    OrderNumberCounter,
)
from .forms import OrderForm, OrderItemFormSet
from apps.products.models import Product


# ─── Устаревшие модели (оставлены для совместимости) ──────────────────────────

class DeliveryLogMoveInline(admin.TabularInline):
    model = DeliveryLogMove
    extra = 1
    verbose_name = "Движение доставки"
    verbose_name_plural = "Движения доставки"


class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('courier', 'total_quantity', 'total_sold', 'date')
    list_filter = ('courier', 'date')
    search_fields = ('courier__full_name',)
    ordering = ('-date',)
    date_hierarchy = 'date'
    inlines = [DeliveryLogMoveInline]
    readonly_fields = ('total_quantity', 'total_sold')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.check_total_quantity()


class DeliveryLogMoveAdmin(admin.ModelAdmin):
    list_display = ('delivery_log', 'action', 'quantity', 'date')
    list_filter = ('action', 'delivery_log__courier', 'date')
    search_fields = ('delivery_log__courier__full_name',)
    ordering = ('-date',)
    date_hierarchy = 'date'


admin.site.register(DeliveryLog, DeliveryLogAdmin)
admin.site.register(DeliveryLogMove, DeliveryLogMoveAdmin)


# ─── Новая архитектура P0: CourierShift → CourierTrip → Order → OrderItem ─────

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('product', 'quantity', 'price', 'exchange_qty', 'sell_with_qty', 'defective_qty')
    readonly_fields = ('price',)
    verbose_name = "Позиция заказа"
    verbose_name_plural = "Позиции заказа"


class OrderInline(admin.TabularInline):
    model = Order
    extra = 0
    fields = ('display_number', 'client', 'payment_type', 'status', 'assigned_courier', 'note', 'created_at', 'delivered_at')
    readonly_fields = ('created_at', 'delivered_at', 'display_number')
    show_change_link = True
    verbose_name = "Заказ"
    verbose_name_plural = "Заказы рейса"


class CourierTripInline(admin.TabularInline):
    model = CourierTrip
    extra = 0
    fields = ('full_loaded', 'full_returned', 'status', 'started_at', 'finished_at')
    readonly_fields = ('started_at', 'finished_at')
    show_change_link = True
    verbose_name = "Рейс"
    verbose_name_plural = "Рейсы смены"


@admin.register(CourierShift)
class CourierShiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'courier', 'date', 'status_badge', 'cash_total', 'card_total', 'total_display', 'opened_at', 'closed_at')
    list_filter = ('status', 'date', 'courier')
    search_fields = ('courier__full_name',)
    readonly_fields = ('cash_total', 'card_total', 'opened_at', 'closed_at', 'date')
    date_hierarchy = 'date'
    inlines = [CourierTripInline]
    ordering = ('-date', '-opened_at')

    @admin.display(description='Статус')
    def status_badge(self, obj):
        color = 'green' if obj.status == CourierShift.Status.OPEN else 'gray'
        label = obj.get_status_display()
        return format_html('<span style="color:{}; font-weight:bold">{}</span>', color, label)

    @admin.display(description='Итого')
    def total_display(self, obj):
        return obj.cash_total + obj.card_total

    actions = ['close_selected_shifts']

    @admin.action(description='Закрыть выбранные смены')
    def close_selected_shifts(self, request, queryset):
        for shift in queryset.filter(status=CourierShift.Status.OPEN):
            shift.close()
        self.message_user(request, f'Закрыто смен: {queryset.count()}')


@admin.register(CourierTrip)
class CourierTripAdmin(admin.ModelAdmin):
    list_display = ('id', 'shift', 'status', 'full_loaded', 'full_returned', 'started_at', 'finished_at')
    list_filter = ('status', 'shift__courier', 'shift__date')
    search_fields = ('shift__courier__full_name',)
    readonly_fields = ('started_at', 'finished_at')
    ordering = ('-started_at',)
    inlines = [OrderInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderForm
    change_form_template = 'admin/logistics/order_change_form.html'
    
    list_display = (
        'id', 'display_number_display', 'trip', 'client', 'payment_type', 'status',
        'total_price_display', 'assigned_courier', 'created_at', 'delivered_at',
    )
    list_filter = ('status', 'payment_type', 'trip__shift__courier', 'trip__shift__date')
    search_fields = ('client__name', 'client__phone', 'note', 'display_number')
    readonly_fields = ('created_at', 'delivered_at', 'display_number')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [OrderItemInline]

    @admin.display(description='Декоративный номер')
    def display_number_display(self, obj):
        if obj.display_number:
            return f'Заказ N{obj.display_number:03d}'
        return '—'

    @admin.display(description='Сумма')
    def total_price_display(self, obj):
        return obj.get_total_price()

    actions = ['mark_as_delivered', 'mark_as_cancelled']

    @admin.action(description='Отметить как доставленные')
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status=Order.Status.DELIVERED, delivered_at=timezone.now())

    @admin.action(description='Отметить как отменённые')
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status=Order.Status.CANCELLED)
    
    def get_inline_instances(self, request, obj=None):
        """Переопределяем для использования formset вместо стандартных inline"""
        # Возвращаем пустой список, т.к. мы используем кастомный шаблон
        # с formset, а не стандартные inline формы
        if request.path.endswith('/add/') or (obj and request.path.endswith('/change/')):
            return []
        return super().get_inline_instances(request, obj)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Добавляем formset и список продуктов в контекст"""
        extra_context = extra_context or {}
        
        # Добавляем список всех продуктов для селекта
        extra_context['products'] = Product.objects.all().order_by('type_product', 'name')
        
        # Получаем объект заказа
        obj = self.get_object(request, object_id)
        
        if request.method == 'POST':
            formset = OrderItemFormSet(request.POST, instance=obj)
        else:
            formset = OrderItemFormSet(instance=obj)
        
        extra_context['inline_admin_formsets'] = [{'formset': formset}]
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        """Добавляем formset и список продуктов в контекст для создания"""
        extra_context = extra_context or {}
        
        # Добавляем список всех продуктов для селекта
        extra_context['products'] = Product.objects.all().order_by('type_product', 'name')
        
        if request.method == 'POST':
            form = self.get_form(request)(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                formset = OrderItemFormSet(request.POST, instance=obj)
            else:
                formset = OrderItemFormSet(request.POST)
        else:
            formset = OrderItemFormSet()
        
        extra_context['inline_admin_formsets'] = [{'formset': formset}]
        
        return super().add_view(request, form_url, extra_context)
    
    def save_model(self, request, obj, form, change):
        """Сохраняем заказ и связанные позиции"""
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """Сохраняем связанные позиции заказа"""
        super().save_related(request, form, formsets, change)
        
        # Сохраняем formset с позициями заказа
        formset = OrderItemFormSet(request.POST, instance=form.instance)
        if formset.is_valid():
            formset.save()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price', 'exchange_qty', 'sell_with_qty', 'defective_qty')
    list_filter = ('product__type_product', 'order__status')
    search_fields = ('product__name', 'order__client__name')
    readonly_fields = ('price',)
    ordering = ('-order__created_at', 'id')


@admin.register(OrderNumberCounter)
class OrderNumberCounterAdmin(admin.ModelAdmin):
    """Счётчик декоративных номеров заказов (только просмотр)."""
    list_display = ('id', 'current_number')
    readonly_fields = ('current_number',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
