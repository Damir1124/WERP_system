/**
 * Поле ввода телефона (Узбекистан, +998).
 *
 * Логика перенесена из frontend/courier/src/pages/OrderCreate.jsx:
 * - вход всегда хранит только «тело» номера (9 цифр) без +998;
 * - произвольный ввод нормализуется: "+998 95 555 55 55", "998955555555",
 *   "895555555" (старый формат с 8), "955555555" и т.д.;
 * - отображается с маской "95 555 55 55";
 * - валидация: ровно 9 цифр (код оператора НЕ проверяется).
 *
 * @param {Object} props
 * @param {string} props.phone — «тело» номера (9 цифр), управляемый извне
 * @param {Function} props.onChange — callback с «телом» номера
 * @param {Function} props.onBlur — callback при потере фокуса (для проверки)
 * @param {string} props.placeholder — плейсхолдер
 * @param {string} props.error — текст ошибки (показывается под полем)
 * @param {boolean} props.required
 */

// Приведение произвольного ввода к «телу» номера (9 цифр)
export function extractPhoneBody(rawInput) {
  let digits = (rawInput || '').replace(/\D/g, '')

  if (digits.startsWith('998') && digits.length > 9) {
    // Убираем код страны 998, если он был вставлен вместе с номером
    digits = digits.slice(3)
  } else if (digits.length === 10 && digits.startsWith('8')) {
    // Старый формат: 8 + 9 цифр
    digits = digits.slice(1)
  }

  return digits.slice(0, 9)
}

// Форматирование тела номера для отображения: "95 555 55 55"
export function formatUzPhoneBody(digits) {
  const parts = []
  if (digits.length > 0) parts.push(digits.slice(0, 2))
  if (digits.length > 2) parts.push(digits.slice(2, 5))
  if (digits.length > 5) parts.push(digits.slice(5, 7))
  if (digits.length > 7) parts.push(digits.slice(7, 9))
  return parts.join(' ')
}

// Валидация: ровно 9 цифр (код оператора не проверяем)
export function isValidUzPhoneBody(digits) {
  return digits.length === 9
}

// Полный номер: "+998XXXXXXXXX" либо null
export function validateAndNormalizePhone(phone) {
  if (!isValidUzPhoneBody(phone)) return null
  return '+998' + phone
}

export default function PhoneInput({
  phone,
  onChange,
  onBlur,
  placeholder = '95 555 55 55',
  error,
  required = false,
  autoComplete = 'tel-national',
}) {
  const handleChange = (e) => {
    onChange(extractPhoneBody(e.target.value))
  }

  return (
    <div>
      <div className="flex items-center border border-gray-300 rounded-xl bg-white overflow-hidden focus-within:ring-2 focus-within:ring-blue-500">
        <span className="px-3 py-2.5 text-sm font-semibold text-gray-500 border-r border-gray-200 bg-gray-50 select-none">
          +998
        </span>
        <input
          type="tel"
          inputMode="numeric"
          autoComplete={autoComplete}
          placeholder={placeholder}
          value={formatUzPhoneBody(phone || '')}
          onChange={handleChange}
          onBlur={onBlur}
          required={required}
          className="flex-1 px-3 py-2.5 text-sm border-0 outline-none"
        />
      </div>
      {error && (
        <p className="text-xs text-red-600 mt-1">{error}</p>
      )}
    </div>
  )
}