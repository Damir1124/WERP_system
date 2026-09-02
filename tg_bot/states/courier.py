"""
FSM States для курьера.
- CourierCreateOrder — создание заказа (см. routers/courier_create_order.py)
- CourierTripStart   — ввод количества загруженных баклажек при старте рейса
- CourierDeliverOrder — пошаговое подтверждение доставки с операциями по таре
"""
from aiogram.fsm.state import State, StatesGroup


class CourierCreateOrder(StatesGroup):
    """Состояния для создания заказа курьером."""

    waiting_for_phone = State()
    waiting_for_address_choice = State()
    waiting_for_address_text = State()
    waiting_for_location = State()
    waiting_for_product_quantity = State()
    waiting_for_add_more_products = State()
    waiting_for_product_selection = State()
    waiting_for_additional_quantity = State()
    waiting_for_payment_type = State()
    waiting_for_confirmation = State()


class CourierTripStart(StatesGroup):
    """Старт рейса: ввод количества загруженных полных баклажек."""
    waiting_for_full_loaded = State()


class CourierDeliverOrder(StatesGroup):
    """Редактирование/подтверждение доставки заказа (экран как в OrderConfirm.jsx)."""
    waiting_for_edit = State()
