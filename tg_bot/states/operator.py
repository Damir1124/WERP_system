from aiogram.fsm.state import State, StatesGroup


class OperatorEditOrder(StatesGroup):
    """FSM для редактирования заказа оператором: адрес → товары."""
    waiting_for_address_choice = State()
    waiting_for_address_text = State()
    waiting_for_product_choice = State()
    waiting_for_product_quantity = State()
    waiting_for_product_add = State()