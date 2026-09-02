"""
Celery-задачи для модуля Warehouse (склад).

Фоновые задачи:
- generate_waybill_task — генерация путевого листа .docx (CPU-задача)
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_waybill_task(self, courier_id: int, date_str: str):
    """Генерация путевого листа .docx для курьера за дату.

    Возвращает путь к сгенерированному файлу (или None при ошибке).
    Генерация docx — CPU-задача, выполняется в фоне, чтобы не блокировать
    HTTP-запрос.
    """
    try:
        from apps.warehouse.utils import generate_waybill
        file_path = generate_waybill(courier_id, date_str)
        logger.info("Путевой лист сгенерирован: %s", file_path)
        return file_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка генерации путевого листа (курьер %s, дата %s): %s",
                       courier_id, date_str, exc)
        raise self.retry(exc=exc)