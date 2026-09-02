"""
Celery-задачи для уведомлений Telegram (bot_bridge).

Все задачи принимают ID объектов, а не сами объекты — Celery сериализует
только простые типы (int, str, dict). Объекты загружаются из БД внутри задачи.

Запуск воркера:
    celery -A WERP_system worker --loglevel=info
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_message_task(self, chat_id: int, text: str, parse_mode='HTML'):
    """Отправка сообщения в Telegram через Bot API (в фоне).

    При ошибке сети — повторная попытка до 3 раз с задержкой 30 сек.
    """
    from apps.bot_bridge.notify import send_telegram_message

    try:
        return send_telegram_message(chat_id, text, parse_mode=parse_mode)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка отправки сообщения в chat_id %s: %s", chat_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_client_order_accepted_task(self, order_id: int):
    """Уведомление клиенту, что курьер принял заказ."""
    from apps.logistics.models import Order

    try:
        order = Order.objects.select_related('client', 'assigned_courier').get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Заказ %s не найден для уведомления клиенту", order_id)
        return False

    from apps.bot_bridge.notify import notify_client_order_accepted
    try:
        return notify_client_order_accepted(order)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка уведомления клиенту по заказу %s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_client_order_delivered_task(self, order_id: int):
    """Уведомление клиенту о доставке заказа."""
    from apps.logistics.models import Order

    try:
        order = Order.objects.select_related('client').get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Заказ %s не найден для уведомления о доставке", order_id)
        return False

    from apps.bot_bridge.notify import notify_client_order_delivered
    try:
        return notify_client_order_delivered(order)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка уведомления о доставке по заказу %s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_courier_new_order_task(self, courier_tg_id: int, order_id: int):
    """Уведомление курьеру о новом заказе в пуле."""
    from apps.logistics.models import Order

    try:
        order = Order.objects.select_related('client').get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Заказ %s не найден для уведомления курьеру", order_id)
        return False

    from apps.bot_bridge.notify import notify_courier_new_order
    try:
        return notify_courier_new_order(courier_tg_id, order)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка уведомления курьеру по заказу %s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_admin_alert_task(self, text: str, admin_tg_id: int = None):
    """Отправка алерта администратору."""
    from apps.bot_bridge.notify import notify_admin_alert
    try:
        return notify_admin_alert(text, admin_tg_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка отправки алерта администратору: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_trip_closed_task(self, trip_id: int):
    """Отчёт о закрытии рейса всем владельцам (в фоне).

    Тяжёлый расчёт get_trip_summary() + отправка всем OWNER — не блокирует
    ответ курьеру при закрытии рейса.
    """
    from apps.logistics.models import CourierTrip

    try:
        trip = CourierTrip.objects.select_related('shift__courier').get(pk=trip_id)
    except CourierTrip.DoesNotExist:
        logger.warning("Рейс %s не найден для отчёта о закрытии", trip_id)
        return False

    from apps.bot_bridge.reports import notify_trip_closed
    try:
        return notify_trip_closed(trip)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка отчёта о закрытии рейса %s: %s", trip_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_shift_closed_task(self, shift_id: int):
    """Отчёт о закрытии смены всем владельцам (в фоне)."""
    from apps.logistics.models import CourierShift

    try:
        shift = CourierShift.objects.select_related('courier').get(pk=shift_id)
    except CourierShift.DoesNotExist:
        logger.warning("Смена %s не найдена для отчёта о закрытии", shift_id)
        return False

    from apps.bot_bridge.reports import notify_shift_closed
    try:
        return notify_shift_closed(shift)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка отчёта о закрытии смены %s: %s", shift_id, exc)
        raise self.retry(exc=exc)