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
    
    # Telegram Mini App (TWA) endpoints
    path('twa/products/', views.PublicProductListView.as_view(), name='twa_product_list'),
    path('twa/order/', views.ClientOrderView.as_view(), name='twa_create_order'),
    
    # Клиентский Mini App (3.3)
    path('client/products/', views.ClientProductListView.as_view(), name='client_products'),
    path('client/order/', views.ClientOrderCreateView.as_view(), name='client_order_create'),
    path('client/orders/', views.ClientOrderHistoryView.as_view(), name='client_orders'),
    path('client/order/<int:order_id>/status/', views.ClientOrderStatusView.as_view(), name='client_order_status'),
    
    # Новые эндпоинты для моделей P0
    path('courier/shifts/', views.CourierShiftListView.as_view(), name='courier_shifts'),
    path('courier/trips/', views.CourierTripListView.as_view(), name='courier_trips'),
    path('courier/trips/<int:trip_id>/orders/', views.OrderListView.as_view(), name='trip_orders'),
    path('courier/orders/confirm/', views.OrderConfirmationView.as_view(), name='order_confirmation'),
    path('courier/orders/update-quantity/', views.OrderQuantityUpdateView.as_view(), name='order_update_quantity'),
    path('courier/orders/create/', views.CreateOrderView.as_view(), name='create_order'),
    
    # Идентификация пользователя по Telegram ID (для бота)
    path('identify/', views.IdentifyView.as_view(), name='identify'),
    
    # Новые API endpoints для курьерского Mini App (3.2)
    path('courier/pool/', views.CourierPoolView.as_view(), name='courier_pool'),  # GET - список, POST - взять заказ
    path('courier/pool/<int:order_id>/assign/', views.CourierPoolView.as_view(), name='courier_assign_order'),
    path('courier/trip/current/', views.CourierCurrentTripView.as_view(), name='courier_current_trip'),
    path('courier/colleagues/', views.CourierColleaguesView.as_view(), name='courier_colleagues'),

    # Новые API endpoints для admin-профиля (3.4)
    path('admin/stats/today/', views.AdminStatsTodayView.as_view(), name='admin_stats_today'),
    path('admin/shifts/', views.AdminShiftsView.as_view(), name='admin_shifts'),
    path('admin/stock/alerts/', views.AdminStockAlertsView.as_view(), name='admin_stock_alerts'),
    path('admin/orders/recent/', views.AdminOrdersRecentView.as_view(), name='admin_orders_recent'),
]