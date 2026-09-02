"""
Сервис исторических показателей «до запуска WERP».

Содержит единственную точку доступа к стартовым итогам из старой системы:
- historical_orders_created_total — общее количество созданных заказов;
- historical_water_sold_total — общее количество проданной основной воды.

Эти значения прибавляются ТОЛЬКО к показателям «За всё время» (period.mode == 'all')
и НЕ влияют на today / yesterday / week / month / custom / смены / рейсы / кассу / финансы / склад.
"""
from dataclasses import dataclass
from datetime import date

from apps.accounting.models import HistoricalStats


@dataclass(frozen=True)
class HistoricalTotals:
    """Снимок исторических итогов."""
    orders_created_total: int = 0
    water_sold_total: int = 0
    werp_start_date: date | None = None
    source: str = ''
    exists: bool = False


def get_historical_totals() -> HistoricalTotals:
    """Вернуть единственную активную историческую базу (или пустую, если её нет)."""
    obj = HistoricalStats.objects.first()
    if obj is None:
        return HistoricalTotals()
    return HistoricalTotals(
        orders_created_total=obj.historical_orders_created_total,
        water_sold_total=obj.historical_water_sold_total,
        werp_start_date=obj.werp_start_date,
        source=obj.source,
        exists=True,
    )


def should_include_historical(period) -> bool:
    """
    Исторические показатели добавляются только в режиме «За всё время» (all).
    Для today / yesterday / week / month / custom — False.
    """
    return getattr(period, 'mode', None) == 'all'