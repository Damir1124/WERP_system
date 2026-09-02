"""
Утилита для валидации узбекских номеров телефона.
Поддерживает различные форматы ввода и автоматически приводит к стандарту +998XXXXXXXXX.
"""
import re
from typing import Tuple


def validate_uzbek_phone(phone: str) -> str:
    """
    Умная валидация узбекского номера телефона.
    
    Поддерживаемые форматы ввода:
        +998901234567 → +998901234567
        998901234567  → +998901234567
        901234567     → +998901234567
        90 123 45 67  → +998901234567
        8901234567    → +998901234567
        +998 90 123-45-67 → +998901234567
    
    Args:
        phone: Номер телефона в любом формате
        
    Returns:
        str: Номер в формате +998XXXXXXXXX
        
    Raises:
        ValueError: Если номер невалиден
        
    Examples:
        >>> validate_uzbek_phone('+998901234567')
        '+998901234567'
        >>> validate_uzbek_phone('901234567')
        '+998901234567'
        >>> validate_uzbek_phone('90 123 45 67')
        '+998901234567'
    """
    if not phone:
        raise ValueError("Номер телефона не может быть пустым")
    
    # Удаляем все символы кроме цифр и +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Удаляем + в начале для обработки
    if phone.startswith('+'):
        phone = phone[1:]
    
    # Если начинается с 8, заменяем на 998
    if phone.startswith('8') and len(phone) == 10:
        phone = '998' + phone[1:]
    
    # Если начинается с 9 (без кода страны), добавляем 998
    if phone.startswith('9') and len(phone) == 9:
        phone = '998' + phone
    
    # Проверяем, что начинается с 998
    if not phone.startswith('998'):
        raise ValueError("Номер должен начинаться с +998 (узбекский код)")
    
    # Проверяем длину (998 + 9 цифр = 12)
    if len(phone) != 12:
        raise ValueError(f"Неверная длина номера: {len(phone)} цифр (должно быть 12)")
    
    # Проверяем, что все символы — цифры
    if not phone.isdigit():
        raise ValueError("Номер должен содержать только цифры")
    
    # Валидация кода оператора намеренно убрана: принимаем любые 9 цифр
    # после +998 (коды операторов меняются, появляются новые MVNO).

    return '+' + phone


def format_phone_display(phone: str) -> str:
    """
    Форматирует номер для красивого отображения.
    
    Args:
        phone: Номер в формате +998XXXXXXXXX
        
    Returns:
        str: Номер в формате +998 XX XXX XX XX
        
    Examples:
        >>> format_phone_display('+998901234567')
        '+998 90 123 45 67'
    """
    if not phone or len(phone) != 13:
        return phone
    
    return f"{phone[:4]} {phone[4:6]} {phone[6:9]} {phone[9:11]} {phone[11:]}"


def extract_last_4_digits(phone: str) -> str:
    """
    Извлекает последние 4 цифры номера для использования как имени клиента.
    
    Args:
        phone: Номер телефона
        
    Returns:
        str: Последние 4 цифры
        
    Examples:
        >>> extract_last_4_digits('+998901234567')
        '4567'
    """
    digits = re.sub(r'\D', '', phone)
    return digits[-4:] if len(digits) >= 4 else digits
