"""
Все текстовые сообщения бота на русском языке.
"""

# Общие сообщения
MSG_ERROR_LOADING = "❌ Ошибка загрузки данных. Попробуйте позже."
MSG_HELP = """
📖 Помощь по командам курьера:

• Пул заказов — список заказов, которые можно взять
• Мой рейс — детали текущего рейса и счётчики
• Смены и рейсы — история ваших смен
• Коллеги — кто сегодня на смене

Для создания заказа используйте кнопку в пуле заказов.
"""

# Пул заказов
MSG_POOL_LEGEND = "💧💧 ✅ ⏳"
MSG_POOL_EMPTY = "Пул заказов пуст."
MSG_POOL_AVAILABLE = "Доступные заказы ({count}):"

# Детали заказа
MSG_ORDER_DETAILS = """📦 Заказ {human_number}

👤 Клиент: {client_name}
📞 Телефон: {client_phone}
📍 Адрес: {client_address}

🚰 Товары:
{items}

💰 Сумма: {total_price:,} сум
💳 Оплата: {payment_type}

⏰ Создан: {time_ago}
"""

MSG_ORDER_TAKEN = "✅ Заказ {human_number} добавлен в ваш рейс!\n\nИспользуйте 'Мой рейс' для просмотра."
MSG_ORDER_ERROR = "❌ {error}"

# Мой рейс
MSG_NO_TRIP = "У вас нет активного рейса.\nОткройте смену и начните рейс."
MSG_TRIP_INFO = """📊 Рейс #{trip_id} (активный)
{'=' * 40}
🚛 Загружено: {full_loaded} шт.
✅ Доставлено: {delivered_count} заказов ({delivered_qty} шт.)
📦 Остаток в машине: {full_remain} шт.
🔄 Пустых в машине: {empty_in_car} шт.
⚠️ Брак: {defect_qty} шт.
{'=' * 40}
💵 Наличных должно быть: {cash_expected:,} сум
💳 По карте: {card_expected:,} сум
{'=' * 40}
"""

# История смен
MSG_NO_SHIFTS = "Нет истории смен."
MSG_SHIFTS_HISTORY = "📅 История ваших смен (последние 5):\n\n"

# Коллеги
MSG_NO_COLLEAGUES = "Нет коллег на смене."
MSG_COLLEAGUES_HEADER = "👥 Ваши коллеги на смене сегодня:\n\n"

# Создание заказа
MSG_CREATE_ORDER_PHONE = "📞 Введите номер телефона клиента:\n(формат: +998901234567)"
MSG_CREATE_ORDER_PHONE_ERROR = "❌ {error}\n\nПопробуйте ещё раз:"
MSG_CREATE_ORDER_CLIENT_FOUND = "✅ Клиент найден: {client_name}\n\nВыберите адрес доставки:"
MSG_CREATE_ORDER_NEW_CLIENT = """📝 Новый клиент!
Имя будет создано автоматически: "{name}"

Введите адрес доставки:
(или отправьте геолокацию)
"""
MSG_CREATE_ORDER_ADDRESS_SAVED = "✅ Адрес сохранён!"
MSG_CREATE_ORDER_LOCATION_SAVED = "✅ Геолокация сохранена!\n📍 Координаты: {lat}, {lon}"
MSG_CREATE_ORDER_QUANTITY = "🚰 Сколько баклажек воды 19л?\n(введите число)"
MSG_CREATE_ORDER_QUANTITY_ERROR = "Введите корректное количество (1-100):"
MSG_CREATE_ORDER_QUANTITY_ADDED = "✅ Добавлено: Вода 19л × {quantity} шт.\n\nДобавить ещё товары?"
MSG_CREATE_ORDER_PAYMENT = "💳 Способ оплаты?"
MSG_CREATE_ORDER_CONFIRMATION = """📦 Подтверждение заказа:

👤 Клиент: {client_name}
📞 Телефон: {phone}
📍 Адрес: {address}

🚰 Товары:
{items}

💳 Оплата: {payment_type}
"""
MSG_CREATE_ORDER_SUCCESS = "✅ Заказ {human_number} создан!\n\nЗаказ автоматически добавлен в ваш текущий рейс.\n\nИспользуйте 'Мой рейс' для просмотра."
MSG_CREATE_ORDER_ERROR = "❌ Ошибка создания заказа:\n{error}\n\nПопробуйте ещё раз."
MSG_CREATE_ORDER_CANCELLED = "Создание заказа отменено."

# Кнопки
BTN_TAKE_ORDER = "✅ Взять заказ"
BTN_BACK_TO_POOL = "⬅️ Назад в пул"
BTN_CREATE_ORDER = "➕ Создать новый заказ"
BTN_USE_SAVED_ADDRESS = "📍 Использовать адрес: {address}"
BTN_ENTER_NEW_ADDRESS = "✍️ Ввести новый адрес"
BTN_SEND_LOCATION = "📍 Отправить геолокацию"
BTN_ADD_MORE_PRODUCTS = "➕ Добавить товар"
BTN_PROCEED_TO_PAYMENT = "✅ Продолжить к оплате"
BTN_PAYMENT_CASH = "💵 Наличные"
BTN_PAYMENT_CARD = "💳 Карта"
BTN_PAYMENT_BONUS = "🎁 Бонусы"
BTN_CONFIRM_CREATE = "✅ Создать заказ"
BTN_CANCEL = "❌ Отменить"
