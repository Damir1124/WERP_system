"""
Сервис для страницы «Курьеры, смены и рейсы» (/dashboard/couriers/).

Содержит функции для статистики по курьерам, списка смен и деталей смены.
"""
import logging
from dataclasses import dataclass, field

from django.db.models import Sum, Count, Q

from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.workers.models import Worker
from apps.dashboard.services.filters import Period

logger = logging.getLogger(__name__)


@dataclass
class CourierStatsRow:
    """Строка статистики по курьеру."""
    courier_id: int
    name: str
    shifts_count: int = 0
    trips_count: int = 0
    orders_delivered: int = 0
    units_sold: int = 0
    cash_total: int = 0
    card_total: int = 0
    revenue: int = 0
    avg_check: int = 0


def get_courier_stats(period: Period) -> list:
    """Статистика по курьерам за период."""
    if period.is_empty:
        return []

    # Все курьеры
    couriers = Worker.objects.filter(worker_type=Worker.WorkerType.COURIER)

    rows = []
    for courier in couriers:
        # Фильтр по заказам курьера через trip.shift.courier
        order_filter = Q(
            trip__shift__courier=courier,
            status=Order.Status.DELIVERED,
            delivered_at__date__gte=period.date_from,
            delivered_at__date__lte=period.date_to,
        )

        # Доставлено заказов
        orders_delivered = Order.objects.filter(order_filter).count()

        # Продано единиц
        units = OrderItem.objects.filter(
            order__trip__shift__courier=courier,
            order__status=Order.Status.DELIVERED,
            order__delivered_at__date__gte=period.date_from,
            order__delivered_at__date__lte=period.date_to,
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # Выручка
        revenue = OrderItem.objects.filter(
            order__trip__shift__courier=courier,
            order__status=Order.Status.DELIVERED,
            order__delivered_at__date__gte=period.date_from,
            order__delivered_at__date__lte=period.date_to,
        ).aggregate(total=Sum('price'))['total'] or 0

        # Наличные и карта (через CourierShift — агрегированные поля)
        shifts_qs = CourierShift.objects.filter(
            courier=courier,
            date__gte=period.date_from,
            date__lte=period.date_to,
        )
        shift_agg = shifts_qs.aggregate(
            cash=Sum('cash_total'),
            card=Sum('card_total'),
        )
        cash_total = shift_agg['cash'] or 0
        card_total = shift_agg['card'] or 0

        # Смены и рейсы
        shifts_count = shifts_qs.count()
        trips_count = CourierTrip.objects.filter(
            shift__courier=courier,
            shift__date__gte=period.date_from,
            shift__date__lte=period.date_to,
        ).count()

        rows.append(CourierStatsRow(
            courier_id=courier.id,
            name=courier.full_name,
            shifts_count=shifts_count,
            trips_count=trips_count,
            orders_delivered=orders_delivered,
            units_sold=units,
            cash_total=cash_total,
            card_total=card_total,
            revenue=revenue,
            avg_check=revenue // orders_delivered if orders_delivered > 0 else 0,
        ))

    # Сортировка по доставленным заказам (убывание)
    rows.sort(key=lambda r: r.orders_delivered, reverse=True)
    return rows


@dataclass
class ShiftRow:
    """Строка списка смен."""
    id: int
    courier_id: int
    courier_name: str
    date: str
    status: str
    status_display: str
    opened_at: str
    closed_at: str | None
    trips_count: int = 0
    orders_delivered: int = 0
    cash_total: int = 0
    card_total: int = 0
    total: int = 0


def get_shifts_list(period: Period, courier_id: str = '', status_filter: str = '') -> list:
    """Список смен за период с фильтрацией."""
    if period.is_empty:
        return []

    qs = CourierShift.objects.select_related('courier').filter(
        date__gte=period.date_from,
        date__lte=period.date_to,
    )

    if courier_id:
        try:
            qs = qs.filter(courier_id=int(courier_id))
        except ValueError:
            pass

    if status_filter:
        qs = qs.filter(status=status_filter)

    qs = qs.order_by('-date', '-opened_at')

    rows = []
    for shift in qs:
        # Доставлено заказов в смене
        delivered = Order.objects.filter(
            trip__shift=shift,
            status=Order.Status.DELIVERED,
        ).count()

        # Рейсы в смене
        trips_count = shift.trips.count()

        rows.append(ShiftRow(
            id=shift.id,
            courier_id=shift.courier.id if shift.courier else None,
            courier_name=shift.courier.full_name if shift.courier else '—',
            date=shift.date.isoformat(),
            status=shift.status,
            status_display=shift.get_status_display(),
            opened_at=shift.opened_at.isoformat() if shift.opened_at else '',
            closed_at=shift.closed_at.isoformat() if shift.closed_at else None,
            trips_count=trips_count,
            orders_delivered=delivered,
            cash_total=shift.cash_total,
            card_total=shift.card_total,
            total=shift.cash_total + shift.card_total,
        ))
    return rows


@dataclass
class TripSummary:
    """Сводка по рейсу."""
    id: int
    status: str
    started_at: str
    finished_at: str | None
    full_loaded: int = 0
    delivered: int = 0
    full_returned: int = 0
    full_remain: int = 0
    empty_received: int = 0
    defective_received: int = 0


@dataclass
class ShiftDetailData:
    """Детали смены."""
    id: int
    courier_name: str
    date: str
    status: str
    status_display: str
    opened_at: str
    closed_at: str | None
    cash_total: int = 0
    card_total: int = 0
    total: int = 0
    trips: list = field(default_factory=list)
    orders: list = field(default_factory=list)


def get_shift_detail(shift_id: int) -> ShiftDetailData | None:
    """Детали смены с рейсами и заказами."""
    try:
        shift = CourierShift.objects.select_related('courier').get(id=shift_id)
    except CourierShift.DoesNotExist:
        return None

    data = ShiftDetailData(
        id=shift.id,
        courier_name=shift.courier.full_name if shift.courier else '—',
        date=shift.date.isoformat(),
        status=shift.status,
        status_display=shift.get_status_display(),
        opened_at=shift.opened_at.isoformat() if shift.opened_at else '',
        closed_at=shift.closed_at.isoformat() if shift.closed_at else None,
        cash_total=shift.cash_total,
        card_total=shift.card_total,
        total=shift.cash_total + shift.card_total,
    )

    # Рейсы смены
    trips = shift.trips.all().order_by('started_at')
    for trip in trips:
        summary = trip.get_trip_summary()
        data.trips.append(TripSummary(
            id=trip.id,
            status=trip.status,
            started_at=trip.started_at.isoformat() if trip.started_at else '',
            finished_at=trip.finished_at.isoformat() if trip.finished_at else None,
            full_loaded=summary['full_loaded'],
            delivered=summary['delivered'],
            full_returned=summary['full_returned'],
            full_remain=summary['full_remain'],
            empty_received=summary['empty_received'],
            defective_received=summary['defective_received'],
        ))

        # Заказы рейса
        orders = Order.objects.filter(trip=trip).select_related(
            'client', 'delivery_address',
        ).prefetch_related('items__product').order_by('created_at')

        for o in orders:
            items_data = []
            for item in o.items.all():
                items_data.append({
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'exchange_qty': item.exchange_qty,
                    'sell_with_qty': item.sell_with_qty,
                    'defective_qty': item.defective_qty,
                })
            data.orders.append({
                'id': o.id,
                'human_number': o.human_number,
                'client_name': o.client.name if o.client else '—',
                'address': o.display_address(),
                'status': o.status,
                'status_display': o.get_status_display(),
                'payment_type_display': o.get_payment_type_display(),
                'total_price': o.get_total_price(),
                'items': items_data,
                'trip_id': trip.id,
            })

    return data


def get_courier_choices() -> list:
    """Список курьеров для фильтра."""
    return list(
        Worker.objects.filter(worker_type=Worker.WorkerType.COURIER)
        .values('id', 'full_name')
        .order_by('full_name')
    )