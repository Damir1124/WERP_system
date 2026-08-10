from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DeliveryLog, DeliveryLogMove,
    CourierShift, CourierTrip, Order, OrderItem,
    OrderNumberCounter,
)
from .forms import OrderForm, OrderItemFormSet
from apps.products.models import Product
from apps.dashboard.services.export_placeholder import ExportPlaceholderMixin


# =============================================================================
# Устаревшие модели (оставлены для совместимости с БД)
# =============================================================================

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

    fieldsets = [
        ('Информация', {
            'fields': ['courier', 'date'],
        }),
        ('Итоги', {
            'fields': ['total_quantity', 'total_sold'],
        }),
    ]

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


# =============================================================================
# Новая архитектура P0: CourierShift → CourierTrip → Order → OrderItem
# =============================================================================

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
    fields = ('trip_link', 'full_loaded', 'full_returned', 'status', 'started_at', 'finished_at')
    readonly_fields = ('trip_link', 'started_at', 'finished_at')
    show_change_link = True
    verbose_name = "Рейс"
    verbose_name_plural = "Рейсы смены"

    @admin.display(description='Рейс')
    def trip_link(self, obj):
        if obj.pk:
            return format_html(
                '<a href="{}">Рейс №{}</a>',
                f'/admin/logistics/couriertrip/{obj.pk}/change/',
                obj.pk
            )
        return '—'


# ─── Смены курьеров ──────────────────────────────────────────────────────────


@admin.register(CourierShift)
class CourierShiftAdmin(ExportPlaceholderMixin, admin.ModelAdmin):
    list_display = (
        'id', 'courier', 'date', 'status_badge', 'trips_count', 'delivered_orders_count',
        'cash_total', 'card_total', 'total_display', 'opened_at', 'closed_at', 'dashboard_link',
    )
    list_filter = ('status', 'date', 'courier')
    search_fields = ('courier__full_name',)
    readonly_fields = ('cash_total', 'card_total', 'opened_at', 'closed_at', 'date')
    date_hierarchy = 'date'
    inlines = [CourierTripInline]
    ordering = ('-date', '-opened_at')
    save_on_top = True
    list_select_related = ('courier',)

    fieldsets = [
        ('Информация о смене', {
            'fields': ['courier', 'date', 'status'],
        }),
        ('Финансы', {
            'fields': ['cash_total', 'card_total'],
        }),
        ('Время', {
            'fields': ['opened_at', 'closed_at'],
            'classes': ['collapse'],
        }),
    ]

    def get_readonly_fields(self, request, obj=None):
        """Для закрытых смен — все поля readonly."""
        fields = list(self.readonly_fields)
        if obj and obj.status == CourierShift.Status.CLOSED:
            for f in ['courier', 'status']:
                if f not in fields:
                    fields.append(f)
        return fields

    @admin.display(description='Статус')
    def status_badge(self, obj):
        if obj.status == CourierShift.Status.OPEN:
            return format_html('<span class="badge-op">Открыта</span>')
        return format_html('<span class="badge-cl">Закрыта</span>')

    @admin.display(description='Итого')
    def total_display(self, obj):
        total = obj.cash_total + obj.card_total
        return f'{total:,} сум'.replace(',', ' ')

    @admin.display(description='Рейсов')
    def trips_count(self, obj):
        return obj.trips.count()

    @admin.display(description='Доставлено')
    def delivered_orders_count(self, obj):
        from django.db.models import Count
        from apps.logistics.models import Order
        return Order.objects.filter(
            trip__shift=obj, status=Order.Status.DELIVERED
        ).count()

    @admin.display(description='Dashboard')
    def dashboard_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" style="font-size:.82rem;">📈 Отчёт</a>',
            f'/dashboard/shifts/{obj.id}/'
        )

    actions = ['close_selected_shifts']

    @admin.action(description='Закрыть выбранные смены')
    def close_selected_shifts(self, request, queryset):
        count = 0
        for shift in queryset.filter(status=CourierShift.Status.OPEN):
            shift.close()
            count += 1
        self.message_user(request, f'Закрыто смен: {count}')


# ─── Рейсы курьеров ──────────────────────────────────────────────────────────


@admin.register(CourierTrip)
class CourierTripAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'shift_link', 'status_badge', 'full_loaded', 'delivered_display',
        'full_returned', 'started_at', 'finished_at', 'orders_link',
    )
    list_filter = ('status', 'shift__courier', 'shift__date')
    search_fields = ('shift__courier__full_name',)
    readonly_fields = ('started_at', 'finished_at')
    ordering = ('-started_at',)
    inlines = [OrderInline]
    list_select_related = ('shift__courier',)

    fieldsets = [
        ('Информация о рейсе', {
            'fields': ['shift', 'status'],
        }),
        ('Загрузка', {
            'fields': ['full_loaded', 'full_returned'],
        }),
        ('Сводка (автоматически)', {
            'fields': ['delivered_display', 'remain_display'],
            'classes': ['collapse'],
        }),
        ('Время', {
            'fields': ['started_at', 'finished_at'],
            'classes': ['collapse'],
        }),
    ]

    def get_readonly_fields(self, request, obj=None):
        """Для завершённых рейсов — все поля readonly."""
        fields = list(self.readonly_fields)
        if obj and obj.status == CourierTrip.Status.DONE:
            for f in ['shift', 'status', 'full_loaded', 'full_returned']:
                if f not in fields:
                    fields.append(f)
        return fields

    @admin.display(description='Смена')
    def shift_link(self, obj):
        return format_html(
            '<a href="{}">Смена #{}</a>',
            f'/admin/logistics/couriershift/{obj.shift.id}/change/',
            obj.shift.id
        )

    @admin.display(description='Статус')
    def status_badge(self, obj):
        if obj.status == CourierTrip.Status.ACTIVE:
            return format_html('<span class="badge-ac">В пути</span>')
        return format_html('<span class="badge-cl">Завершён</span>')

    @admin.display(description='Доставлено')
    def delivered_display(self, obj):
        summary = obj.get_trip_summary()
        return summary['delivered']

    @admin.display(description='Остаток в машине')
    def remain_display(self, obj):
        summary = obj.get_trip_summary()
        return f"Полных: {summary['full_remain']}, Пустых: {summary['empty_received']}, Брак: {summary['defective_received']}"

    @admin.display(description='Заказы')
    def orders_link(self, obj):
        return format_html(
            '<a href="{}?trip__id__exact={}" target="_blank">📋 Список</a>',
            '/admin/logistics/order/',
            obj.pk
        )


# ─── Заказы ──────────────────────────────────────────────────────────────────


@admin.register(Order)
class OrderAdmin(ExportPlaceholderMixin, admin.ModelAdmin):
    form = OrderForm
    change_form_template = 'admin/logistics/order_change_form.html'

    list_display = (
        'id', 'display_number_display', 'client', 'client_phone', 'delivery_address_short',
        'trip_shift_info', 'payment_type', 'status_badge',
        'total_price_display', 'assigned_courier', 'created_at', 'delivered_at',
    )
    list_filter = (
        'status', 'payment_type', 'trip__shift__courier',
        'assigned_courier', 'trip', 'trip__shift__date',
        'created_at', 'delivered_at',
    )
    search_fields = (
        'id', 'display_number', 'client__name', 'client__phone',
        'delivery_address_text', 'note',
    )
    readonly_fields = ('created_at', 'delivered_at', 'display_number')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [OrderItemInline]
    list_per_page = 25
    save_on_top = True
    list_select_related = ('client', 'trip', 'trip__shift', 'trip__shift__courier', 'assigned_courier')

    # ─── Кастомные поля для списка ─────────────────────────────────────────

    @admin.display(description='Номер', ordering='display_number')
    def display_number_display(self, obj):
        if obj.display_number:
            return f'№{obj.display_number:03d}'
        return f'ID:{obj.id}'

    @admin.display(description='Телефон')
    def client_phone(self, obj):
        if obj.client:
            return format_html(
                '<a href="tel:{}">{}</a>',
                obj.client.phone, obj.client.phone
            )
        return '—'

    @admin.display(description='Адрес')
    def delivery_address_short(self, obj):
        addr = obj.delivery_address_text or ''
        if not addr and obj.delivery_address:
            addr = str(obj.delivery_address)
        return addr[:50] + '...' if len(addr) > 50 else addr

    @admin.display(description='Смена / Рейс')
    def trip_shift_info(self, obj):
        if obj.trip and obj.trip.shift:
            return format_html(
                '<a href="{}">Смена #{}</a> / <a href="{}">Рейс #{}</a>',
                f'/admin/logistics/couriershift/{obj.trip.shift.id}/change/',
                obj.trip.shift.id,
                f'/admin/logistics/couriertrip/{obj.trip.id}/change/',
                obj.trip.id,
            )
        if obj.assigned_courier:
            return f'Назначен: {obj.assigned_courier.full_name}'
        return '—'

    @admin.display(description='Сумма')
    def total_price_display(self, obj):
        total = obj.get_total_price()
        return f'{total:,} сум'.replace(',', ' ')

    @admin.display(description='Статус')
    def status_badge(self, obj):
        if obj.status == Order.Status.DELIVERED:
            return format_html('<span class="badge-dl">Доставлен</span>')
        elif obj.status == Order.Status.PENDING:
            return format_html('<span class="badge-pd">Ожидает</span>')
        elif obj.status == Order.Status.CANCELLED:
            return format_html('<span class="badge-cn">Отменён</span>')
        return obj.get_status_display()

    # ─── Защита DELIVERED/CANCELLED заказов ────────────────────────────────

    def get_readonly_fields(self, request, obj=None):
        """Для DELIVERED и CANCELLED заказов — все поля readonly, кроме note."""
        fields = list(self.readonly_fields)

        if obj is None:
            return fields  # Новый заказ — стандартные readonly

        # Добавляем базовые readonly
        fields.extend(['display_number', 'created_at', 'delivered_at'])

        if obj.status == Order.Status.PENDING:
            # PENDING: можно редактировать всё
            return fields

        # DELIVERED или CANCELLED: защищаем
        protected = [
            'trip', 'client', 'delivery_address', 'delivery_address_text',
            'delivery_latitude', 'delivery_longitude', 'assigned_courier',
            'created_by_worker', 'payment_type', 'status',
        ]
        for f in protected:
            if f not in fields:
                fields.append(f)
        return fields

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление доставленных заказов (ломает историю)."""
        if obj and obj.status == Order.Status.DELIVERED:
            return False
        return super().has_delete_permission(request, obj)

    # ─── Admin-действия ────────────────────────────────────────────────────

    actions = ['mark_as_cancelled']

    @admin.action(description='Отменить выбранные PENDING-заказы')
    def mark_as_cancelled(self, request, queryset):
        count = queryset.filter(status=Order.Status.PENDING).update(status=Order.Status.CANCELLED)
        self.message_user(request, f'Отменено PENDING-заказов: {count}')

    # ─── Формы ─────────────────────────────────────────────────────────────

    def get_formsets_with_inlines(self, request, obj=None):
        """Для DELIVERED/CANCELLED не показываем inline-формы."""
        if obj and obj.status != Order.Status.PENDING:
            return  # пустой генератор — inline не показываются
        yield from super().get_formsets_with_inlines(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['products'] = Product.objects.all().order_by('type_product', 'name')
        obj = self.get_object(request, object_id)
        extra_context['order_readonly'] = obj and obj.status != Order.Status.PENDING
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['products'] = Product.objects.all().order_by('type_product', 'name')
        extra_context['order_readonly'] = False
        return super().add_view(request, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)


# ─── Позиции заказов ─────────────────────────────────────────────────────────


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price', 'exchange_qty', 'sell_with_qty', 'defective_qty')
    list_filter = ('product__type_product', 'order__status')
    search_fields = ('product__name', 'order__client__name')
    readonly_fields = ('price',)
    ordering = ('-order__created_at', 'id')
    list_per_page = 25

    fieldsets = [
        ('Информация о позиции', {
            'fields': ['order', 'product', 'quantity', 'price'],
        }),
        ('Учёт тары', {
            'fields': ['exchange_qty', 'sell_with_qty', 'defective_qty'],
            'classes': ['collapse'],
        }),
    ]


# ─── Счётчик номеров заказов ─────────────────────────────────────────────────


@admin.register(OrderNumberCounter)
class OrderNumberCounterAdmin(admin.ModelAdmin):
    """Счётчик декоративных номеров заказов (только просмотр)."""
    list_display = ('id', 'current_number')
    readonly_fields = ('current_number',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
