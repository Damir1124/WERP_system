"""
Модуль отчётов о закрытии рейсов и смен курьеров для Telegram.

Формирует HTML-сообщение с итогами закрытия и отправляет его в назначенный
админ-чат через send_telegram_message().

Источники данных (единый расчёт с mini-app курьера, чтобы не было расхождений):
- Рейс: CourierTrip.get_trip_summary() + агрегация OrderItem по payment_type
  (ровно как в CourierCurrentTripView, который питает Trip.jsx).
- Смена: get_shift_report() из apps/dashboard/services/reports.py
  (прямой подсчёт из OrderItem — источник истины, не кэшированные поля).
- Авто: Garage (plate_number, vehicle_name), привязанный к курьеру.
"""
import logging

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from apps.logistics.models import CourierShift, CourierTrip, Order, OrderItem
from apps.warehouse.models import Garage

logger = logging.getLogger(__name__)


def _resolve_admin_chat_ids():
    """Список chat_id получателей отчёта.

    Отчёт уходит:
    - всем сотрудникам с worker_type=OWNER и заполненным tg_id;
    - дополнительно в settings.ADMIN_CHAT_ID, если он задан (например, группа).
    Список дедуплицируется.
    """
    from apps.workers.models import Worker

    chat_ids = set()

    # Все владельцы (тип сотрудника OWNER) с tg_id
    owners = Worker.objects.filter(
        worker_type=Worker.WorkerType.OWNER,
    ).exclude(tg_id__isnull=True)
    for owner in owners:
        chat_ids.add(owner.tg_id)

    # Дополнительный явный чат (группа/пользователь) из настроек
    chat_id = getattr(settings, 'ADMIN_CHAT_ID', None)
    if chat_id:
        try:
            chat_ids.add(int(chat_id))
        except (TypeError, ValueError):
            logger.warning("ADMIN_CHAT_ID некорректен: %r", chat_id)

    if not chat_ids:
        logger.warning("Не найден получатель отчёта: нет владельцев (OWNER) с tg_id и не задан ADMIN_CHAT_ID")
    return list(chat_ids)


def _sum_delivered_price(trip, payment_type) -> int:
    """Сумма price доставленных позиций рейса по типу оплаты.

    Тот же запрос, что в CourierCurrentTripView (источник для Trip.jsx)
    и в apps/dashboard/services/reports.py — единый метод расчёта.
    """
    total = OrderItem.objects.filter(
        order__trip=trip,
        order__status=Order.Status.DELIVERED,
        order__payment_type=payment_type,
    ).aggregate(total=Sum('price'))['total']
    return total or 0


def _vehicle_info(courier) -> str:
    """Номер и название авто курьера (если в Garage привязана машина)."""
    garage = Garage.objects.filter(courier=courier).first()
    if not garage:
        return ''
    parts = []
    if garage.plate_number:
        parts.append(garage.plate_number)
    if garage.vehicle_name:
        parts.append(garage.vehicle_name)
    return ' '.join(parts)


def _fmt_num(n) -> str:
    """Формат числа с разделителями: 120000 -> '120 000'."""
    return f"{n or 0:,}".replace(",", " ")


def _fmt_dt(dt) -> str:
    """Формат даты/времени: 19.08.2026 20:45 (локальное время сервера)."""
    local = timezone.localtime(dt)
    return local.strftime("%d.%m.%Y %H:%M")


def build_trip_report_text(trip: CourierTrip) -> str:
    """HTML-текст отчёта о закрытии рейса."""
    summary = trip.get_trip_summary()
    cash = _sum_delivered_price(trip, Order.PaymentType.CASH)
    card = _sum_delivered_price(trip, Order.PaymentType.CARD)
    total = cash + card
    courier = trip.shift.courier
    vehicle = _vehicle_info(courier)
    closed_at = trip.finished_at or timezone.now()
    courier_name = courier.full_name if courier else '—'

    lines = [
        "🏁 <b>Рейс закрыт</b>",
        "",
        f"🕐 Время закрытия: {_fmt_dt(closed_at)}",
        f"🚚 Рейс: #{trip.id}",
        f"👤 Курьер: {courier_name}",
    ]
    if vehicle:
        lines.append(f"🚗 Авто: {vehicle}")
    lines += [
        "",
        "💰 <b>Финансы</b>",
        f"• Наличные: {_fmt_num(cash)} сум",
        f"• Карта: {_fmt_num(card)} сум",
        f"• Итого: {_fmt_num(total)} сум",
        f"• Продано воды: {summary['delivered']} бак",
        "",
        "📦 <b>Тара</b>",
        f"• Взято: {summary['full_loaded']} бак",
        f"• Возвращено пустых: {summary['empty_received']} шт",
        f"• Осталось в машине: {summary['full_remain']} бак",
    ]
    return "\n".join(lines)


def build_shift_report_text(shift: CourierShift) -> str:
    """HTML-текст отчёта о закрытии смены.

    Тара агрегируется по всем рейсам смены через get_trip_summary() —
    тот же метод расчёта, что в mini-app курьера.
    """
    from apps.dashboard.services.reports import get_shift_report

    report = get_shift_report(shift)
    courier = shift.courier
    vehicle = _vehicle_info(courier)
    closed_at = shift.closed_at or timezone.now()
    courier_name = courier.full_name if courier else '—'

    orders_count = Order.objects.filter(
        trip__shift=shift,
        status=Order.Status.DELIVERED,
    ).count()

    total_loaded = 0
    total_empty = 0
    total_remain = 0
    for trip in shift.trips.all():
        s = trip.get_trip_summary()
        total_loaded += s['full_loaded']
        total_empty += s['empty_received']
        total_remain += s['full_remain']

    lines = [
        "✅ <b>Смена закрыта</b>",
        "",
        f"🕐 Время закрытия: {_fmt_dt(closed_at)}",
        f"📋 Смена: #{shift.id}",
        f"👤 Курьер: {courier.full_name}",
    ]
    if vehicle:
        lines.append(f"🚗 Авто: {vehicle}")
    lines += [
        "",
        "💰 <b>Финансы</b>",
        f"• Наличные: {_fmt_num(report.total_cash)} сум",
        f"• Карта: {_fmt_num(report.total_card)} сум",
        f"• Итого: {_fmt_num(report.total_amount)} сум",
        f"• Продано воды: {report.total_water_sold} бак",
        f"• Заказов выполнено: {orders_count}",
        f"• Рейсов: {report.total_trips}",
        "",
        "📦 <b>Тара (по всем рейсам)</b>",
        f"• Взято: {total_loaded} бак",
        f"• Возвращено пустых: {total_empty} шт",
        f"• Осталось в машине: {total_remain} бак",
    ]
    return "\n".join(lines)


def _send_to_admins(text: str) -> bool:
    """Отправить текст всем получателям (владельцам + ADMIN_CHAT_ID).

    Импорт notify.py ленивый: notify.py требует requests, которого может не быть
    в окружении. Так приложение стартует без requests (как в views.py:644).
    Возвращает True, если хотя бы одно сообщение отправлено успешно.
    """
    chat_ids = _resolve_admin_chat_ids()
    if not chat_ids:
        return False

    try:
        from apps.bot_bridge.notify import send_telegram_message
    except Exception as e:  # noqa: BLE001
        logger.warning("Не удалось импортировать send_telegram_message: %s", e)
        return False

    sent_any = False
    for chat_id in chat_ids:
        try:
            if send_telegram_message(chat_id, text):
                sent_any = True
        except Exception as e:  # noqa: BLE001
            logger.warning("Ошибка отправки отчёта в chat_id %s: %s", chat_id, e)
    return sent_any


def notify_trip_closed(trip: CourierTrip) -> bool:
    """Отправить отчёт о закрытии рейса всем владельцам. True при успехе."""
    return _send_to_admins(build_trip_report_text(trip))


def notify_shift_closed(shift: CourierShift) -> bool:
    """Отправить отчёт о закрытии смены всем владельцам. True при успехе."""
    return _send_to_admins(build_shift_report_text(shift))