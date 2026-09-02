"""
Модуль уведомлений для Telegram-бота.
Отправляет уведомления клиентам и курьерам через Telegram Bot API.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
if not TELEGRAM_BOT_TOKEN:
    # Попробуем получить из переменных окружения
    import os
    TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN')

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"


def send_telegram_message(chat_id: int, text: str, parse_mode='HTML', disable_web_page_preview=True):
    """
    Отправляет сообщение в Telegram через Bot API.
    Возвращает True при успехе, False при ошибке.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не настроен, уведомления не отправляются")
        return False
    if not chat_id:
        logger.warning("Не указан chat_id для отправки уведомления")
        return False

    url = TELEGRAM_API_URL + "sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': disable_web_page_preview,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.debug(f"Уведомление отправлено в chat_id {chat_id}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка отправки уведомления в Telegram: {e}")
        return False


def notify_client_order_accepted(order):
    """
    Отправляет tg-уведомление клиенту когда курьер взял заказ.
    
    Текст уведомления:
    Курьер принял ваш заказ:
      Курьер: Иван Иванов
      Телефон: +998901234567
      Заказ: Вода 20л × 2 шт.
      Статус: В пути 🚚
    """
    if not order.client or not order.client.tg_id:
        logger.warning(f"У заказа {order.id} нет клиента или tg_id, уведомление не отправлено")
        return False

    courier_info = ""
    if order.assigned_courier:
        courier_info = f"Курьер: {order.assigned_courier.full_name}\n"
        phone = getattr(order.assigned_courier, 'phone', None)
        if phone:
            courier_info += f"Телефон: {phone}\n"
    else:
        courier_info = "Курьер будет назначен в ближайшее время\n"

    # Собираем позиции из OrderItem (поля product/quantity перенесены туда)
    items = order.items.select_related('product').all()
    if items:
        items_str = ", ".join(f"{i.product.name} × {i.quantity} шт." for i in items)
    else:
        items_str = "Неизвестный товар"

    text = (
        f"✅ <b>Курьер принял ваш заказ</b>\n\n"
        f"{courier_info}"
        f"Заказ: {items_str}\n"
        f"Статус: В пути 🚚\n\n"
        f"Номер заказа: {order.human_number}"
    )
    return send_telegram_message(order.client.tg_id, text)


def notify_client_order_delivered(order):
    """
    Уведомление клиенту о доставке заказа.
    """
    if not order.client or not order.client.tg_id:
        logger.warning(f"У заказа {order.id} нет клиента или tg_id, уведомление не отправлено")
        return False

    # Собираем позиции из OrderItem
    items = order.items.select_related('product').all()
    if items:
        items_str = ", ".join(f"{i.product.name} × {i.quantity} шт." for i in items)
    else:
        items_str = "Неизвестный товар"
    total_price = order.get_total_price()

    text = (
        f"🎉 <b>Ваш заказ доставлен!</b>\n\n"
        f"Заказ: {items_str}\n"
        f"Сумма: {total_price} сум\n"
        f"Спасибо за покупку!\n\n"
        f"Номер заказа: {order.human_number}"
    )
    return send_telegram_message(order.client.tg_id, text)


def notify_courier_new_order(courier_tg_id: int, order):
    """
    Уведомление курьеру о новом заказе в пуле (если используется пул заказов).
    """
    if not courier_tg_id:
        logger.warning("Не указан tg_id курьера для уведомления")
        return False

    client_name = order.client.name if order.client else "Неизвестный клиент"
    # Используем снимок адреса из заказа (не зависит от удалённого ClientAddress)
    address = order.display_address()

    # Собираем позиции из OrderItem
    items = order.items.select_related('product').all()
    if items:
        items_str = ", ".join(f"{i.product.name} × {i.quantity} шт." for i in items)
    else:
        items_str = "Неизвестный товар"

    text = (
        f"📦 <b>Новый заказ</b>\n\n"
        f"Клиент: {client_name}\n"
        f"Адрес: {address}\n"
        f"Товар: {items_str}\n\n"
        f"Заберите заказ из пула."
    )
    return send_telegram_message(courier_tg_id, text)


def notify_admin_alert(text: str, admin_tg_id: int = None):
    """
    Отправляет алерт администратору.
    Если admin_tg_id не указан, пытается получить из настроек или из модели Worker с is_admin=True.
    """
    if not admin_tg_id:
        # Попробуем найти администратора в базе
        from apps.workers.models import Worker
        admin = Worker.objects.filter(is_admin=True).first()
        if admin and admin.tg_id:
            admin_tg_id = admin.tg_id
        else:
            logger.warning("Не найден администратор с tg_id для отправки алерта")
            return False
    
    return send_telegram_message(admin_tg_id, f"⚠️ <b>Алерт:</b>\n{text}")


def notify_owner_installment_reminder(installment):
    """
    Отправляет напоминание владельцу (owner) о предстоящем взносе по рассрочке.

    Отправляется всем сотрудникам с worker_type=OWNER и tg_id.
    Текст содержит: клиент, телефон, продукты, сумму, долг, дату платежа,
    и кто оформил рассрочку (курьер/сотрудник).
    """
    from apps.workers.models import Worker

    if not installment.client:
        logger.warning(f"У рассрочки {installment.id} нет клиента, напоминание не отправлено")
        return False

    # Собираем позиции
    items = installment.items.select_related('product').all()
    if items:
        items_str = ", ".join(f"{i.product.name} × {i.quantity} шт." for i in items)
    else:
        items_str = "Неизвестный товар"

    # Кто оформил
    issued_by = installment.issued_by.full_name if installment.issued_by else "Не указан"

    # Номер заказа, если рассрочка по заказу
    order_info = ""
    if installment.order:
        order_info = f"\nЗаказ: №{installment.order.human_number}"

    text = (
        f"💳 <b>Напоминание о взносе по рассрочке</b>\n\n"
        f"👤 Клиент: {installment.client.name}\n"
        f"📞 Телефон: {installment.client.phone}\n"
        f"🛒 Продукты: {items_str}\n"
        f"💰 Сумма рассрочки: {installment.amount} сум\n"
        f"💵 Оплачено: {installment.paid_amount} сум\n"
        f"📉 Остаток долга: {installment.debt} сум\n"
        f"📅 Дата платежа: {installment.due_date}\n"
        f"👤 Оформил: {issued_by}"
        f"{order_info}\n\n"
        f"Не забудьте взять взнос с клиента вовремя!"
    )

    # Отправляем всем владельцам
    owners = Worker.objects.filter(worker_type=Worker.WorkerType.OWNER, tg_id__isnull=False)
    sent = False
    for owner in owners:
        if send_telegram_message(owner.tg_id, text):
            sent = True

    if not sent:
        logger.warning(f"Не найдено владельцев с tg_id для напоминания по рассрочке {installment.id}")
    return sent