from django.urls import path
from apps.bot_bridge import views

app_name = 'bot_bridge'

urlpatterns = [
    # Профиль курьера
    path('courier/profile/', views.CourierProfileView.as_view(), name='courier_profile'),
    
    # Доставки
    path('courier/deliveries/', views.CourierDeliveryListView.as_view(), name='courier_deliveries'),
    path('courier/deliveries/today/', views.TodayDeliveriesView.as_view(), name='today_deliveries'),
    path('courier/deliveries/<int:delivery_id>/mark-delivered/', 
         views.MarkAsDeliveredView.as_view(), name='mark_delivered'),
    
    # Подтверждение доставки
    path('courier/deliveries/confirm/', views.DeliveryConfirmationView.as_view(), name='confirm_delivery'),
    
    # Изменение количества
    path('courier/deliveries/update-quantity/', views.UpdateQuantityView.as_view(), name='update_quantity'),
    
    # Каталог продуктов
    path('products/', views.ProductListView.as_view(), name='product_list'),
    
    # Информация о клиентах
    path('clients/', views.ClientInfoView.as_view(), name='client_info'),
]