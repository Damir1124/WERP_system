"""
Единый сервис фильтра периода для Dashboard.

Используется во всех страницах дашборда для единообразной
обработки параметров периода из GET-запроса.

Поддерживаемые режимы:
    today     — текущий день (Asia/Samarkand)
    yesterday — вчерашний день
    week      — текущая календарная неделя (пн–вс)
    month     — текущий календарный месяц
    all       — без ограничения (date_from=None, date_to=None)
    custom    — ручной date_from / date_to
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

LOCAL_TZ = 'Asia/Samarkand'


@dataclass
class Period:
    """Значение периода после разбора параметров запроса.

    Все страницы дашборда получают один объект Period и
    используют его поля для фильтрации queryset'ов.
    """
    mode: str          # today / yesterday / week / month / all / custom
    date_from: date | None
    date_to: date | None
    errors: list[str]  # сообщения об ошибках (пустой список, если всё ок)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def is_empty(self) -> bool:
        """True если период не задан (all mode)."""
        return self.date_from is None and self.date_to is None


def today_local() -> date:
    """Текущая дата в часовом поясе Asia/Samarkand (настроен в settings.py)."""
    return timezone.localdate()


def _week_boundaries(d: date) -> tuple[date, date]:
    """Понедельник и воскресенье календарной недели, содержащей d."""
    monday = d - timedelta(days=d.weekday())  # weekday(): 0=пн
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _month_boundaries(d: date) -> tuple[date, date]:
    """Первый и последний день месяца, содержащего d."""
    first = d.replace(day=1)
    if d.month == 12:
        last = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last = d.replace(month=d.month + 1, day=1) - timedelta(days=1)
    return first, last


def parse_period(get_params: dict) -> Period:
    """Разобрать параметры GET-запроса и вернуть Period.

    Параметры (из query string):
        period — today / yesterday / week / month / all
        date_from — строка YYYY-MM-DD (если period=custom или не указан)
        date_to   — строка YYYY-MM-DD

    Если period не указан — по умолчанию today.
    """
    errors: list[str] = []
    today = today_local()

    mode = get_params.get('period', 'today')
    date_from_str = get_params.get('date_from', '').strip()
    date_to_str = get_params.get('date_to', '').strip()

    # Если переданы date_from/date_to, приоритет ручного режима
    if date_from_str or date_to_str:
        mode = 'custom'

    # ── Режимы без ручных дат ──────────────────────────────────────────────
    if mode == 'today':
        return Period(mode='today', date_from=today, date_to=today, errors=[])

    if mode == 'yesterday':
        yesterday = today - timedelta(days=1)
        return Period(mode='yesterday', date_from=yesterday, date_to=yesterday, errors=[])

    if mode == 'week':
        monday, sunday = _week_boundaries(today)
        return Period(mode='week', date_from=monday, date_to=sunday, errors=[])

    if mode == 'month':
        first, last = _month_boundaries(today)
        return Period(mode='month', date_from=first, date_to=last, errors=[])

    if mode == 'all':
        return Period(mode='all', date_from=None, date_to=None, errors=[])

    # ── Ручной диапазон (custom или явно переданные date_from/date_to) ─────
    # Если переданы date_from/date_to, переключаемся в custom mode
    # вне зависимости от значения period
    if date_from_str or date_to_str:
        mode = 'custom'

    date_from: date | None = None
    date_to: date | None = None

    if date_from_str:
        try:
            date_from = date.fromisoformat(date_from_str)
        except ValueError:
            errors.append(f'Неверный формат date_from="{date_from_str}". Ожидается ГГГГ-ММ-ДД.')

    if date_to_str:
        try:
            date_to = date.fromisoformat(date_to_str)
        except ValueError:
            errors.append(f'Неверный формат date_to="{date_to_str}". Ожидается ГГГГ-ММ-ДД.')

    # Если date_from не указан, но указан date_to — берём неделю до date_to
    if date_from is None and date_to is not None:
        date_from = date_to - timedelta(days=6)

    # Если date_to не указан, но указан date_from — берём неделю после date_from
    if date_to is None and date_from is not None:
        date_to = date_from + timedelta(days=6)

    # Валидация: date_from не может быть больше date_to
    if date_from is not None and date_to is not None and date_from > date_to:
        errors.append(
            f'Дата «от» ({date_from}) больше даты «до» ({date_to}). '
            'Период не может быть отрицательным.'
        )
        # Не делаем запрос с некорректным периодом
        return Period(mode='custom', date_from=None, date_to=None, errors=errors)

    return Period(mode='custom', date_from=date_from, date_to=date_to, errors=errors)