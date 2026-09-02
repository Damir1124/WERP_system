from django.urls import path
from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardIndexView.as_view(), name='index'),

    # P6.3 — заказы и товары
    path('orders/', views.DashboardOrdersView.as_view(), name='orders'),
    path('products/', views.DashboardProductsView.as_view(), name='products'),

    # P6.4 — курьеры
    path('couriers/', views.DashboardCouriersView.as_view(), name='couriers'),
    path('shifts/<int:shift_id>/', views.ShiftDetailView.as_view(), name='shift_detail'),

    # P6.5 — склад и финансы
    path('stock/', views.DashboardStockView.as_view(), name='stock'),
    path('finance/', views.DashboardFinanceView.as_view(), name='finance'),

    # Отчёты по сменам за дату
    path('reports/', views.DashboardReportsView.as_view(), name='reports'),

    # CRUD: Зарплатные периоды
    path('salary-periods/', views.SalaryPeriodListView.as_view(), name='salary_period_list'),
    path('salary-periods/new/', views.SalaryPeriodCreateView.as_view(), name='salary_period_create'),
    path('salary-periods/<int:pk>/edit/', views.SalaryPeriodUpdateView.as_view(), name='salary_period_update'),
    path('salary-periods/<int:pk>/delete/', views.SalaryPeriodDeleteView.as_view(), name='salary_period_delete'),

    # CRUD: Контракты
    path('contracts/', views.ContractListView.as_view(), name='contract_list'),
    path('contracts/new/', views.ContractCreateView.as_view(), name='contract_create'),
    path('contracts/<int:pk>/edit/', views.ContractUpdateView.as_view(), name='contract_update'),
    path('contracts/<int:pk>/delete/', views.ContractDeleteView.as_view(), name='contract_delete'),

    # CRUD: Рассрочки
    path('installments/', views.InstallmentListView.as_view(), name='installment_list'),
    path('installments/new/', views.InstallmentCreateView.as_view(), name='installment_create'),
    path('installments/<int:pk>/edit/', views.InstallmentUpdateView.as_view(), name='installment_update'),
    path('installments/<int:pk>/delete/', views.InstallmentDeleteView.as_view(), name='installment_delete'),
]