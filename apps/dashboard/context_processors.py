"""
Контекстные процессоры для административной панели.

Добавляют счётчики записей на главную страницу Admin (/admin/),
чтобы диспетчер сразу видел масштаб данных без перехода в список.
"""


def admin_dashboard_counts(request):
    """Счётчики ключевых сущностей для главной страницы Admin."""
    counts = {}

    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return counts

    from apps.logistics.models import Order, CourierShift
    from apps.clients.models import Client
    from apps.products.models import Product
    from apps.workers.models import Worker
    from apps.warehouse.models import Garage
    from apps.accounting.models import SalaryPeriod, Contract, Installment

    counts['order_count'] = Order.objects.count()
    counts['shift_count'] = CourierShift.objects.count()
    counts['client_count'] = Client.objects.count()
    counts['product_count'] = Product.objects.count()
    counts['worker_count'] = Worker.objects.count()
    counts['garage_count'] = Garage.objects.count()
    counts['salaryperiod_count'] = SalaryPeriod.objects.count()
    counts['contract_count'] = Contract.objects.count()
    counts['installment_count'] = Installment.objects.count()

    return counts
