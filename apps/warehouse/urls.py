from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    path('garage/', views.GarageListView.as_view(), name='garage-list'),
    path('waybill/<int:courier_id>/', views.WaybillGenerateView.as_view(), name='waybill-generate'),

    # Автономный контур складских продуктов
    path('warehouse-products/', views.WarehouseProductListView.as_view(), name='warehouse-product-list'),
    path('warehouse-products/<int:pk>/', views.WarehouseProductDetailView.as_view(), name='warehouse-product-detail'),
    path('warehouse-stock/', views.WarehouseStockListView.as_view(), name='warehouse-stock-list'),
    path('warehouse-movements/', views.WarehouseMovementListView.as_view(), name='warehouse-movement-list'),
    path('warehouse-adjustments/', views.WarehouseAdjustmentListView.as_view(), name='warehouse-adjustment-list'),
    path('warehouse-mappings/', views.WarehouseMappingListView.as_view(), name='warehouse-mapping-list'),
]