from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    path('stock/', views.StockBalanceListView.as_view(), name='stock-list'),
    path('stock/<int:pk>/', views.StockBalanceDetailView.as_view(), name='stock-detail'),
    path('movements/', views.StockMovementListView.as_view(), name='movement-list'),
    path('garage/', views.GarageListView.as_view(), name='garage-list'),
    path('inventory/', views.InventoryAdjustmentListView.as_view(), name='inventory-list'),
    path('waybill/<int:courier_id>/', views.WaybillGenerateView.as_view(), name='waybill-generate'),
]