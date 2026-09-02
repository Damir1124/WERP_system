// src/components/DeliveryAddressSummary.jsx
// Единый визуальный ответ на вопрос «куда привезут заказ».
// Три состояния:
//   — адрес не указан: спокойная нейтральная строка «Адрес не указан»;
//   — после нажатия/ошибки (highlightError): «Укажите адрес» с красным акцентом;
//   — адрес указан: компактная синяя карточка с текстом адреса.
// Используется в Cart.jsx (sticky-футер), OrderForm.jsx, OrderEdit.jsx.
import { ICONS } from '../icons/water-icons.jsx'
import { t } from '../i18n.js'
import { resolveDeliveryAddress, formatDeliveryAddress } from '../utils/address.js'

export default function DeliveryAddressSummary({
  address,
  latitude,
  longitude,
  selectedAddressId,
  savedAddresses,
  onEdit,
  highlightError = false,
  compact = false,
  lang = 'ru',
  anchorId = 'delivery-address-anchor',
}) {
  const resolved = resolveDeliveryAddress({ address, latitude, longitude, selectedAddressId, savedAddresses })
  const text = formatDeliveryAddress(resolved)

  if (resolved.isEmpty) {
    // Состояние «не указан»: спокойное → «Укажите адрес» при ошибке.
    // Под заголовком — подсвеченная подсказка «нажмите, чтобы указать адрес».
    return (
      <button
        type="button"
        onClick={onEdit}
        id={anchorId}
        className={`w-full flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-all ${
          highlightError
            ? 'border-red-300 bg-red-50 shake-once'
            : 'border-gray-200 bg-gray-50'
        }`}
      >
        <span className={`flex items-center justify-center w-7 h-7 rounded-full shrink-0 ${highlightError ? 'bg-red-100 text-red-500' : 'bg-white text-gray-400'}`}>
          <ICONS.location size={15} />
        </span>
        <span className="flex-1 min-w-0">
          <span className={`block text-sm font-medium ${highlightError ? 'text-red-600' : 'text-gray-500'}`}>
            {highlightError ? t('specify_address', lang) : t('address_not_selected', lang)}
          </span>
          <span className={`block text-xs font-semibold ${highlightError ? 'text-red-400' : 'text-blue-500'}`}>
            {t('address_not_selected_hint', lang)}
          </span>
        </span>
        <span className={`text-base ${highlightError ? 'text-red-400' : 'text-gray-300'}`}>›</span>
      </button>
    )
  }

  return (
    <div className={`rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 text-white ${compact ? 'px-3 py-2' : 'px-3.5 py-2.5'} shadow-soft`}>
      <div className="flex items-center gap-2.5">
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-white/20 shrink-0">
          <ICONS.location size={15} />
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] uppercase tracking-wide text-blue-100 font-semibold leading-none mb-0.5">
            {t('where_delivery', lang)}
          </p>
          <p className="font-semibold leading-snug break-words text-sm">{text}</p>
        </div>
        {onEdit && (
          <button
            type="button"
            onClick={onEdit}
            className="shrink-0 text-[11px] font-semibold bg-white text-blue-600 px-2.5 py-1 rounded-md active:scale-95"
          >
            {t('change_address', lang)}
          </button>
        )}
      </div>
    </div>
  )
}