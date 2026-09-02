"""
Сервис отчётов по сменам курьеров (apps/dashboard/services/reports.py).

Строит иерархический отчёт «смена → рейсы → заказы → позиции» для выбранной даты.

Данные вычисляются на лету из существующих моделей
(CourierShift / CourierTrip / Order / OrderItem), поэтому отчёт всегда актуален
и не требует хранения снимков или дополнительных миграций.

Структура отчёта:
1. Сводка смены: продано воды (тип WATER), число рейсов, наличные, карта.
2. Рейсы: взято воды, привезено пустых, остаток (формат как в mini-app курьера).
3. Оплата по рейсу: наличные / карта (только по DELIVERED заказам).
4. Заказы рейса: номер, адрес, тип оплаты, сумма, позиции (наименование, кол-во, сумма).
"""
import logging
from dataclasses import dataclass, field

from django.db.models import Sum

from apps.logistics.models import CourierShift, Order, OrderItem
from apps.products.models import Product

logger = logging.getLogger(__name__)


@dataclass
class ReportItem:
    """Позиция заказа в отчёте."""
    product_name: str
    quantity: int
    sum: int


@dataclass
class ReportOrder:
    """Заказ в отчёте."""
    id: int
    display_number: str
    address: str
    payment_type: str
    payment_type_display: str
    status: str
    status_display: str
    total_amount: int
    items: list = field(default_factory=list)


@dataclass
class ReportTrip:
    """Рейс в отчёте."""
    id: int
    status: str
    started_at: str
    finished_at: str | None
    water_taken: int = 0      # взято воды (full_loaded)
    empty_returned: int = 0   # привезено пустых (empty_received)
    remaining: int = 0        # остаток (full_remain)
    cash_amount: int = 0      # наличные по рейсу
    card_amount: int = 0      # карта по рейсу
    orders: list = field(default_factory=list)


@dataclass
class ShiftReport:
    """Отчёт по одной смене."""
    id: int
    courier_name: str
    date: str
    status: str
    status_display: str
    opened_at: str
    closed_at: str | None
    total_water_sold: int = 0
    total_trips: int = 0
    total_cash: int = 0
    total_card: int = 0
    trips: list = field(default_factory=list)

    @property
    def total_amount(self) -> int:
        """Итоговая выручка смены (наличные + карта)."""
        return self.total_cash + self.total_card


def _sum_delivered_price(trip, payment_type) -> int:
    """Сумма price доставленных позиций рейса по типу оплаты."""
    total = OrderItem.objects.filter(
        order__trip=trip,
        order__status=Order.Status.DELIVERED,
        order__payment_type=payment_type,
    ).aggregate(total=Sum('price'))['total']
    return total or 0


def _sum_delivered_price_for_shift(shift, payment_type) -> int:
    """Сумма price доставленных позиций смены по типу оплаты.

    Считаем напрямую из OrderItem (источник истины), а не из кэшированных
    полей CourierShift.cash_total/card_total — так отчёт всегда точен,
    даже если сигнал пересчёта ещё не отработал.
    """
    total = OrderItem.objects.filter(
        order__trip__shift=shift,
        order__status=Order.Status.DELIVERED,
        order__payment_type=payment_type,
    ).aggregate(total=Sum('price'))['total']
    return total or 0


def _build_trip(trip) -> ReportTrip:
    """Собрать рейс: сводка тары + оплата + заказы."""
    summary = trip.get_trip_summary()

    report_trip = ReportTrip(
        id=trip.id,
        status=trip.status,
        started_at=trip.started_at.isoformat() if trip.started_at else '',
        finished_at=trip.finished_at.isoformat() if trip.finished_at else None,
        water_taken=summary['full_loaded'],
        empty_returned=summary['empty_received'],
        remaining=summary['full_remain'],
        cash_amount=_sum_delivered_price(trip, Order.PaymentType.CASH),
        card_amount=_sum_delivered_price(trip, Order.PaymentType.CARD),
    )

    orders = Order.objects.filter(trip=trip).select_related(
        'client', 'delivery_address',
    ).prefetch_related('items__product').order_by('created_at')

    for o in orders:
        items = [
            ReportItem(
                product_name=item.product.name,
                quantity=item.quantity,
                sum=item.price or 0,
            )
            for item in o.items.all()
        ]
        report_trip.orders.append(ReportOrder(
            id=o.id,
            display_number=o.human_number,
            address=o.display_address(),
            payment_type=o.payment_type,
            payment_type_display=o.get_payment_type_display(),
            status=o.status,
            status_display=o.get_status_display(),
            total_amount=o.get_total_price(),
            items=items,
        ))

    return report_trip


def get_shift_report(shift: CourierShift) -> ShiftReport:
    """Построить отчёт по одной смене."""
    # Продано воды (тип WATER) по доставленным заказам смены
    water_sold = OrderItem.objects.filter(
        order__trip__shift=shift,
        order__status=Order.Status.DELIVERED,
        product__type_product=Product.TypeProduct.WATER,
    ).aggregate(total=Sum('quantity'))['total'] or 0

    report = ShiftReport(
        id=shift.id,
        courier_name=shift.courier.full_name if shift.courier else '—',
        date=shift.date.isoformat(),
        status=shift.status,
        status_display=shift.get_status_display(),
        opened_at=shift.opened_at.isoformat() if shift.opened_at else '',
        closed_at=shift.closed_at.isoformat() if shift.closed_at else None,
        total_water_sold=water_sold,
        total_trips=shift.trips.count(),
        total_cash=_sum_delivered_price_for_shift(shift, Order.PaymentType.CASH),
        total_card=_sum_delivered_price_for_shift(shift, Order.PaymentType.CARD),
    )

    trips = shift.trips.all().order_by('started_at')
    for trip in trips:
        report.trips.append(_build_trip(trip))

    return report


def get_reports_for_date(date) -> list:
    """Отчёты по всем сменам за указанную дату.

    Возвращает список ShiftReport, отсортированный по курьеру и времени открытия.
    """
    shifts = CourierShift.objects.filter(date=date).select_related('courier').order_by(
        'courier__full_name', 'opened_at',
    )
    return [get_shift_report(shift) for shift in shifts]
