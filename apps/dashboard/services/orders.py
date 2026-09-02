"""
Сервис для страницы «Заказы и продажи» (/dashboard/orders/).

Содержит функции для KPI заказов и таблицы с пагинацией.
"""
import logging
from dataclasses import dataclass, field

from django.core.paginator import Paginator, Page
from django.db.models import Sum, Count, Q

from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.workers.models import Worker
from apps.dashboard.services.filters import Period
from apps.dashboard.services.historical import (
    get_historical_totals, should_include_historical,
)

logger = logging.getLogger(__name__)


@dataclass
class OrdersPageData:
    """Все данные для страницы заказов."""
    # KPI
    orders_created: int = 0
    orders_delivered: int = 0
    orders_cancelled: int = 0
    orders_pending: int = 0
    avg_check: int = 0
    units_sold: int = 0

    # Исторические показатели «За всё время»
    historical_orders_created_total: int = 0
    historical_water_sold_total: int = 0
    historical_included: bool = False

    # Таблица
    orders_page: Page | None = None
    total_count: int = 0

    # Фильтры (для формы)
    status_filter: str = ''
    courier_filter: str = ''
    payment_filter: str = ''
    search_query: str = ''

    # Для выпадающих списков фильтров
    courier_choices: list = field(default_factory=list)


def _orders_kpi(period: Period) -> dict:
    """KPI для страницы заказов."""
    result = {
        'orders_created': 0,
        'orders_delivered': 0,
        'orders_cancelled': 0,
        'orders_pending': 0,
        'avg_check': 0,
        'units_sold': 0,
    }

    if period.is_empty:
        # Режим «all» — считаем ВСЕ заказы (без фильтра по дате)
        result['orders_created'] = Order.objects.count()
        result['orders_delivered'] = Order.objects.filter(
            status=Order.Status.DELIVERED,
        ).count()
        result['orders_cancelled'] = Order.objects.filter(
            status=Order.Status.CANCELLED,
        ).count()
        units = OrderItem.objects.filter(
            order__status=Order.Status.DELIVERED,
        ).aggregate(total=Sum('quantity'))
        result['units_sold'] = units['total'] or 0
    else:
        # Создано
        result['orders_created'] = Order.objects.filter(
            created_at__date__gte=period.date_from,
            created_at__date__lte=period.date_to,
        ).count()

        # Доставлено
        result['orders_delivered'] = Order.objects.filter(
            status=Order.Status.DELIVERED,
            delivered_at__date__gte=period.date_from,
            delivered_at__date__lte=period.date_to,
        ).count()

        # Отменено
        result['orders_cancelled'] = Order.objects.filter(
            status=Order.Status.CANCELLED,
            created_at__date__gte=period.date_from,
            created_at__date__lte=period.date_to,
        ).count()

        # Продано единиц
        units = OrderItem.objects.filter(
            order__status=Order.Status.DELIVERED,
            order__delivered_at__date__gte=period.date_from,
            order__delivered_at__date__lte=period.date_to,
        ).aggregate(total=Sum('quantity'))
        result['units_sold'] = units['total'] or 0

        # Средний чек
        if result['orders_delivered'] > 0:
            total_revenue = OrderItem.objects.filter(
                order__status=Order.Status.DELIVERED,
                order__delivered_at__date__gte=period.date_from,
                order__delivered_at__date__lte=period.date_to,
            ).aggregate(total=Sum('price'))['total'] or 0
            result['avg_check'] = total_revenue // result['orders_delivered']

    # В ожидании (текущие, без периода)
    result['orders_pending'] = Order.objects.filter(
        status=Order.Status.PENDING,
    ).count()

    return result


def _get_orders_queryset(period: Period, filters: dict):
    """Базовый QuerySet заказов с фильтрацией."""
    qs = Order.objects.select_related(
        'client', 'assigned_courier', 'trip__shift__courier',
        'delivery_address',
    ).prefetch_related('items__product')

    if not period.is_empty:
        qs = qs.filter(
            created_at__date__gte=period.date_from,
            created_at__date__lte=period.date_to,
        )

    # Фильтр по статусу
    status = filters.get('status', '')
    if status:
        qs = qs.filter(status=status)

    # Фильтр по типу оплаты
    payment = filters.get('payment', '')
    if payment:
        qs = qs.filter(payment_type=payment)

    # Фильтр по курьеру (через trip.shift.courier или assigned_courier)
    courier_id = filters.get('courier', '')
    if courier_id:
        try:
            cid = int(courier_id)
            qs = qs.filter(
                Q(trip__shift__courier_id=cid) | Q(assigned_courier_id=cid)
            )
        except ValueError:
            pass

    # Поиск по клиенту / телефону / декоративному номеру
    search = filters.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(client__name__icontains=search) |
            Q(client__phone__icontains=search) |
            Q(display_number=search) |
            Q(id=search)
        )

    return qs.order_by('-created_at')


def get_orders_page(period: Period, filters: dict, page_num: int = 1, per_page: int = 25) -> OrdersPageData:
    """Получить страницу заказов со всеми данными."""
    data = OrdersPageData()

    # KPI
    kpi = _orders_kpi(period)
    data.orders_created = kpi['orders_created']
    data.orders_delivered = kpi['orders_delivered']
    data.orders_cancelled = kpi['orders_cancelled']
    data.orders_pending = kpi['orders_pending']
    data.avg_check = kpi['avg_check']
    data.units_sold = kpi['units_sold']

    # Исторические показатели «За всё время» — только в режиме all
    if should_include_historical(period):
        hist = get_historical_totals()
        data.historical_orders_created_total = hist.orders_created_total
        data.historical_water_sold_total = hist.water_sold_total
        data.historical_included = hist.exists
        data.orders_created += hist.orders_created_total
        data.units_sold += hist.water_sold_total

    # Фильтры
    data.status_filter = filters.get('status', '')
    data.payment_filter = filters.get('payment', '')
    data.courier_filter = filters.get('courier', '')
    data.search_query = filters.get('search', '')

    # Список курьеров для фильтра
    data.courier_choices = list(
        Worker.objects.filter(worker_type=Worker.WorkerType.COURIER)
        .values('id', 'full_name')
        .order_by('full_name')
    )

    # Пагинация
    qs = _get_orders_queryset(period, filters)
    paginator = Paginator(qs, per_page)
    data.orders_page = paginator.get_page(page_num)
    data.total_count = paginator.count

    return data