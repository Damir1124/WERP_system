"""
Сервис для страницы «Склад» (/dashboard/stock/).

Содержит функции для остатков и движений склада.
"""
import logging
from dataclasses import dataclass, field

from apps.warehouse.models import WarehouseStockBalance, WarehouseStockMovement
from apps.dashboard.services.filters import Period

logger = logging.getLogger(__name__)

CRITICAL_THRESHOLD = 10  # общий критический порог
WARNING_THRESHOLD = 20   # порог «близок к критическому»


@dataclass
class StockRow:
    """Строка остатков склада."""
    product_id: int
    name: str
    category: str
    category_display: str
    quantity: int = 0
    last_received: str | None = None
    last_departure: str | None = None
    status: str = 'Норма'       # critical / warning / normal
    status_css: str = 'success'


def _status_css(quantity: int) -> tuple[str, str]:
    """Вернуть (label, css_class) для статуса остатка."""
    if quantity < CRITICAL_THRESHOLD:
        return 'Критический', 'danger'
    if quantity < WARNING_THRESHOLD:
        return 'Близок к критическому', 'warning'
    return 'Норма', 'success'


def get_stock_balances() -> list:
    """Список остатков склада с подсветкой статуса."""
    balances = WarehouseStockBalance.objects.select_related('warehouse_product').order_by('warehouse_product__name')

    rows = []
    for b in balances:
        wp = b.warehouse_product
        if wp is None:
            continue
        label, css = _status_css(b.quantity)

        rows.append(StockRow(
            product_id=wp.id,
            name=wp.name,
            category='',
            category_display='Складской продукт',
            quantity=b.quantity,
            last_received=b.last_received_date.isoformat() if b.last_received_date else None,
            last_departure=b.last_departure_date.isoformat() if b.last_departure_date else None,
            status=label,
            status_css=css,
        ))
    return rows


@dataclass
class MovementRow:
    """Строка движения склада."""
    date: str
    operation: str
    operation_display: str
    product_name: str
    quantity: int
    source: str = '—'
    note: str = '—'


def get_recent_movements(limit: int = 50) -> list:
    """Последние движения склада."""
    movements = WarehouseStockMovement.objects.select_related(
        'warehouse_product',
    ).order_by('-created_at', '-id')[:limit]

    rows = []
    for m in movements:
        product_name = m.warehouse_product.name if m.warehouse_product else '—'
        source = 'Приход' if m.operation_type == WarehouseStockMovement.OperationType.INCOME else 'Расход'
        rows.append(MovementRow(
            date=m.created_at.date().isoformat(),
            operation=m.operation_type,
            operation_display=m.get_operation_type_display(),
            product_name=product_name,
            quantity=m.quantity,
            source=source,
            note=m.note or '—',
        ))
    return rows