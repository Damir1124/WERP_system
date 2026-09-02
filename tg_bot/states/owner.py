from aiogram.fsm.state import State, StatesGroup


class OwnerCreateOrder(StatesGroup):
    """FSM для создания заказа администратором: телефон → адрес → товары → подтверждение."""
    waiting_for_phone = State()
    waiting_for_address_choice = State()
    waiting_for_address_text = State()
    waiting_for_product_choice = State()
    waiting_for_product_quantity = State()
    waiting_for_product_add = State()
    waiting_for_payment = State()
    waiting_for_confirmation = State()


class OwnerEditOrder(StatesGroup):
    """FSM для редактирования заказа администратором: адрес → товары."""
    waiting_for_address_choice = State()
    waiting_for_address_text = State()
    waiting_for_product_choice = State()
    waiting_for_product_quantity = State()
    waiting_for_product_add = State()
