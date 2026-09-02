import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'
import { t, tF } from '../i18n.js'
import { useCart, decrementQty } from '../cart.jsx'
import { ICONS } from '../icons/water-icons.jsx'
import PhoneInput, { extractPhoneBody, validateAndNormalizePhone } from '../components/PhoneInput.jsx'
import LocationPicker from '../components/LocationPicker.jsx'

const FALLBACK_IMG = 'data:image/svg+xml;utf8,' +
  '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">' +
  '<rect width="120" height="120" fill="#e0f2fe"/>' +
  '<text x="60" y="68" font-size="42" text-anchor="middle">💧</text></svg>'

export default function Cart({ clientData, lang = 'ru' }) {
  const cart = useCart()
  const navigate = useNavigate()
  const [paymentType, setPaymentType] = useState('CASH')
  const [address, setAddress] = useState(clientData?.address || '')
  const [phone, setPhone] = useState(clientData?.phone ? extractPhoneBody(clientData.phone) : '')
  const [phoneError, setPhoneError] = useState(null)
  const [note, setNote] = useState('')
  const [showMap, setShowMap] = useState(false)
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)
  const [selectedAddressId, setSelectedAddressId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [savedAddresses, setSavedAddresses] = useState([])

  // Загружаем сохранённые адреса клиента
  useEffect(() => {
    if (clientData?.phone) {
      clientApi
        .getAddresses(clientData.phone)
        .then((data) => setSavedAddresses(Array.isArray(data.addresses) ? data.addresses : []))
        .catch(() => setSavedAddresses([]))
    }
  }, [clientData?.phone])

  const handleLocationSelect = (lat, lon) => {
    setLatitude(lat)
    setLongitude(lon)
    setSelectedAddressId(null)
    // Не вписываем локацию в поле адреса — координаты уже есть,
    // ниже отображается индикатор «📍 Локация - ...». Иначе в карточке заказа
    // будет дублирование «Location | Локация - lat, lon».
    setAddress('')
  }

  const handleSelectAddress = (addr) => {
    // Не вписываем текст в поле «Адрес доставки» — только подсвечиваем кнопку.
    // Адрес и координаты берутся из выбранного сохранённого адреса при оформлении.
    setSelectedAddressId(addr.id)
    setLatitude(addr.latitude)
    setLongitude(addr.longitude)
  }

  // Отображение адреса: если есть текст — текст, иначе «Локация - lat, lon»
  const formatAddress = (addr) => {
    if (addr.address_text) return addr.address_text
    if (addr.latitude != null && addr.longitude != null) {
      return `Локация - ${addr.latitude}, ${addr.longitude}`
    }
    return 'Локация'
  }

  // Проверка телефона при потере фокуса
  const handlePhoneBlur = () => {
    if (phone.length === 0) {
      setPhoneError(null)
      return
    }
    if (!validateAndNormalizePhone(phone)) {
      setPhoneError(t('phone_invalid', lang))
    } else {
      setPhoneError(null)
      // Обновляем телефон в профиле клиента
      const normalized = validateAndNormalizePhone(phone)
      if (clientData?.id && normalized !== clientData.phone) {
        clientApi
          .updateProfile({ client_id: clientData.id, phone: normalized })
          .catch(() => {})
      }
    }
  }

  const handleCheckout = async (e) => {
    e.preventDefault()
    // Валидация телефона
    const normalizedPhone = validateAndNormalizePhone(phone)
    if (!normalizedPhone) {
      setPhoneError(t('phone_invalid', lang))
      return
    }

    // Если выбран сохранённый адрес — берём адрес и координаты из него
    let finalAddress = address
    let finalLat = latitude
    let finalLon = longitude
    if (selectedAddressId) {
      const selected = savedAddresses.find((a) => a.id === selectedAddressId)
      if (selected) {
        // Если у сохранённого адреса нет текста — оставляем адрес пустым,
        // только координаты (иначе будет «Location | Локация - lat, lon»)
        finalAddress = selected.address_text || ''
        finalLat = selected.latitude
        finalLon = selected.longitude
      }
    }

    if (!finalAddress.trim() && (finalLat == null || finalLon == null)) {
      setError(t('address_required', lang))
      return
    }
    if (cart.items.length === 0) return

    setLoading(true)
    setError(null)
    try {
      const result = await clientApi.createOrder({
        items: cart.items.map((it) => ({
          product_id: it.product.id,
          quantity: it.quantity,
        })),
        payment_type: paymentType,
        phone: normalizedPhone,
        address: finalAddress,
        note,
        latitude: finalLat,
        longitude: finalLon,
      })
      cart.clear()
      const displayNum = result.display_number != null
        ? String(result.display_number).padStart(3, '0')
        : String(result.order_id)
      navigate('/orders', {
        state: { successMessage: tF('order_created_success', lang, { num: displayNum }) },
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const totalPrice = cart.totalPrice

  if (cart.isEmpty) {
    return (
      <div className="p-4">
        <div className="text-center py-16">
          <div className="text-6xl mb-4"><ICONS.cart size={60} /></div>
          <p className="text-gray-500 font-medium text-lg">{t('cart_empty', lang)}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-6 px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-xl shadow-soft glow-blue"
          >
            {t('go_to_catalog', lang)}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="pb-28">
      {/* ─── Список позиций ─────────────────────────────────────────────────── */}
      <div className="p-4 pb-0">
        <h2 className="text-xl font-bold text-gray-900 mb-4">{t('cart_title', lang)}</h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {cart.items.map(({ product, quantity }) => {
            const imgUrl = product.image_url || FALLBACK_IMG
            const lineTotal = product.price * quantity
            return (
              <div
                key={product.id}
                className="bg-white rounded-2xl shadow-soft border border-gray-100 p-3 flex gap-3 items-center"
              >
                <div className="w-16 h-16 rounded-xl bg-blue-50 overflow-hidden shrink-0">
                  <img src={imgUrl} alt={product.name} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.src = FALLBACK_IMG }} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">
                    {product.name}
                  </h3>
                  <p className="text-gray-400 text-xs">{product.price.toLocaleString()} сум / шт.</p>
                  <p className="text-blue-600 font-bold text-sm mt-0.5">{lineTotal.toLocaleString()} сум</p>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0">
                  {/* Степпер */}
                  <div className="flex items-center gap-1 bg-blue-50 border border-blue-200 rounded-lg p-0.5">
                    <button
                      onClick={() => cart.setQuantity(product.id, decrementQty(product, quantity))}
                      className="w-7 h-7 rounded-md bg-white text-blue-700 font-bold text-sm shadow-sm active:scale-95 transition-all"
                    >
                      −
                    </button>
                    <span className="w-6 text-center text-sm font-bold text-gray-900">{quantity}</span>
                    <button
                      onClick={() => cart.add(product, 1)}
                      className="w-7 h-7 rounded-md bg-blue-600 text-white font-bold text-sm shadow-sm active:scale-95 transition-all"
                    >
                      +
                    </button>
                  </div>
                  {/* Удалить */}
                  <button
                    onClick={() => cart.remove(product.id)}
                    className="text-red-500 hover:text-red-600 text-xs font-medium flex items-center gap-1"
                  >
                    <ICONS.delete size={12} /> {t('remove_item', lang)}
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        {/* Очистить корзину */}
        <button
          onClick={() => cart.clear()}
          className="mt-4 w-full py-2 text-red-500 text-sm font-medium hover:text-red-600 transition-colors"
        >
          {t('clear_cart', lang)}
        </button>

        {/* ─── Поля оформления (в потоке, скроллируемые) ────────────────────── */}
        <div className="mt-5 space-y-4 bg-white rounded-2xl shadow-soft border border-gray-100 p-4">
          <h3 className="text-base font-bold text-gray-900 flex items-center gap-1.5"><ICONS.checklist size={16} /> {t('checkout', lang)}</h3>

          {/* Способ оплаты */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('payment_type', lang)}
            </label>
            <div className="flex gap-2">
              {[
                { value: 'CASH', label: t('pay_cash_short', lang) },
                { value: 'CARD', label: t('pay_card_short', lang) },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setPaymentType(opt.value)}
                  className={`flex-1 py-2 rounded-xl text-sm font-medium border-2 transition-all ${
                    paymentType === opt.value
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white text-gray-600'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Телефон */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('phone', lang)} *
            </label>
            <PhoneInput
              phone={phone}
              onChange={setPhone}
              onBlur={handlePhoneBlur}
              error={phoneError}
              required
            />
          </div>

          {/* Сохранённые адреса */}
          {savedAddresses.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('choose_saved_address', lang)}
              </label>
              <div className="space-y-1.5">
                {savedAddresses.map((addr) => (
                  <button
                    key={addr.id}
                    type="button"
                    onClick={() => handleSelectAddress(addr)}
                    className={`w-full text-left p-2.5 rounded-xl border-2 transition-all text-sm ${
                      selectedAddressId === addr.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 bg-white text-gray-700'
                    }`}
                  >
                    {addr.label && <span className="font-medium">{addr.label}: </span>}
                    {formatAddress(addr)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Адрес */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('delivery_address', lang)} *
            </label>
            <input
              type="text"
              value={address}
              onChange={(e) => {
                setAddress(e.target.value)
                setSelectedAddressId(null)
              }}
              placeholder={t('address_placeholder', lang)}
              className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={() => setShowMap(true)}
              className="mt-2 w-full py-2 border border-blue-300 text-blue-700 font-medium rounded-xl text-sm"
            >
              {t('use_geolocation', lang)}
            </button>
            {(latitude != null || longitude != null) && (
              <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                <ICONS.location size={12} /> Локация - {latitude?.toFixed?.(6) ?? latitude}, {longitude?.toFixed?.(6) ?? longitude}
              </p>
            )}
          </div>

          {/* Примечание */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('note', lang)}
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t('note_placeholder', lang)}
              className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* ─── Sticky-блок: только Итого + кнопка ─────────────────────────────── */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-3 shadow-soft z-50">
        <div className="flex justify-between items-center mb-3">
          <span className="text-gray-600 text-sm">{t('total_to_pay', lang)}:</span>
          <span className="text-2xl font-extrabold text-blue-600">{totalPrice.toLocaleString()} сум</span>
        </div>
        <button
          onClick={handleCheckout}
          disabled={loading}
          className="w-full py-3.5 bg-gradient-to-r from-blue-500 to-blue-700 text-white font-bold rounded-xl shadow-soft glow-blue hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all text-base"
        >
          {loading ? t('processing', lang) : t('checkout', lang)}
        </button>
      </div>

      {showMap && (
        <LocationPicker
          initialPosition={latitude != null && longitude != null ? { lat: latitude, lon: longitude } : null}
          onLocationSelect={handleLocationSelect}
          onClose={() => setShowMap(false)}
          lang={lang}
        />
      )}
    </div>
  )
}