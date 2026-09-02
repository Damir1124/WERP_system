"""
Сервис KPI для главной страницы Dashboard.

Содержит функции для расчёта финансовых показателей
и агрегатов по заказам за выбранный период.
"""
import logging
from dataclasses import dataclass, field

from django.db import models
from django.db.models import Sum, Count, Q

from apps.accounting.models import Finance, FinancialTransactions
from apps.logistics.models import Order, OrderItem, CourierShift, CourierTrip
from apps.products.models import Product
from apps.warehouse.models import WarehouseStockBalance
from apps.dashboard.services.filters import Period
from apps.dashboard.services.historical import (
    get_historical_totals, should_include_historical,
)

logger = logging.getLogger(__name__)

STOCK_CRITICAL_THRESHOLD = 10


@dataclass
class OverviewData:
    """Все данные для главной страницы Dashboard."""
    # Финансы
    income: int = 0
    consumption: int = 0
    profit: int = 0
    card_profit: int = 0
    cash_deliveries: int = 0

    # Заказы
    orders_created: int = 0
    orders_delivered: int = 0
    orders_pending: int = 0
    orders_cancelled: int = 0
    units_sold: int = 0

    # Исторические показатели «За всё время» (добавляются только в режиме all)
    historical_orders_created_total: int = 0
    historical_water_sold_total: int = 0
    historical_included: bool = False

    # Активная работа
    active_shifts_count: int = 0
    active_trips_count: int = 0
    unassigned_orders_count: int = 0
    critical_stock_count: int = 0

    # Таблицы
    active_shifts: list = field(default_factory=list)
    recent_orders: list = field(default_factory=list)
    top_products: list = field(default_factory=list)
    top_couriers: list = field(default_factory=list)
    stock_alerts: list = field(default_factory=list)


def _finance_kpi(period: Period) -> dict:
    """Финансовые KPI: доход, расход, прибыль, безнал, наличные по доставкам."""
    result = {
        'income': 0,
        'consumption': 0,
        'profit': 0,
        'card_profit': 0,
        'cash_deliveries': 0,
    }

    if period.is_empty:
        return result

    # Агрегация Finance за период
    finance_qs = Finance.objects.filter(
        date__gte=period.date_from,
        date__lte=period.date_to,
    ).aggregate(
        total_income=Sum('income'),
        total_consumption=Sum('consumption'),
        total_profit=Sum('profit'),
        total_card=Sum('card_profit'),
    )
    result['income'] = finance_qs['total_income'] or 0
    result['consumption'] = finance_qs['total_consumption'] or 0
    result['profit'] = finance_qs['total_profit'] or 0
    result['card_profit'] = finance_qs['total_card'] or 0

    # Наличные по доставкам: сумма OrderItem.price для DELIVERED + CASH за период
    cash_qs = OrderItem.objects.filter(
        order__status=Order.Status.DELIVERED,
        order__payment_type=Order.PaymentType.CASH,
        order__delivered_at__date__gte=period.date_from,
        order__delivered_at__date__lte=period.date_to,
    ).aggregate(total=Sum('price'))
    result['cash_deliveries'] = cash_qs['total'] or 0

    return result


def _orders_kpi(period: Period) -> dict:
    """KPI по заказам: создано, доставлено, ожидает, отменено, продано единиц."""
    result = {
        'orders_created': 0,
        'orders_delivered': 0,
        'orders_pending': 0,
        'orders_cancelled': 0,
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
        # Создано за период (по created_at)
        result['orders_created'] = Order.objects.filter(
            created_at__date__gte=period.date_from,
            created_at__date__lte=period.date_to,
        ).count()

        # Доставлено за период (по delivered_at)
        result['orders_delivered'] = Order.objects.filter(
            status=Order.Status.DELIVERED,
            delivered_at__date__gte=period.date_from,
            delivered_at__date__lte=period.date_to,
        ).count()

        # Отменено — используем created_at (нет cancelled_at)
        result['orders_cancelled'] = Order.objects.filter(
            status=Order.Status.CANCELLED,
            created_at__date__gte=period.date_from,
            created_at__date__lte=period.date_to,
        ).count()

        # Продано единиц товара (сумма quantity по доставленным заказам за период)
        units = OrderItem.objects.filter(
            order__status=Order.Status.DELIVERED,
            order__delivered_at__date__gte=period.date_from,
            order__delivered_at__date__lte=period.date_to,
        ).aggregate(total=Sum('quantity'))
        result['units_sold'] = units['total'] or 0

    # Pending — всегда текущее состояние (без периода)
    result['orders_pending'] = Order.objects.filter(
        status=Order.Status.PENDING,
    ).count()

    return result


def _active_work() -> dict:
    """Показатели «Сейчас в работе» (без периода — текущее состояние)."""
    active_shifts_count = CourierShift.objects.filter(
        status=CourierShift.Status.OPEN,
    ).count()

    active_trips_count = CourierTrip.objects.filter(
        status=CourierTrip.Status.ACTIVE,
    ).count()

    orders_pending = Order.objects.filter(
        status=Order.Status.PENDING,
    ).count()

    unassigned = Order.objects.filter(
        status=Order.Status.PENDING,
        assigned_courier__isnull=True,
    ).count()

    critical = WarehouseStockBalance.objects.filter(
        quantity__lt=STOCK_CRITICAL_THRESHOLD,
    ).count()

    return {
        'active_shifts_count': active_shifts_count,
        'active_trips_count': active_trips_count,
        'orders_pending': orders_pending,
        'unassigned_orders_count': unassigned,
        'critical_stock_count': critical,
    }


def _active_shifts_table() -> list:
    """Таблица активных смен с агрегированными данными."""
    shifts = CourierShift.objects.filter(
        status=CourierShift.Status.OPEN,
    ).select_related('courier').order_by('courier__full_name')

    rows = []
    for shift in shifts:
        # Количество доставленных заказов сегодня
        delivered_today = Order.objects.filter(
            trip__shift=shift,
            status=Order.Status.DELIVERED,
        ).count()

        # Информация о текущем рейсе
        active_trip = shift.trips.filter(
            status=CourierTrip.Status.ACTIVE,
        ).first()

        rows.append({
            'id': shift.id,
            'courier_name': shift.courier.full_name if shift.courier else '—',
            'opened_at': shift.opened_at,
            'trip_info': f'Рейс №{active_trip.id}' if active_trip else '—',
            'delivered_today': delivered_today,
            'cash_total': shift.cash_total,
            'card_total': shift.card_total,
        })
    return rows


def _recent_orders(period: Period, limit: int = 20) -> list:
    """Последние заказы за период."""
    if period.is_empty:
        return []

    orders = Order.objects.filter(
        created_at__date__gte=period.date_from,
        created_at__date__lte=period.date_to,
    ).select_related(
        'client', 'assigned_courier', 'trip__shift__courier',
        'delivery_address',
    ).prefetch_related(
        'items__product',
    ).order_by('-created_at')[:limit]

    rows = []
    for o in orders:
        # Курьер: приоритет trip.shift.courier, fallback assigned_courier
        courier = None
        if o.trip and o.trip.shift:
            courier = o.trip.shift.courier
        elif o.assigned_courier:
            courier = o.assigned_courier

        rows.append({
            'id': o.id,
            'display_number': o.human_number,
            'created_at': o.created_at,
            'client_name': o.client.name if o.client else '—',
            'address': o.display_address(),
            'courier_name': courier.full_name if courier else '—',
            'trip_id': o.trip.id if o.trip else None,
            'total_price': o.get_total_price(),
            'payment_type': o.payment_type,
            'payment_type_display': o.get_payment_type_display(),
            'status': o.status,
            'status_display': o.get_status_display(),
        })
    return rows


def _top_products(period: Period, limit: int = 5) -> list:
    """Топ-N товаров по количеству проданных единиц за период."""
    if period.is_empty:
        return []

    products = (
        OrderItem.objects
        .filter(
            order__status=Order.Status.DELIVERED,
            order__delivered_at__date__gte=period.date_from,
            order__delivered_at__date__lte=period.date_to,
        )
        .values('product__name', 'product_id')
        .annotate(
            sold=Sum('quantity'),
            revenue=Sum('price'),
        )
        .order_by('-sold')[:limit]
    )

    return [
        {
            'name': p['product__name'],
            'sold': p['sold'] or 0,
            'revenue': p['revenue'] or 0,
        }
        for p in products
    ]


def _top_couriers(period: Period, limit: int = 5) -> list:
    """Топ-N курьеров по количеству доставленных заказов за период."""
    if period.is_empty:
        return []

    # Курьер определяется через trip.shift.courier
    couriers = (
        Order.objects
        .filter(
            status=Order.Status.DELIVERED,
            delivered_at__date__gte=period.date_from,
            delivered_at__date__lte=period.date_to,
            trip__isnull=False,
        )
        .values(
            courier_id=models.F('trip__shift__courier__id'),
            courier_name=models.F('trip__shift__courier__full_name'),
        )
        .annotate(
            delivered=Count('id'),
            revenue=Sum('items__price'),
            trips=Count('trip', distinct=True),
        )
        .order_by('-delivered')[:limit]
    )

    return [
        {
            'name': c['courier_name'],
            'delivered': c['delivered'],
            'revenue': c['revenue'] or 0,
            'trips': c['trips'],
        }
        for c in couriers
    ]


def _stock_alerts() -> list:
    """Критические остатки склада (quantity < порога)."""
    alerts = WarehouseStockBalance.objects.filter(
        quantity__lt=STOCK_CRITICAL_THRESHOLD,
    ).select_related('warehouse_product').order_by('quantity')

    return [
        {
            'product_name': a.warehouse_product.name,
            'quantity': a.quantity,
        }
        for a in alerts
    ]


def get_overview(period: Period) -> OverviewData:
    """Собрать все данные для главной страницы Dashboard."""
    data = OverviewData()

    # Финансы
    fin = _finance_kpi(period)
    data.income = fin['income']
    data.consumption = fin['consumption']
    data.profit = fin['profit']
    data.card_profit = fin['card_profit']
    data.cash_deliveries = fin['cash_deliveries']

    # Заказы
    ord_kpi = _orders_kpi(period)
    data.orders_created = ord_kpi['orders_created']
    data.orders_delivered = ord_kpi['orders_delivered']
    data.orders_pending = ord_kpi['orders_pending']
    data.orders_cancelled = ord_kpi['orders_cancelled']
    data.units_sold = ord_kpi['units_sold']

    # Исторические показатели «За всё время» — только в режиме all
    if should_include_historical(period):
        hist = get_historical_totals()
        data.historical_orders_created_total = hist.orders_created_total
        data.historical_water_sold_total = hist.water_sold_total
        data.historical_included = hist.exists
        data.orders_created += hist.orders_created_total
        data.units_sold += hist.water_sold_total

    # Активная работа (текущее состояние, без периода)
    work = _active_work()
    data.active_shifts_count = work['active_shifts_count']
    data.active_trips_count = work['active_trips_count']
    data.orders_pending = work['orders_pending']
    data.unassigned_orders_count = work['unassigned_orders_count']
    data.critical_stock_count = work['critical_stock_count']

    # Таблицы
    data.active_shifts = _active_shifts_table()
    data.recent_orders = _recent_orders(period)
    data.top_products = _top_products(period)
    data.top_couriers = _top_couriers(period)
    data.stock_alerts = _stock_alerts()

    return data