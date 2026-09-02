"""
FSM States для клиента.
- OrderStates — создание заказа
- AddressStates — управление адресами (добавление)
"""
from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """Состояния для создания заказа."""
    waiting_quantity = State()       # Шаг 1: ввод количества
    waiting_address = State()        # Шаг 2: выбор из списка или ввод нового
    waiting_address_text = State()   # Шаг 2: ввод текста/геолокации
    waiting_address_label = State()  # Шаг 2: ввод названия адреса
    waiting_phone = State()          # Шаг 3: ввод телефона


class AddressStates(StatesGroup):
    """Состояния для управления адресами."""
    waiting_address_text = State()   # ввод текста/геолокации
    waiting_address_label = State()  # ввод названия адреса