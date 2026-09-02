"""
Сервис для страницы «Товары и тара» (/dashboard/products/).

Содержит функции для продаж по товарам и учёта тары.
"""
import logging
from dataclasses import dataclass, field

from django.db import models
from django.db.models import Sum, Count, Q

from apps.logistics.models import Order, OrderItem
from apps.products.models import Product
from apps.dashboard.services.filters import Period

logger = logging.getLogger(__name__)


@dataclass
class ProductSalesRow:
    """Строка таблицы продаж по товару."""
    product_id: int
    name: str
    category: str
    category_display: str
    sold: int = 0
    orders_count: int = 0
    revenue: int = 0
    avg_price: int = 0
    exchange_qty: int = 0
    sell_with_qty: int = 0
    defective_qty: int = 0


@dataclass
class ContainerStats:
    """Учёт тары для BOTTLE_20L."""
    water_sold: int = 0
    exchange_qty: int = 0
    sell_with_qty: int = 0
    defective_qty: int = 0


@dataclass
class ProductsPageData:
    """Все данные для страницы товаров."""
    sales: list = field(default_factory=list)
    container: ContainerStats | None = None
    type_filter: str = ''
    sort_by: str = '-sold'


def get_product_sales(period: Period, type_filter: str = '', sort_by: str = '-sold') -> list:
    """Таблица продаж по товарам за период."""
    if period.is_empty:
        return []

    # Базовый фильтр — только доставленные заказы за период
    base_filter = Q(
        order__status=Order.Status.DELIVERED,
        order__delivered_at__date__gte=period.date_from,
        order__delivered_at__date__lte=period.date_to,
    )

    # Фильтр по типу товара
    if type_filter:
        base_filter = base_filter & Q(product__type_product=type_filter)

    rows = (
        OrderItem.objects
        .filter(base_filter)
        .values(
            pid=models.F('product__id'),
            name=models.F('product__name'),
            category=models.F('product__type_product'),
        )
        .annotate(
            sold=Sum('quantity'),
            orders_count=Count('order', distinct=True),
            revenue=Sum('price'),
            exchange_qty=Sum('exchange_qty'),
            sell_with_qty=Sum('sell_with_qty'),
            defective_qty=Sum('defective_qty'),
        )
        .order_by(sort_by)
    )

    result = []
    for r in rows:
        category = r['category']
        category_display = dict(Product.TypeProduct.choices).get(category, category)
        sold = r['sold'] or 0
        revenue = r['revenue'] or 0
        result.append(ProductSalesRow(
            product_id=r['pid'],
            name=r['name'],
            category=category,
            category_display=category_display,
            sold=sold,
            orders_count=r['orders_count'] or 0,
            revenue=revenue,
            avg_price=revenue // sold if sold > 0 else 0,
            exchange_qty=r['exchange_qty'] or 0,
            sell_with_qty=r['sell_with_qty'] or 0,
            defective_qty=r['defective_qty'] or 0,
        ))

    return result


def get_container_stats(period: Period) -> ContainerStats | None:
    """Учёт тары для BOTTLE_20L за период."""
    if period.is_empty:
        return None

    items = OrderItem.objects.filter(
        order__status=Order.Status.DELIVERED,
        order__delivered_at__date__gte=period.date_from,
        order__delivered_at__date__lte=period.date_to,
        product__type_product=Product.TypeProduct.BOTTLE_20L,
    )

    stats = items.aggregate(
        water_sold=Sum('quantity'),
        exchange=Sum('exchange_qty'),
        sell_with=Sum('sell_with_qty'),
        defective=Sum('defective_qty'),
    )

    return ContainerStats(
        water_sold=stats['water_sold'] or 0,
        exchange_qty=stats['exchange'] or 0,
        sell_with_qty=stats['sell_with'] or 0,
        defective_qty=stats['defective'] or 0,
    )


def get_products_page(period: Period, type_filter: str = '', sort_by: str = '-sold') -> ProductsPageData:
    """Собрать все данные для страницы товаров."""
    data = ProductsPageData()
    data.type_filter = type_filter
    data.sort_by = sort_by
    data.sales = get_product_sales(period, type_filter, sort_by)
    data.container = get_container_stats(period)
    return data