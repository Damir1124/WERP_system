from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.ClientListView.as_view(), name='client-list'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('<int:pk>/orders/', views.ClientOrderHistoryView.as_view(), name='client-orders'),
    
    # Новые эндпоинты для работы с адресами
    path('addresses/<str:phone>/', views.get_client_addresses, name='client-addresses'),
    path('addresses/save/', views.save_client_address, name='save-client-address'),
]