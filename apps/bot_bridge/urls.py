from django.urls import path
from apps.bot_bridge import views
from apps.clients.views import (
    get_client_addresses,
    save_client_address,
    delete_client_address,
    update_client_profile,
)
app_name = 'bot_bridge'
urlpatterns = [
    # Корневой эндпоинт
    path('', views.APIRootView.as_view(), name='api_root'),
    # Идентификация пользователя по tg_id
    path('identify/', views.IdentifyView.as_view(), name='identify'),

    # ── Курьер: профиль ──────────────────────────────────────────────────────
    path('courier/profile/', views.CourierProfileView.as_view(), name='courier_profile'),

    # ── Курьер: смены ────────────────────────────────────────────────────────
    path('shifts/current/', views.ShiftCurrentView.as_view(), name='shift_current'),
    path('shifts/history/', views.ShiftHistoryView.as_view(), name='shift_history'),
    path('shifts/', views.CourierShiftListView.as_view(), name='shifts'),
    path('courier/shifts/', views.CourierShiftListView.as_view(), name='courier_shifts'),
    path('courier/shifts/<int:shift_id>/close/', views.CourierShiftCloseView.as_view(), name='courier_shift_close'),

    # ── Курьер: рейсы ────────────────────────────────────────────────────────
    path('trips/', views.CourierTripListView.as_view(), name='trips'),
    path('courier/trips/', views.CourierTripListView.as_view(), name='courier_trips'),
    path('courier/trips/<int:pk>/close/', views.TripCloseView.as_view(), name='trip_close'),
    path('courier/trips/<int:trip_id>/orders/', views.OrderListView.as_view(), name='trip_orders'),

    # ── Курьер: текущий рейс ─────────────────────────────────────────────────
    path('courier/trip/current/', views.CourierCurrentTripView.as_view(), name='courier_current_trip'),

    # ── Курьер: пул заказов ──────────────────────────────────────────────────
    path('courier/pool/', views.CourierPoolView.as_view(), name='courier_pool'),
    path('courier/pool/<int:order_id>/', views.CourierPoolDetailView.as_view(), name='courier_pool_detail'),
    path('courier/pool/<int:order_id>/assign/', views.CourierAssignOrderView.as_view(), name='courier_assign_order'),
    path('courier/pool/<int:order_id>/return/', views.CourierReturnToPoolView.as_view(), name='courier_return_to_pool'),

    # ── Курьер: операции с заказами ──────────────────────────────────────────
    path('courier/orders/confirm/', views.OrderConfirmationView.as_view(), name='order_confirmation'),
    path('courier/orders/update-quantity/', views.OrderQuantityUpdateView.as_view(), name='order_update_quantity'),
    path('courier/orders/create/', views.CreateOrderView.as_view(), name='create_order'),
    path('courier/orders/aggregate/', views.CourierOrdersAggregateView.as_view(), name='courier_orders_aggregate'),

    # ── Курьер: коллеги ──────────────────────────────────────────────────────
    path('courier/colleagues/', views.CourierColleaguesView.as_view(), name='courier_colleagues'),

    # ── Курьер: продукты и клиенты ───────────────────────────────────────────
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('clients/', views.ClientInfoView.as_view(), name='client_info'),
    path('clients/search/', views.ClientSearchView.as_view(), name='client_search'),
    # Адреса клиента (зарегистрированы здесь, т.к. фронтенд курьера зовёт api/bot/clients/addresses/...)
    # ВАЖНО: статические пути (save/, delete/) ДО динамического <str:phone>/,
    # иначе 'delete' будет перехвачен как номер телефона.
    path('clients/addresses/save/', save_client_address, name='save_client_address'),
    path('clients/addresses/delete/', delete_client_address, name='delete_client_address'),
    path('clients/addresses/<str:phone>/', get_client_addresses, name='client_addresses'),
    path('clients/profile/update/', update_client_profile, name='update_client_profile'),
    
    # ── Курьер: создание заказа (новый endpoint) ─────────────────────────────
    path('courier/orders/create-new/', views.CourierCreateOrderView.as_view(), name='courier_create_order'),

    # ── Клиент: Mini App ─────────────────────────────────────────────────────
    path('client/products/', views.ClientProductListView.as_view(), name='client_products'),
    path('client/order/', views.ClientOrderCreateView.as_view(), name='client_order_create'),
    path('client/orders/', views.ClientOrderHistoryView.as_view(), name='client_orders'),
    path('client/order/<int:order_id>/status/', views.ClientOrderStatusView.as_view(), name='client_order_status'),
    path('client/order/<int:order_id>/update/', views.ClientOrderUpdateView.as_view(), name='client_order_update'),
    path('client/order/<int:order_id>/delete/', views.ClientOrderDeleteView.as_view(), name='client_order_delete'),
    path('client/register/', views.ClientRegisterView.as_view(), name='client_register'),
    path('client/profile/', views.ClientProfileView.as_view(), name='client_profile'),

    # ── Оператор ─────────────────────────────────────────────────────────────
    path('operator/orders/', views.OperatorOrdersListView.as_view(), name='operator_orders'),
    path('operator/orders/<int:order_id>/', views.OperatorOrderDetailView.as_view(), name='operator_order_detail'),
    path('operator/orders/<int:order_id>/update/', views.OperatorOrderUpdateView.as_view(), name='operator_order_update'),
    path('operator/orders/<int:order_id>/delete/', views.OperatorOrderDeleteView.as_view(), name='operator_order_delete'),

    # ── Администратор ────────────────────────────────────────────────────────
    path('admin/stats/today/', views.AdminStatsTodayView.as_view(), name='admin_stats_today'),
    path('admin/shifts/', views.AdminShiftsView.as_view(), name='admin_shifts'),
    path('admin/stock/alerts/', views.AdminStockAlertsView.as_view(), name='admin_stock_alerts'),
    path('admin/orders/recent/', views.AdminOrdersRecentView.as_view(), name='admin_orders_recent'),

    # ── Owner Dashboard (Mini App) ───────────────────────────────────────────
    path('owner/stats/', views.OwnerStatsView.as_view(), name='owner_stats'),

    # ── Устаревшие (410 Gone) ────────────────────────────────────────────────
    path('courier/deliveries/', views.CourierDeliveryListView.as_view(), name='courier_deliveries'),
    path('courier/deliveries/today/', views.TodayDeliveriesView.as_view(), name='today_deliveries'),
    path('courier/deliveries/<int:delivery_id>/mark-delivered/', views.MarkAsDeliveredView.as_view(), name='mark_delivered'),
    path('courier/deliveries/confirm/', views.DeliveryConfirmationView.as_view(), name='confirm_delivery'),
    path('courier/deliveries/update-quantity/', views.UpdateQuantityView.as_view(), name='update_quantity'),
    path('twa/products/', views.PublicProductListView.as_view(), name='twa_product_list'),
    path('twa/order/', views.ClientOrderView.as_view(), name='twa_create_order'),
]
