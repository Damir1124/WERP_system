// ─── Мультиязычность клиентского Mini App (RU / UZ / EN) ─────────────────────
// Формат словаря: { key: { ru: '...', uz: '...', en: '...' } }
// Повторяет структуру tg_bot/constants.py для единообразия с ботом.

export const LANGUAGES = {
  ru: '🇷🇺 Русский',
  uz: "🇺🇿 O'zbek",
  en: '🇬🇧 English',
}

const STRINGS = {
  // ─── Приветствие / выбор языка ─────────────────────────────────────────────
  welcome: {
    ru: 'Добро пожаловать в EcoLife Water!\n💧 Закажите воду легко.\n🚚 Доставка по Самарканду бесплатная.',
    uz: "EcoLife Water'ga xush kelibsiz!\n💧 Suv buyurtma qilish oson.\n🚚 Samarqand bo'ylab yetkazib berish bepul.",
    en: 'Welcome to EcoLife Water!\n💧 Order water easily.\n🚚 Free delivery in Samarkand.',
  },
  choose_language: {
    ru: '🌐 Выберите язык / Tilni tanlang / Choose language:',
    uz: '🌐 Tilni tanlang / Выберите язык / Choose language:',
    en: '🌐 Choose language / Tilni tanlang / Выберите язык:',
  },
  app_title: {
    ru: 'Eco Life Zam-Zam',
    uz: 'Eco Life Zam-Zam',
    en: 'Eco Life Zam-Zam',
  },
  app_subtitle: {
    ru: 'Доставка питьевой воды',
    uz: "Ichimlik suv yetkazib berish",
    en: 'Drinking water delivery',
  },
  hello: {
    ru: 'Привет',
    uz: 'Salom',
    en: 'Hello',
  },

  // ── Навигация ─────────────────────────────────────────────────────────────
  nav_catalog: {
    ru: 'Каталог',
    uz: 'Katalog',
    en: 'Catalog',
  },
  nav_orders: {
    ru: 'Заказы',
    uz: 'Buyurtmalar',
    en: 'Orders',
  },
  nav_addresses: {
    ru: 'Адреса',
    uz: 'Manzillar',
    en: 'Addresses',
  },

  // ── Каталог ───────────────────────────────────────────────────────────────
  catalog_title: {
    ru: 'Каталог товаров',
    uz: 'Tovar katalogi',
    en: 'Product catalog',
  },
  catalog_loading: {
    ru: 'Загрузка каталога...',
    uz: 'Katalog yuklabotilmoqda...',
    en: 'Loading catalog...',
  },
  catalog_empty: {
    ru: 'Товары не найдены',
    uz: 'Tovarlar topilmadi',
    en: 'No products found',
  },
  catalog_error: {
    ru: 'Ошибка',
    uz: 'Xato',
    en: 'Error',
  },
  retry: {
    ru: 'Повторить',
    uz: 'Qayta urinish',
    en: 'Retry',
  },
  order_btn: {
    ru: 'Заказать',
    uz: 'Buyurtma',
    en: 'Order',
  },
  per_unit: {
    ru: 'сум / шт.',
    uz: "so'm / dona",
    en: 'sum / pc.',
  },

  // ─── Оформление заказа ────────────────────────────────────────────────────
  order_title: {
    ru: 'Оформление заказа',
    uz: 'Buyurtmani rasmiylash',
    en: 'Order checkout',
  },
  back: {
    ru: '← Назад',
    uz: '← Orqaga',
    en: '← Back',
  },
  product_not_found: {
    ru: 'Товар не найден',
    uz: 'Tovar topilmadi',
    en: 'Product not found',
  },
  to_catalog: {
    ru: 'В каталог',
    uz: 'Katalogga',
    en: 'To catalog',
  },
  quantity: {
    ru: 'Количество',
    uz: 'Soni',
    en: 'Quantity',
  },
  payment_type: {
    ru: 'Способ оплаты',
    uz: "To'lov usuli",
    en: 'Payment method',
  },
  pay_cash: {
    ru: 'Наличные',
    uz: 'Naqd',
    en: 'Cash',
  },
  pay_card: {
    ru: 'Карта',
    uz: 'Karta',
    en: 'Card',
  },
  delivery_address: {
    ru: 'Адрес доставки',
    uz: 'Yetkazib berish manzil',
    en: 'Delivery address',
  },
  address_placeholder: {
    ru: 'Введите адрес',
    uz: 'Manzilni kiriting',
    en: 'Enter address',
  },
  choose_saved_address: {
    ru: 'Выберите сохранённый адрес или добавьте новый:',
    uz: "Saqlandi manzilni tanlang yoki yangisini qo'shing:",
    en: 'Choose a saved address or add a new one:',
  },
  add_new_address: {
    ru: '➕ Добавить новый адрес',
    uz: "➕ Yangi manzil qo'shish",
    en: '➕ Add new address',
  },
  use_geolocation: {
    ru: 'Указать на карте',
    uz: 'Xaritada belgilash',
    en: 'Pick on map',
  },
  address_label: {
    ru: 'Метка (Дом, Офис)',
    uz: 'Belgi (Uy, Ofis)',
    en: 'Label (Home, Office)',
  },
  address_label_placeholder: {
    ru: 'Например: Дом',
    uz: 'Masalan: Uy',
    en: 'e.g.: Home',
  },
  note: {
    ru: 'Примечание (необязательно)',
    uz: 'Izoh (ixtiyoriy)',
    en: 'Note (optional)',
  },
  note_placeholder: {
    ru: 'Например: позвоните за 10 минут...',
    uz: "Masalan: 10 daqiqa oldin qo'ngiring...",
    en: 'e.g.: call 10 minutes before...',
  },
  total: {
    ru: 'Итого',
    uz: 'Jami',
    en: 'Total',
  },
  confirm_order: {
    ru: 'Подтвердить заказ',
    uz: 'Buyurtmani tasdiqlash',
    en: 'Confirm order',
  },
  processing: {
    ru: 'Оформляем...',
    uz: 'Rasmiylashda...',
    en: 'Processing...',
  },
  phone: {
    ru: 'Телефон',
    uz: 'Telefon',
    en: 'Phone',
  },
  phone_placeholder: {
    ru: '+998901234567',
    uz: '+998901234567',
    en: '+998901234567',
  },
  phone_required: {
    ru: 'Введите номер телефона',
    uz: 'Telefon raqamni kiriting',
    en: 'Enter your phone number',
  },
  phone_invalid: {
    ru: 'Номер телефона должен содержать 9 цифр',
    uz: 'Telefon raqam 9 ta raqamdan iborat bo\'lishi kerak',
    en: 'Phone number must contain 9 digits',
  },
  address_required: {
    ru: 'Введите адрес доставки',
    uz: 'Yetkazib berish manzilni kiriting',
    en: 'Enter delivery address',
  },

  // ─── Мои заказы ───────────────────────────────────────────────────────────
  my_orders: {
    ru: 'Мои заказы',
    uz: 'Mening buyurtmalarim',
    en: 'My orders',
  },
  refresh: {
    ru: 'Обновить',
    uz: 'Yangilash',
    en: 'Refresh',
  },
  orders_loading: {
    ru: 'Загрузка заказов...',
    uz: 'Buyurtmalar yuklanotilmoqda...',
    en: 'Loading orders...',
  },
  no_orders: {
    ru: 'У вас пока нет заказов',
    uz: 'Sizda hali buyurtmalar yoq',
    en: 'You have no orders yet',
  },
  no_orders_hint: {
    ru: 'Перейдите в каталог, чтобы сделать заказ',
    uz: "Buyurtma qilish uchun katalogga o'ting",
    en: 'Go to catalog to place an order',
  },
  order_num: {
    ru: 'Заказ',
    uz: 'Buyurtma',
    en: 'Order',
  },
  status_pending: {
    ru: 'Ожидает',
    uz: 'Kutmoqda',
    en: 'Pending',
  },
  status_delivered: {
    ru: 'Доставлен',
    uz: 'Yetkazib berildi',
    en: 'Delivered',
  },
  status_cancelled: {
    ru: 'Отменён',
    uz: 'Bekor qilindi',
    en: 'Cancelled',
  },
  quantity_label: {
    ru: 'Количество',
    uz: 'Qo',
    en: 'Quantity',
  },
  amount: {
    ru: 'Сумма',
    uz: 'Summa',
    en: 'Amount',
  },
  payment: {
    ru: 'Оплата',
    uz: "To'lov",
    en: 'Payment',
  },
  date: {
    ru: 'Дата',
    uz: 'Sana',
    en: 'Date',
  },
  pay_cash_short: {
    ru: 'Наличные',
    uz: 'Naqd',
    en: 'Cash',
  },
  pay_card_short: {
    ru: 'Карта',
    uz: 'Karta',
    en: 'Card',
  },
  pay_bonus_short: {
    ru: 'Бонус',
    uz: 'Bonus',
    en: 'Bonus',
  },
  pending_hint: {
    ru: 'Ваш заказ ожидает назначения курьера',
    uz: "Buyurtmangiz kuryer tayinlashni kutmoqda",
    en: 'Your order is waiting for courier assignment',
  },
  delivered_at: {
    ru: 'Доставлен',
    uz: 'Yetkazib berildi',
    en: 'Delivered',
  },
  order_created_success: {
    ru: 'Заказ {num} создан! Ожидайте курьера.',
    uz: 'Buyurtma {num} yaratildi! Kuryerni kuting.',
    en: 'Order {num} created! Expect the courier.',
  },

  // ─── Мои адреса ───────────────────────────────────────────────────────────
  my_addresses: {
    ru: 'Мои адреса',
    uz: 'Mening manzillarim',
    en: 'My addresses',
  },
  no_addresses: {
    ru: 'У вас пока нет сохранённых адресов',
    uz: 'Sizda saqlangi manzillar yoq',
    en: 'You have no saved addresses yet',
  },
  add_address: {
    ru: 'Добавить адрес',
    uz: "Manzil qo'shish",
    en: 'Add address',
  },
  delete_address: {
    ru: 'Удалить',
    uz: "O'chirish",
    en: 'Delete',
  },
  address_saved: {
    ru: 'Адрес сохранён!',
    uz: 'Manzil saqlandi!',
    en: 'Address saved!',
  },
  address_deleted: {
    ru: 'Адрес удалён.',
    uz: "Manzil o'chirildi.",
    en: 'Address deleted.',
  },
  confirm_delete_address: {
    ru: 'Удалить этот адрес?',
    uz: "Ushbu manzilni o'chirishni xohlaysizmi?",
    en: 'Delete this address?',
  },
  save_address: {
    ru: 'Сохранить адрес',
    uz: 'Manzilni saqlash',
    en: 'Save address',
  },
  cancel: {
    ru: 'Отмена',
    uz: 'Bekor qilish',
    en: 'Cancel',
  },
  confirm: {
    ru: 'Подтвердить',
    uz: 'Tasdiqlash',
    en: 'Confirm',
  },
  my_location: {
    ru: 'Моя локация',
    uz: 'Mening joylashuvim',
    en: 'My location',
  },
  pick_on_map_hint: {
    ru: 'Нажмите на карту, чтобы выбрать точное место',
    uz: 'Aniq joyni tanlash uchun xaritmni bosing',
    en: 'Tap the map to choose the exact spot',
  },
  coordinates: {
    ru: 'Координаты',
    uz: 'Koordinatalar',
    en: 'Coordinates',
  },
  geolocation_not_supported: {
    ru: 'Геолокация не поддерживается вашим браузером',
    uz: "Geolokatsiya brauzeringda qo'llab-qo'llab emas",
    en: 'Geolocation is not supported by your browser',
  },
  geolocation_failed: {
    ru: 'Не удалось получить геолокацию',
    uz: 'Geolokatsiyani olish imkon bo\'lmadi',
    en: 'Failed to get geolocation',
  },

  // ─── Регистрация ──────────────────────────────────────────────────────────
  register_title: {
    ru: 'Регистрация',
    uz: "Ro'yxatdan o'tish",
    en: 'Registration',
  },
  register_hint: {
    ru: 'Введите ваши данные для первого заказа',
    uz: 'Birinchi buyurtma uchun ma\'lumotlarni kiriting',
    en: 'Enter your details for the first order',
  },
  your_name: {
    ru: 'Ваше имя *',
    uz: 'Ismingiz *',
    en: 'Your name *',
  },
  name_placeholder: {
    ru: 'Иван Иванов',
    uz: 'Ivan Ivanov',
    en: 'Ivan Ivanov',
  },
  register_btn: {
    ru: 'Зарегистрироваться',
    uz: "Ro'yxatdan o'tish",
    en: 'Register',
  },
  registering: {
    ru: 'Регистрация...',
    uz: "Ro'yxatdan o'tilmoqda...",
    en: 'Registering...',
  },
  name_phone_required: {
    ru: 'Имя и телефон обязательны',
    uz: 'Ism va telefon majburiy',
    en: 'Name and phone are required',
  },
  open_in_telegram: {
    ru: 'Откройте в Telegram',
    uz: 'Telegramda oching',
    en: 'Open in Telegram',
  },
  works_in_telegram: {
    ru: 'Это приложение работает только внутри Telegram.',
    uz: 'Ushbu ilova faqat Telegram ichida ishlaydi.',
    en: 'This app works only inside Telegram.',
  },
  connection_error: {
    ru: 'Ошибка подключения',
    uz: 'Ulanish xato',
    en: 'Connection error',
  },
  connection_error_hint: {
    ru: 'Не удалось подключиться к серверу',
    uz: 'Serverga ulanish imkon bo\'lmadi',
    en: 'Failed to connect to the server',
  },
  loading: {
    ru: 'Загрузка...',
    uz: 'Yuklanilmoqda...',
    en: 'Loading...',
  },

  // ─── Каталог: кнопка «Купить» / корзина ────────────────────────────────────
  buy: {
    ru: 'Купить',
    uz: 'Sotib olish',
    en: 'Buy',
  },
  load_more: {
    ru: 'Загрузить ещё',
    uz: 'Yana yuklash',
    en: 'Load more',
  },
  cart: {
    ru: 'Корзина',
    uz: 'Savat',
    en: 'Cart',
  },
  cart_items: {
    ru: 'Корзина ({n})',
    uz: 'Savat ({n})',
    en: 'Cart ({n})',
  },
  cart_title: {
    ru: 'Корзина',
    uz: 'Savat',
    en: 'Cart',
  },
  cart_empty: {
    ru: 'Нет выбранных товаров',
    uz: 'Tanlangan mahsulotlar yoq',
    en: 'No products selected',
  },
  go_to_catalog: {
    ru: 'Перейти в каталог',
    uz: 'Katalogga o\'tish',
    en: 'Go to catalog',
  },
  total_to_pay: {
    ru: 'Итого к оплате',
    uz: "To'lash uchun jami",
    en: 'Total to pay',
  },
  checkout: {
    ru: 'Оформить заказ',
    uz: 'Buyurtmani rasmiylash',
    en: 'Checkout',
  },
  clear_cart: {
    ru: 'Очистить корзину',
    uz: 'Savatni tozalash',
    en: 'Clear cart',
  },
  remove_item: {
    ru: 'Удалить',
    uz: "O'chirish",
    en: 'Remove',
  },

  // ─── Заказы: редактирование / удаление ────────────────────────────────────
  edit_order: {
    ru: 'Редактировать',
    uz: 'Tahrirlash',
    en: 'Edit',
  },
  delete_order: {
    ru: 'Отменить',
    uz: 'Bekor qilish',
    en: 'Cancel',
  },
  edit_order_title: {
    ru: 'Редактирование заказа',
    uz: 'Buyurtmani tahrirlash',
    en: 'Edit order',
  },
  save_changes: {
    ru: 'Сохранить изменения',
    uz: "O'zgarishlarni saqlash",
    en: 'Save changes',
  },
  order_updated: {
    ru: 'Заказ обновлён',
    uz: 'Buyurtma yangilandi',
    en: 'Order updated',
  },
  order_deleted: {
    ru: 'Заказ отменён',
    uz: 'Buyurtma bekor qilindi',
    en: 'Order cancelled',
  },
  confirm_delete_order: {
    ru: 'Отменить этот заказ?',
    uz: "Ushbu buyurtmani bekor qilishni xohlaysizmi?",
    en: 'Cancel this order?',
  },
  address: {
    ru: 'Адрес',
    uz: 'Manzil',
    en: 'Address',
  },
  edit_only_pending: {
    ru: 'Редактирование возможно только пока заказ ожидает курьера',
    uz: "Buyurtma kuryerni kutayotgandagina tahrirlash mumkin",
    en: 'Editing is possible only while the order is awaiting a courier',
  },
}

// ─── Определение языка ──────────────────────────────────────────────────────
// Приоритет: sessionStorage (выбор пользователя) → язык Telegram → 'ru'
export function detectLanguage() {
  const saved = sessionStorage.getItem('client_lang')
  if (saved && STRINGS && ['ru', 'uz', 'en'].includes(saved)) return saved

  const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
  if (tgLang) {
    const base = tgLang.split('-')[0].toLowerCase()
    if (['ru', 'uz', 'en'].includes(base)) return base
    if (base === 'uk' || base === 'be') return 'ru'
  }
  return 'ru'
}

export function setLanguage(lang) {
  sessionStorage.setItem('client_lang', lang)
}

// ─── Функция перевода ─────────────────────────────────────────────────────────
export function t(key, lang) {
  const entry = STRINGS[key]
  if (!entry) return key
  return entry[lang] || entry.ru || key
}

// Функция с подстановкой {placeholders}
export function tF(key, lang, params = {}) {
  let text = t(key, lang)
  for (const [k, v] of Object.entries(params)) {
    text = text.replace(`{${k}}`, String(v))
  }
  return text
}