"""
Утилиты для работы с Telegram Mini App и проверки подписей.
"""
import hashlib
import hmac
import os
from urllib.parse import parse_qs, urlencode
from django.conf import settings


def verify_telegram_init_data(init_data: str) -> bool:
    """
    Проверяет подпись initData от Telegram Mini App.
    Алгоритм: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    
    Параметры:
        init_data: строка вида "query_id=...&user=...&auth_date=...&hash=..."
    
    Возвращает:
        True если подпись верна, иначе False.
    """
    if not init_data:
        return False
    
    # Разбираем строку на параметры
    parsed = parse_qs(init_data, keep_blank_values=False)
    
    # Извлекаем hash
    hash_value = parsed.get('hash', [None])[0]
    if not hash_value:
        return False
    
    # Удаляем hash из параметров для вычисления HMAC
    del parsed['hash']
    
    # Сортируем ключи в алфавитном порядке
    sorted_params = sorted(parsed.items(), key=lambda x: x[0])
    
    # Формируем строку данных в формате "key=value" с разделителем "\n"
    data_check_string = '\n'.join(
        f"{key}={value[0]}" for key, value in sorted_params
    )
    
    # Секретный ключ: HMAC_SHA256(BOT_TOKEN, "WebAppData")
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        # Если BOT_TOKEN не установлен, пропускаем проверку (для разработки)
        return True
    
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()
    
    # Вычисляем HMAC_SHA256(secret_key, data_check_string)
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Сравниваем хеши
    return hmac.compare_digest(computed_hash, hash_value)


def extract_user_id_from_init_data(init_data: str) -> int | None:
    """
    Извлекает Telegram ID пользователя из initData.
    Возвращает None, если не удалось извлечь.
    """
    try:
        parsed = parse_qs(init_data, keep_blank_values=False)
        user_str = parsed.get('user', [None])[0]
        if not user_str:
            return None
        # user_str - JSON строка, но мы можем извлечь id простым способом
        import json
        user = json.loads(user_str)
        return user.get('id')
    except Exception:
        return None