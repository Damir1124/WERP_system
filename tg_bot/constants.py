"""
Мультиязычные тексты для клиентского бота (RU / UZ / EN).
Каждый словарь: {lang_code: текст}
"""
from typing import Dict

# ─── Языки ─────────────────────────────────────────────────────────────────────
LANGUAGES: Dict[str, str] = {
    'ru': '🇷🇺 Русский',
    'uz': "🇺🇿 O'zbek",
    'en': '🇬🇧 English',
}

# ─── Приветствие ───────────────────────────────────────────────────────────────
WELCOME = {
    'ru': (
        "Добро пожаловать в EcoLife Water!\n"
        "💧 У нас вы легко можете заказать воду.\n"
        "🚚 Доставка по Самарканду бесплатная.\n"
        "✅ 19 литров в 1 капсуле.\n"
        "💸 Цена 15 000 сум (тара возвратная)"
    ),
    'uz': (
        "EcoLife Water'ga xush kelibsiz!\n"
        "💧 Bizdan suv buyurtma qilish oson.\n"
        "🚚 Samarqand bo'ylab yetkazib berish bepul.\n"
        "✅ 1 kapsulada 19 litr.\n"
        "💸 Narxi 15 000 so'm (idish qaytariladi)"
    ),
    'en': (
        "Welcome to EcoLife Water!\n"
        "💧 You can easily order water from us.\n"
        "🚚 Free delivery in Samarkand.\n"
        "✅ 19 liters in 1 capsule.\n"
        "💸 Price 15,000 sum (returnable container)"
    ),
}

# ─── Главное меню ──────────────────────────────────────────────────────────────
MAIN_MENU_BTN = {
    'ru': '🛒 Сделать заказ',
    'uz': "🛒 Buyurtma berish",
    'en': '🛒 Make an order',
}

MY_ADDRESSES_BTN = {
    'ru': '📋 Мои адреса',
    'uz': "📋 Mening manzillarim",
    'en': '📋 My addresses',
}

LANG_BTN = {
    'ru': '🌐 Выбор языка',
    'uz': "🌐 Tilni tanlash",
    'en': '🌐 Language',
}

COOLERS_BTN = {
    'ru': 'Куллеры',
    'uz': 'Kullerlar',
    'en': 'Coolers',
}

# ─── Количество ────────────────────────────────────────────────────────────────
ASK_QUANTITY = {
    'ru': 'Сколько баклажек хотите заказать? (пример: 2)',
    'uz': "Nechta butilka buyurtma qilmoqchisiz? (masalan: 2)",
    'en': 'How many bottles would you like to order? (example: 2)',
}

INVALID_QUANTITY = {
    'ru': '❌ Пожалуйста, введите целое положительное число.',
    'uz': "❌ Iltimos, butun musbat son kiriting.",
    'en': '❌ Please enter a positive integer.',
}

# ─── Адрес ─────────────────────────────────────────────────────────────────────
ADDRESS_CHOOSE = {
    'ru': 'Выберите адрес доставки из списка или добавьте новый:',
    'uz': "Yetkazib berish manzilini tanlang yoki yangisini qo'shing:",
    'en': 'Choose a delivery address from the list or add a new one:',
}

ADDRESS_ASK_TEXT = {
    'ru': 'Введите адрес или отправьте геолокацию 📍',
    'uz': "Manzilni kiriting yoki geolokatsiya yuboring 📍",
    'en': 'Enter the address or send a location 📍',
}

ADDRESS_ASK_LABEL = {
    'ru': (
        'Дайте название этому адресу (например: Дом, Офис)\n'
        'или нажмите Пропустить'
    ),
    'uz': (
        "Ushbu manzilga nom bering (masalan: Uy, Ofis)\n"
        "yoki O'tkazib yuborish tugmasini bosing"
    ),
    'en': (
        'Give this address a name (e.g.: Home, Office)\n'
        'or press Skip'
    ),
}

ADDRESS_SAVED = {
    'ru': '✅ Адрес сохранён!',
    'uz': "✅ Manzil saqlandi!",
    'en': '✅ Address saved!',
}

ADDRESS_DELETED = {
    'ru': '🗑️ Адрес удалён.',
    'uz': "🗑️ Manzil o'chirildi.",
    'en': '🗑️ Address deleted.',
}

ADDRESS_CONFIRM_DELETE = {
    'ru': 'Удалить этот адрес?',
    'uz': "Ushbu manzilni o'chirishni xohlaysizmi?",
    'en': 'Delete this address?',
}

NO_ADDRESSES = {
    'ru': 'Сохранённых адресов нет.',
    'uz': "Saqlandigan manzillar yo'q.",
    'en': 'No saved addresses.',
}

MY_ADDRESSES_HEADER = {
    'ru': '📍 Ваши сохранённые адреса:',
    'uz': "📍 Sizning saqlangan manzillaringiz:",
    'en': '📍 Your saved addresses:',
}

# ─── Телефон ───────────────────────────────────────────────────────────────────
ASK_PHONE = {
    'ru': 'Введите телефон или нажмите кнопку ниже',
    'uz': "Telefon raqamingizni kiriting yoki pastdagi tugmani bosing",
    'en': 'Enter your phone number or press the button below',
}

INVALID_PHONE = {
    'ru': '❌ Неверный формат номера. Попробуйте ещё раз.',
    'uz': "❌ Noto'g'ri raqam formati. Qayta urinib ko'ring.",
    'en': '❌ Invalid phone format. Try again.',
}

# ─── Заказ ─────────────────────────────────────────────────────────────────────
ORDER_CREATED = {
    'ru': '✅ Заказ получен!',
    'uz': "✅ Buyurtma qabul qilindi!",
    'en': '✅ Order received!',
}

ORDER_NUMBER = {
    'ru': 'Номер заказа: <b>{human_number}</b>',
    'uz': "Buyurtma raqami: <b>{human_number}</b>",
    'en': 'Order number: <b>{human_number}</b>',
}

ORDER_SUMMARY = {
    'ru': '💧 Вода 19л × {quantity} шт.\n📍 {address}',
    'uz': "💧 Suv 19l × {quantity} dona\n📍 {address}",
    'en': '💧 Water 19l × {quantity} pcs\n📍 {address}',
}

BTN_MAIN_MENU = {
    'ru': '🏠 Главное меню',
    'uz': "🏠 Bosh menyu",
    'en': '🏠 Main menu',
}

# ─── Кнопки ────────────────────────────────────────────────────────────────────
BTN_BACK = {
    'ru': '⬅️ Назад',
    'uz': '⬅️ Orqaga',
    'en': '⬅️ Back',
}

BTN_SKIP = {
    'ru': 'Пропустить',
    'uz': "O'tkazib yuborish",
    'en': 'Skip',
}

BTN_ADD_ADDRESS = {
    'ru': '➕ Добавить адрес',
    'uz': "➕ Manzil qo'shish",
    'en': '➕ Add address',
}

BTN_NEW_ADDRESS = {
    'ru': '➕ Новый адрес',
    'uz': "➕ Yangi manzil",
    'en': '➕ New address',
}

BTN_DELETE = {
    'ru': '🗑️ Удалить',
    'uz': "🗑️ O'chirish",
    'en': '🗑️ Delete',
}

BTN_YES = {
    'ru': '✅ Да',
    'uz': '✅ Ha',
    'en': '✅ Yes',
}

BTN_NO = {
    'ru': '❌ Нет',
    'uz': "❌ Yo'q",
    'en': '❌ No',
}

BTN_SEND_LOCATION = {
    'ru': '📍 Отправить геолокацию',
    'uz': '📍 Geolokatsiya yuborish',
    'en': '📍 Send location',
}

BTN_SEND_PHONE = {
    'ru': '📱 Отправить номер',
    'uz': '📱 Raqam yuborish',
    'en': '📱 Send number',
}

# ─── Метки адреса ──────────────────────────────────────────────────────────────
ADDRESS_LABELS = ['Дом', 'Офис', 'Работа', "Uy", "Ofis", "Ish", 'Home', 'Office', 'Work']


def t(texts: Dict[str, str], lang: str) -> str:
    """Получить текст для указанного языка. Fallback на русский."""
    return texts.get(lang) or texts.get('ru', '')