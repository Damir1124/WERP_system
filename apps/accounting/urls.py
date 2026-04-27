from django.urls import path
from apps.accounting import views

app_name = 'accounting'

urlpatterns = [
    # Основная информация о зарплате курьера
    path('salary/', views.SalaryDetailView.as_view(), name='salary_detail'),
    
    # Сводка по зарплате за текущий месяц
    path('salary/summary/', views.SalarySummaryView.as_view(), name='salary_summary'),
    
    # Список всех платежей по зарплате
    path('salary/payments/', views.SalaryPaymentsListView.as_view(), name='salary_payments'),
    
    # Последние бонусы
    path('salary/bonuses/', views.RecentBonusesView.as_view(), name='recent_bonuses'),
    
    # Последние штрафы
    path('salary/fines/', views.RecentFinesView.as_view(), name='recent_fines'),
]