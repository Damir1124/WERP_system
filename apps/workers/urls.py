from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('', views.WorkerListView.as_view(), name='worker-list'),
    path('<int:pk>/', views.WorkerDetailView.as_view(), name='worker-detail'),
    path('<int:pk>/salary/', views.WorkerSalaryView.as_view(), name='worker-salary'),
]