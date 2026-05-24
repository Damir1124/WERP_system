from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # CourierShift
    path('shifts/', views.ShiftListView.as_view(), name='shift-list'),
    path('shifts/<int:pk>/', views.ShiftDetailView.as_view(), name='shift-detail'),
    path('shifts/<int:pk>/close/', views.ShiftCloseView.as_view(), name='shift-close'),

    # CourierTrip
    path('trips/', views.TripListView.as_view(), name='trip-list'),
    path('trips/<int:pk>/', views.TripDetailView.as_view(), name='trip-detail'),
    path('trips/<int:pk>/summary/', views.TripSummaryView.as_view(), name='trip-summary'),
    path('trips/<int:pk>/close/', views.TripCloseView.as_view(), name='trip-close'),

    # Order
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/deliver/', views.OrderDeliverView.as_view(), name='order-deliver'),
]