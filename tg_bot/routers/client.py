"""
Роутер для обработки команд клиента.
Прямой доступ к Django ORM (с sync_to_async).
Флоу:
  1. /start → выбор языка → главное меню
  2. Сделать заказ → количество → адрес → телефон → создание заказа
  3. Мои адреса → список → добавить/удалить
"""
import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, Location, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.clients.models import Client, ClientAddress
from apps.logistics.models import Order, OrderItem
from apps.products.models import Product

from tg_bot.states.client import OrderStates, AddressStates
from apps.bot_bridge.phone_validator import validate_uzbek_phone
from tg_bot.constants import t
from tg_bot.constants import (
    WELCOME, MAIN_MENU_BTN, MY_ADDRESSES_BTN, LANG_BTN, COOLERS_BTN,
    BTN_MAIN_MENU,
    ASK_QUANTITY, INVALID_QUANTITY,
    ADDRESS_CHOOSE, ADDRESS_ASK_TEXT, ADDRESS_ASK_LABEL, ADDRESS_SAVED,
    ADDRESS_DELETED, ADDRESS_CONFIRM_DELETE, NO_ADDRESSES, MY_ADDRESSES_HEADER,
    ASK_PHONE, INVALID_PHONE,
    ORDER_CREATED, ORDER_NUMBER, ORDER_SUMMARY,
)
from tg_bot.keyboards.client import (
    get_lang_keyboard, get_main_keyboard,
    get_quantity_keyboard,
    get_address_list_keyboard, get_address_label_keyboard, get_location_keyboard,
    get_phone_keyboard,
    get_my_addresses_keyboard, get_confirm_delete_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="client")

WATER_TYPE = '19W'


# ═══════════════════════════════════════════════════════════════════════════════
# Async-обёртки для Django ORM (sync_to_async)
# ═══════════════════════════════════════════════════════════════════════════════

@sync_to_async
def get_client_by_tgid(tg_id: int) -> Optional[Client]:
    return Client.objects.filter(tg_id=tg_id).first()


@sync_to_async
def get_client_by_phone(phone: str) -> Optional[Client]:
    return Client.objects.filter(phone=phone).first()


@sync_to_async
def get_or_create_client_by_phone(phone: str, tg_id: int) -> tuple:
    """
    Безопасный поиск или создание клиента.
    
    Порядок поиска:
    1. Найти по tg_id — если нашли, обновить phone (если был placeholder)
    2. Найти по phone — если нашли, обновить tg_id
    3. Создать нового — name пустой, телефон реальный
    """
    # Шаг 1: поиск по tg_id
    try:
        client = Client.objects.get(tg_id=tg_id)
        # Обновляем phone если был пустой/placeholder
        if client.phone != phone:
            # Сбрасываем старый phone у другого клиента, если такой phone уже есть
            Client.objects.filter(phone=phone).exclude(id=client.id).update(phone='')
            client.phone = phone
            client.save(update_fields=['phone'])
        return client, False
    except Client.DoesNotExist:
        pass

    # Шаг 2: поиск по phone
    try:
        client = Client.objects.get(phone=phone)
        if client.tg_id is None:
            client.tg_id = tg_id
            client.save(update_fields=['tg_id'])
        return client, False
    except Client.DoesNotExist:
        pass

    # Шаг 3: создать нового клиента с именем из последних 4 цифр номера
    client = Client.objects.create(
        phone=phone,
        name=f"Клиент {phone[-4:]}",
        tg_id=tg_id,
    )
    return client, True


@sync_to_async
def get_client_by_tgid(tg_id: int):
    """Найти клиента по tg_id. Возвращает client или None."""
    return Client.objects.filter(tg_id=tg_id).first()


@sync_to_async
def get_client_addresses(client: Client) -> list:
    """Получить до 3-х последних адресов клиента."""
    return list(
        ClientAddress.objects.filter(client=client)
        .order_by('-last_used_at', '-created_at')[:3]
    )


@sync_to_async
def get_all_client_addresses(client: Client) -> list:
    """Получить ВСЕ адреса клиента (для управления)."""
    return list(
        ClientAddress.objects.filter(client=client)
        .order_by('-last_used_at', '-created_at')
    )


@sync_to_async
def create_client_address(client: Client, **kwargs) -> ClientAddress:
    return ClientAddress.objects.create(client=client, **kwargs)


@sync_to_async
def get_address_by_id(address_id: int) -> Optional[ClientAddress]:
    return ClientAddress.objects.filter(id=address_id).first()


@sync_to_async
def update_address_last_used(address_id: int):
    ClientAddress.objects.filter(id=address_id).update(last_used_at=timezone.now())


@sync_to_async
def delete_address(address_id: int):
    ClientAddress.objects.filter(id=address_id).delete()


@sync_to_async
def enforce_max_addresses(client: Client):
    """Удалить самый старый адрес, если их больше 3."""
    addresses = list(
        ClientAddress.objects.filter(client=client)
        .order_by('-last_used_at', '-created_at')
    )
    if len(addresses) > 3:
        oldest = addresses[-1]
        oldest.delete()


@sync_to_async
def get_water_product() -> Optional[Product]:
    return Product.objects.filter(type_product=WATER_TYPE).first()


@sync_to_async
def create_order(client: Client, **kwargs) -> Order:
    from apps.logistics.services import create_order_with_display_number
    return create_order_with_display_number(client=client, **kwargs)


@sync_to_async
def create_order_item(order: Order, **kwargs) -> OrderItem:
    return OrderItem.objects.create(order=order, **kwargs)


@sync_to_async
def get_order_total(order: Order) -> int:
    return order.get_total_price()


# ═══════════════════════════════════════════════════════════════════════════════
# FLOU 1 — /start → Язык → Главное меню
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие с выбором языка."""
    await state.clear()
    await message.answer(
        "🌐 Выберите язык / Tilni tanlang / Choose language:",
        reply_markup=get_lang_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    """Сохранить язык и показать главное меню."""
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    await callback.message.delete()

    await callback.message.answer(
        t(WELCOME, lang),
        reply_markup=get_main_keyboard(lang)
    )
    await callback.answer()


# ─── Главное меню ──────────────────────────────────────────────────────────────

@router.message(F.text.in_([
    MAIN_MENU_BTN['ru'], MAIN_MENU_BTN['uz'], MAIN_MENU_BTN['en'],
]))
async def main_menu_order(message: Message, state: FSMContext):
    """Начать заказ."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = message.from_user.id
    await state.update_data(tg_id=tg_id)

    # Проверяем, есть ли клиент с таким tg_id
    client = await get_client_by_tgid(tg_id)
    if client:
        await state.update_data(client_id=client.id, client_phone=client.phone or '')

    await message.answer(
        t(ASK_QUANTITY, lang),
        reply_markup=get_quantity_keyboard(lang),
    )
    await state.set_state(OrderStates.waiting_quantity)


@router.message(F.text.in_([
    MY_ADDRESSES_BTN['ru'], MY_ADDRESSES_BTN['uz'], MY_ADDRESSES_BTN['en'],
]))
async def main_menu_addresses(message: Message, state: FSMContext):
    """Показать список адресов."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = message.from_user.id

    client = await get_client_by_tgid(tg_id)
    if not client:
        await message.answer(t(NO_ADDRESSES, lang))
        return

    addresses = await get_all_client_addresses(client)
    if not addresses:
        await message.answer(t(NO_ADDRESSES, lang))
        return

    await message.answer(
        t(MY_ADDRESSES_HEADER, lang),
        reply_markup=get_my_addresses_keyboard(addresses, lang)
    )


@router.message(F.text.in_([
    LANG_BTN['ru'], LANG_BTN['uz'], LANG_BTN['en'],
]))
async def main_menu_lang(message: Message, state: FSMContext):
    """Сменить язык."""
    await message.answer(
        "🌐 Выберите язык / Tilni tanlang / Choose language:",
        reply_markup=get_lang_keyboard()
    )


@router.message(F.text.in_([
    COOLERS_BTN['ru'], COOLERS_BTN['uz'], COOLERS_BTN['en'],
]))
async def main_menu_coolers(message: Message, state: FSMContext):
    """Информация о кулерах."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    texts = {
        'ru': 'Информация о кулерах появится позже.',
        'uz': "Kullerlar haqida ma'lumot keyinroq paydo bo'ladi.",
        'en': 'Information about coolers will appear later.',
    }
    await message.answer(texts.get(lang, texts['ru']))


# ═══════════════════════════════════════════════════════════════════════════════
# FLOU 2 — Сделать заказ
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Шаг 1 — Количество ───────────────────────────────────────────────────────

@router.message(OrderStates.waiting_quantity)
async def process_quantity(message: Message, state: FSMContext):
    """Обработка ввода количества."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    text = message.text.strip()

    # Проверка на "Главное меню" — сброс FSM
    if text in [BTN_MAIN_MENU['ru'], BTN_MAIN_MENU['uz'], BTN_MAIN_MENU['en']]:
        await state.clear()
        await state.update_data(lang=lang)
        await message.answer(
            t(WELCOME, lang),
            reply_markup=get_main_keyboard(lang)
        )
        return

    if not text.isdigit() or int(text) < 1:
        await message.answer(t(INVALID_QUANTITY, lang))
        return

    quantity = int(text)
    await state.update_data(quantity=quantity)

    tg_id = data.get('tg_id') or message.from_user.id
    client = await get_client_by_tgid(tg_id)

    if client:
        addresses = await get_client_addresses(client)
        if addresses:
            await message.answer(
                t(ADDRESS_CHOOSE, lang),
                reply_markup=get_address_list_keyboard(addresses, lang)
            )
            await state.set_state(OrderStates.waiting_address)
            return

    # Нет адресов — сразу ввод нового
    await message.answer(
        t(ADDRESS_ASK_TEXT, lang),
        reply_markup=get_location_keyboard(lang)
    )
    await state.set_state(OrderStates.waiting_address_text)


# ─── Главное меню (сбрасывает FSM и возвращает в главное меню) ────────────────

@router.message(F.text.in_([
    BTN_MAIN_MENU['ru'], BTN_MAIN_MENU['uz'], BTN_MAIN_MENU['en'],
]))
async def go_to_main_menu(message: Message, state: FSMContext):
    """Сбросить FSM и показать главное меню."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    await state.clear()
    await state.update_data(lang=lang)
    await message.answer(
        t(WELCOME, lang),
        reply_markup=get_main_keyboard(lang)
    )


# ─── Шаг 2 — Адрес (выбор из списка) ──────────────────────────────────────────

@router.callback_query(F.data.startswith("sel_addr_"), OrderStates.waiting_address)
async def select_saved_address(callback: CallbackQuery, state: FSMContext):
    """Выбрать существующий адрес."""
    address_id = int(callback.data.split("_")[2])
    await state.update_data(address_id=address_id)

    # Обновляем last_used_at
    await update_address_last_used(address_id)

    await callback.message.edit_text("✅ Адрес выбран.")
    await callback.answer()

    await ask_phone(callback.message, state)


@router.callback_query(F.data == "new_addr", OrderStates.waiting_address)
async def enter_new_address_from_order(callback: CallbackQuery, state: FSMContext):
    """Ввести новый адрес (из флоу заказа)."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    # Удаляем предыдущее сообщение с inline-клавиатурой
    await callback.message.delete()
    # Отправляем новое сообщение с ReplyKeyboard
    await callback.message.answer(
        t(ADDRESS_ASK_TEXT, lang),
        reply_markup=get_location_keyboard(lang)
    )
    await state.set_state(OrderStates.waiting_address_text)
    await callback.answer()


# ─── Шаг 2 (продолжение) — Ввод нового адреса ──────────────────────────────────

async def _save_address_text(state: FSMContext, message: Message, lang: str):
    """Перейти к вводу метки адреса после получения текста/геолокации."""
    await message.answer(
        t(ADDRESS_ASK_LABEL, lang),
        reply_markup=get_address_label_keyboard(lang)
    )


@router.message(OrderStates.waiting_address_text, F.location)
async def process_address_location(message: Message, state: FSMContext):
    """Обработка геолокации как адреса."""
    loc: Location = message.location
    await state.update_data(
        new_address_text='',
        new_address_lat=loc.latitude,
        new_address_lon=loc.longitude,
    )
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    await message.answer(
        f"📍 {loc.latitude:.6f}, {loc.longitude:.6f}",
        reply_markup=ReplyKeyboardRemove()
    )
    await _save_address_text(state, message, lang)
    await state.set_state(OrderStates.waiting_address_label)


@router.message(OrderStates.waiting_address_text, F.text)
async def process_address_text(message: Message, state: FSMContext):
    """Обработка текстового адреса."""
    text = message.text.strip()
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    # Проверка на "Назад"
    if text in ['⬅️ Назад', "⬅️ Orqaga", "⬅️ Back"]:
        tg_id = data.get('tg_id') or message.from_user.id
        client = await get_client_by_tgid(tg_id)
        if client:
            addresses = await get_client_addresses(client)
            if addresses:
                await message.answer(
                    t(ADDRESS_CHOOSE, lang),
                    reply_markup=get_address_list_keyboard(addresses, lang)
                )
                await state.set_state(OrderStates.waiting_address)
                return
        await message.answer(
            t(ASK_QUANTITY, lang),
            reply_markup=get_quantity_keyboard(lang),
        )
        await state.set_state(OrderStates.waiting_quantity)
        return

    await state.update_data(
        new_address_text=text,
        new_address_lat=None,
        new_address_lon=None,
    )
    await _save_address_text(state, message, lang)
    await state.set_state(OrderStates.waiting_address_label)


# ─── Шаг 2 (продолжение) — Ввод метки адреса ───────────────────────────────────

@router.message(OrderStates.waiting_address_label, F.text)
async def process_address_label(message: Message, state: FSMContext):
    """Обработка ввода метки адреса."""
    text = message.text.strip()
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = data.get('tg_id') or message.from_user.id

    # Определяем метку
    skip_labels = ['Пропустить', "O'tkazib yuborish", 'Skip']
    label = '' if text in skip_labels else text

    # Сохраняем данные адреса в FSM (клиент будет создан при вводе телефона)
    await state.update_data(
        new_address_text=data.get('new_address_text', ''),
        new_address_lat=data.get('new_address_lat'),
        new_address_lon=data.get('new_address_lon'),
        new_address_label=label,
    )

    await message.answer(
        t(ADDRESS_SAVED, lang),
        reply_markup=ReplyKeyboardRemove()
    )

    # Переходим к шагу телефона
    await ask_phone(message, state)


# ─── Шаг 3 — Телефон ──────────────────────────────────────────────────────────

async def ask_phone(message: Message, state: FSMContext):
    """Запросить номер телефона."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    await message.answer(
        t(ASK_PHONE, lang),
        reply_markup=get_phone_keyboard(lang)
    )
    await state.set_state(OrderStates.waiting_phone)


@router.message(OrderStates.waiting_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Обработка контакта (отправка номера)."""
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    await _process_phone(message, state, phone)


@router.message(OrderStates.waiting_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    """Обработка текстового ввода номера."""
    text = message.text.strip()
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    # Проверка на "Назад"
    if text in ['⬅️ Назад', "⬅️ Orqaga", "⬅️ Back"]:
        tg_id = data.get('tg_id') or message.from_user.id
        client = await get_client_by_tgid(tg_id)
        if client:
            addresses = await get_client_addresses(client)
            if addresses:
                await message.answer(
                    t(ADDRESS_CHOOSE, lang),
                    reply_markup=get_address_list_keyboard(addresses, lang)
                )
                await state.set_state(OrderStates.waiting_address)
                return
        await message.answer(
            t(ADDRESS_ASK_TEXT, lang),
            reply_markup=get_location_keyboard(lang)
        )
        await state.set_state(OrderStates.waiting_address_text)
        return

    try:
        phone = validate_uzbek_phone(text)
    except ValueError as e:
        await message.answer(f"{t(INVALID_PHONE, lang)}\n{str(e)}")
        return

    await _process_phone(message, state, phone)


async def _process_phone(message: Message, state: FSMContext, phone: str):
    """Общий обработчик: найти/создать клиента и создать заказ."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = data.get('tg_id') or message.from_user.id

    # Найти или создать клиента по телефону
    client, _ = await get_or_create_client_by_phone(phone, tg_id)

    await state.update_data(client_id=client.id, client_phone=phone)

    await message.answer(
        f"✅ {phone}",
        reply_markup=ReplyKeyboardRemove()
    )

    await _create_order(message, state, client)


# ─── Шаг 4 — Создание заказа ───────────────────────────────────────────────────

async def _create_order(message: Message, state: FSMContext, client: Client):
    """Создать заказ и показать подтверждение."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    quantity = data.get('quantity', 1)
    address_id = data.get('address_id')

    # Если адрес ещё не создан — создаём из FSM данных
    address = None
    if address_id:
        address = await get_address_by_id(address_id)

    if not address:
        # Создаём адрес из FSM данных
        address = await create_client_address(
            client,
            address_text=data.get('new_address_text', ''),
            latitude=data.get('new_address_lat'),
            longitude=data.get('new_address_lon'),
            label=data.get('new_address_label', ''),
            last_used_at=timezone.now(),
        )
        await enforce_max_addresses(client)

    # Получаем продукт "Вода 19л"
    product = await get_water_product()
    if not product:
        await message.answer("❌ Ошибка: продукт не найден.")
        await state.clear()
        return

    # Создаём заказ
    order = await create_order(
        client,
        payment_type=Order.PaymentType.CASH,
        status=Order.Status.PENDING,
        trip=None,
    )
    await create_order_item(
        order,
        product=product,
        quantity=quantity,
        price=None,  # рассчитается в save()
    )

    # Обновляем last_used_at адреса
    await update_address_last_used(address.id)

    # Формируем ответ
    address_display = address.address_text or '(геолокация)'
    if address.label:
        address_display = f"{address.label}: {address_display}"

    # Если есть координаты — делаем адрес ссылкой на Яндекс.Карты (pt = долгота,широта)
    if address.latitude and address.longitude:
        maps_url = f"https://yandex.ru/maps/?pt={address.longitude},{address.latitude}&z=17&l=map"
        address_display = f'<a href="{maps_url}">{address_display}</a>'

    await message.answer(
        f"{t(ORDER_CREATED, lang)}\n"
        f"{t(ORDER_NUMBER, lang).format(human_number=order.human_number)}\n"
        f"{t(ORDER_SUMMARY, lang).format(quantity=quantity, address=address_display)}",
        reply_markup=get_main_keyboard(lang),
        parse_mode='HTML',
    )
    await state.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# FLOU 3 — Мои адреса (управление)
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("del_addr_"))
async def delete_address_confirm(callback: CallbackQuery, state: FSMContext):
    """Запросить подтверждение удаления адреса."""
    address_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    await callback.message.edit_text(
        t(ADDRESS_CONFIRM_DELETE, lang),
        reply_markup=get_confirm_delete_keyboard(address_id, lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_"))
async def delete_address_execute(callback: CallbackQuery, state: FSMContext):
    """Подтвердить удаление адреса."""
    address_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = callback.from_user.id

    await delete_address(address_id)

    # Показываем обновлённый список
    client = await get_client_by_tgid(tg_id)
    if client:
        addresses = await get_all_client_addresses(client)
        await callback.message.edit_text(
            f"{t(ADDRESS_DELETED, lang)}\n\n{t(MY_ADDRESSES_HEADER, lang)}"
            if addresses else t(ADDRESS_DELETED, lang),
            reply_markup=get_my_addresses_keyboard(addresses, lang) if addresses else None
        )
    else:
        await callback.message.edit_text(t(ADDRESS_DELETED, lang))
    await callback.answer()


@router.callback_query(F.data == "cancel_del")
async def cancel_delete_address(callback: CallbackQuery, state: FSMContext):
    """Отменить удаление адреса."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = callback.from_user.id

    client = await get_client_by_tgid(tg_id)
    if client:
        addresses = await get_all_client_addresses(client)
        await callback.message.edit_text(
            t(MY_ADDRESSES_HEADER, lang),
            reply_markup=get_my_addresses_keyboard(addresses, lang)
        )
    else:
        await callback.message.edit_text(t(NO_ADDRESSES, lang))
    await callback.answer()


@router.callback_query(F.data == "add_addr")
async def add_address_from_management(callback: CallbackQuery, state: FSMContext):
    """Добавить адрес из режима управления адресами."""
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    await callback.message.edit_text(t(ADDRESS_ASK_TEXT, lang))
    await callback.message.answer(
        t(ADDRESS_ASK_TEXT, lang),
        reply_markup=get_location_keyboard(lang)
    )
    await state.set_state(AddressStates.waiting_address_text)
    await callback.answer()


# ─── Обработка ввода адреса из управления адресами ─────────────────────────────

@router.message(AddressStates.waiting_address_text, F.location)
async def process_address_location_mgmt(message: Message, state: FSMContext):
    """Геолокация из управления адресами."""
    loc: Location = message.location
    await state.update_data(
        new_address_text='',
        new_address_lat=loc.latitude,
        new_address_lon=loc.longitude,
    )
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    await message.answer(
        f"📍 {loc.latitude:.6f}, {loc.longitude:.6f}",
        reply_markup=ReplyKeyboardRemove()
    )
    await _save_address_text(state, message, lang)
    await state.set_state(AddressStates.waiting_address_label)


@router.message(AddressStates.waiting_address_text, F.text)
async def process_address_text_mgmt(message: Message, state: FSMContext):
    """Текст адреса из управления адресами."""
    text = message.text.strip()
    data = await state.get_data()
    lang = data.get('lang', 'ru')

    if text in ['⬅️ Назад', "⬅️ Orqaga", "⬅️ Back"]:
        tg_id = data.get('tg_id') or message.from_user.id
        client = await get_client_by_tgid(tg_id)
        if client:
            addresses = await get_all_client_addresses(client)
            await message.answer(
                t(MY_ADDRESSES_HEADER, lang),
                reply_markup=get_my_addresses_keyboard(addresses, lang)
            )
        else:
            await message.answer(t(NO_ADDRESSES, lang))
        await state.set_state(None)
        return

    await state.update_data(
        new_address_text=text,
        new_address_lat=None,
        new_address_lon=None,
    )
    await _save_address_text(state, message, lang)
    await state.set_state(AddressStates.waiting_address_label)


@router.message(AddressStates.waiting_address_label, F.text)
async def process_address_label_mgmt(message: Message, state: FSMContext):
    """Метка адреса из управления адресами."""
    text = message.text.strip()
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    tg_id = data.get('tg_id') or message.from_user.id

    skip_labels = ['Пропустить', "O'tkazib yuborish", 'Skip']
    label = '' if text in skip_labels else text

    client = await get_client_by_tgid(tg_id)
    if not client:
        await message.answer(
            "❌ Сначала сделайте заказ, чтобы зарегистрироваться в системе.",
            reply_markup=get_main_keyboard(lang)
        )
        await state.set_state(None)
        return

    await create_client_address(
        client,
        address_text=data.get('new_address_text', ''),
        latitude=data.get('new_address_lat'),
        longitude=data.get('new_address_lon'),
        label=label,
        last_used_at=timezone.now(),
    )
    await enforce_max_addresses(client)

    await message.answer(
        t(ADDRESS_SAVED, lang),
        reply_markup=ReplyKeyboardRemove()
    )

    # Показать обновлённый список
    addresses = await get_all_client_addresses(client)
    await message.answer(
        t(MY_ADDRESSES_HEADER, lang),
        reply_markup=get_my_addresses_keyboard(addresses, lang)
    )
    await state.set_state(None)


# ─── Fallback для "noop" кнопок ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("noop_"))
async def noop_callback(callback: CallbackQuery):
    """Ничего не делать на информационные кнопки."""
    await callback.answer()
