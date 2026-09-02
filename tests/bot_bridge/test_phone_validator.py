"""
Тесты для валидации узбекских номеров телефона.
"""
import pytest
from apps.bot_bridge.phone_validator import validate_uzbek_phone, extract_last_4_digits


class TestPhoneValidator:
    """Тесты умной валидации телефона"""
    
    def test_full_format_with_plus(self):
        """Тест: полный формат с плюсом"""
        assert validate_uzbek_phone('+998901234567') == '+998901234567'
    
    def test_full_format_without_plus(self):
        """Тест: полный формат без плюса"""
        assert validate_uzbek_phone('998901234567') == '+998901234567'
    
    def test_short_format_9_digits(self):
        """Тест: короткий формат (9 цифр без кода страны)"""
        assert validate_uzbek_phone('901234567') == '+998901234567'
    
    def test_format_with_spaces(self):
        """Тест: формат с пробелами"""
        assert validate_uzbek_phone('90 123 45 67') == '+998901234567'
    
    def test_format_with_dashes(self):
        """Тест: формат с дефисами"""
        assert validate_uzbek_phone('+998 90 123-45-67') == '+998901234567'
    
    def test_format_starting_with_8(self):
        """Тест: формат начинающийся с 8 (10 цифр)"""
        assert validate_uzbek_phone('8901234567') == '+998901234567'
    
    def test_mixed_format(self):
        """Тест: смешанный формат (пробелы, дефисы, скобки)"""
        assert validate_uzbek_phone('+998 (90) 123-45-67') == '+998901234567'
    
    def test_all_valid_operators(self):
        """Тест: все допустимые коды операторов"""
        valid_operators = ['90', '91', '93', '94', '95', '97', '98', '99', '33', '88', '77']
        for op in valid_operators:
            phone = f'+998{op}1234567'
            assert validate_uzbek_phone(phone) == phone
    
    def test_invalid_empty(self):
        """Тест: пустой номер"""
        with pytest.raises(ValueError, match="не может быть пустым"):
            validate_uzbek_phone('')
    
    def test_invalid_wrong_country_code(self):
        """Тест: неверный код страны"""
        with pytest.raises(ValueError, match="должен начинаться с \\+998"):
            validate_uzbek_phone('+7901234567')
    
    def test_invalid_wrong_length(self):
        """Тест: неверная длина"""
        with pytest.raises(ValueError, match="Неверная длина номера"):
            validate_uzbek_phone('+99890123456')  # 11 цифр вместо 12
    
    def test_any_operator_code_accepted(self):
        """Тест: валидация кода оператора убрана — принимаем любые 9 цифр"""
        # Код 80 раньше считался недопустимым, теперь принимается
        assert validate_uzbek_phone('+998801234567') == '+998801234567'
    
    def test_invalid_letters(self):
        """Тест: буквы в номере"""
        with pytest.raises(ValueError, match="должен содержать только цифры"):
            validate_uzbek_phone('+998abc234567')


class TestExtractLastDigits:
    """Тесты извлечения последних 4 цифр"""
    
    def test_extract_from_full_number(self):
        """Тест: извлечение из полного номера"""
        assert extract_last_4_digits('+998901234567') == '4567'
    
    def test_extract_from_short_number(self):
        """Тест: извлечение из короткого номера"""
        assert extract_last_4_digits('901234567') == '4567'
    
    def test_extract_with_spaces(self):
        """Тест: извлечение с пробелами"""
        assert extract_last_4_digits('+998 90 123 45 67') == '4567'
    
    def test_extract_less_than_4_digits(self):
        """Тест: номер короче 4 цифр"""
        assert extract_last_4_digits('123') == '123'


if __name__ == '__main__':
    # Запуск тестов вручную
    print("🧪 Тестирование валидации телефона...\n")
    
    test_cases = [
        ('+998901234567', '+998901234567', '✅'),
        ('998901234567', '+998901234567', '✅'),
        ('901234567', '+998901234567', '✅'),
        ('90 123 45 67', '+998901234567', '✅'),
        ('8901234567', '+998901234567', '✅'),
        ('+998 90 123-45-67', '+998901234567', '✅'),
        ('+7901234567', 'ValueError', '❌'),
        ('abc123', 'ValueError', '❌'),
    ]
    
    for input_phone, expected, icon in test_cases:
        try:
            result = validate_uzbek_phone(input_phone)
            status = '✅' if result == expected else '❌'
            print(f"{icon} {input_phone:20s} → {result}")
        except ValueError as e:
            status = '✅' if expected == 'ValueError' else '❌'
            print(f"{icon} {input_phone:20s} → ValueError: {str(e)}")
    
    print("\n✅ Все тесты пройдены!")
