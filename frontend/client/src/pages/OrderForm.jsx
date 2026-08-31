import { useState, useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'
import { t, tF } from '../i18n.js'
import { ICONS, TYPE_ICONS } from '../icons/water-icons.jsx'
import LocationPicker from '../components/LocationPicker.jsx'
import DeliveryAddressSummary from '../components/DeliveryAddressSummary.jsx'
import { resolveDeliveryAddress } from '../utils/address.js'

export default function OrderForm({ clientData, lang = 'ru' }) {
  const { productId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const product = location.state?.product

  const [form, setForm] = useState({
    quantity: 1,
    payment_type: 'CASH',
    address: clientData?.address || '',
    note: '',
    phone: clientData?.phone || '',
    latitude: null,
    longitude: null,
  })
  const [savedAddresses, setSavedAddresses] = useState([])
  const [selectedAddressId, setSelectedAddressId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showMap, setShowMap] = useState(false)
  // Подсветка блока адреса при попытке оформить без адреса (scroll + shake)
  const [addrError, setAddrError] = useState(false)
  // Раскрывающийся блок «Изменить адрес»
  const [showAddressEditor, setShowAddressEditor] = useState(false)
  // Подсветка блока ввода адреса при клике «Изменить» (на 1.5 сек)
  const [editorHighlight, setEditorHighlight] = useState(false)

  // Загружаем сохранённые адреса клиента
  useEffect(() => {
    if (clientData?.phone) {
      clientApi
        .getAddresses(clientData.phone)
        .then((data) => setSavedAddresses(Array.isArray(data.addresses) ? data.addresses : []))
        .catch(() => setSavedAddresses([]))
    }
  }, [clientData?.phone])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSelectAddress = (addr) => {
    // Не вписываем текст в поле «Адрес доставки» — только подсвечиваем кнопку.
    // Адрес, координаты и лейбл берутся из выбранного сохранённого адреса через резолвер.
    setSelectedAddressId(addr.id)
    setForm((prev) => ({
      ...prev,
      address: '',
      latitude: addr.latitude,
      longitude: addr.longitude,
    }))
  }

  const handleLocationSelect = (lat, lon) => {
    setSelectedAddressId(null)
    setForm((prev) => ({ ...prev, latitude: lat, longitude: lon }))
  }

  const totalPrice = product ? product.price * form.quantity : 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.phone.trim()) {
      setError(t('phone_required', lang))
      return
    }
    // Единый резолвер: какой адрес реально уйдёт в заказ
    const resolved = resolveDeliveryAddress({
      address: form.address,
      latitude: form.latitude,
      longitude: form.longitude,
      selectedAddressId,
      savedAddresses,
    })
    if (resolved.isEmpty) {
      setAddrError(true)
      document.getElementById('delivery-address-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setTimeout(() => setAddrError(false), 1500)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await clientApi.createOrder({
        product_id: parseInt(productId),
        quantity: parseInt(form.quantity),
        payment_type: form.payment_type,
        address: resolved.text || '',
        note: form.note,
        latitude: resolved.lat,
        longitude: resolved.lon,
      })
      const displayNum = result.display_number != null ? String(result.display_number).padStart(3, '0') : String(result.order_id)
      navigate('/orders', {
        state: { successMessage: tF('order_created_success', lang, { num: displayNum }) },
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!product) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500 mb-4">{t('product_not_found', lang)}</p>
        <button onClick={() => navigate('/')} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
          {t('to_catalog', lang)}
        </button>
      </div>
    )
  }

  return (
    <div className="p-4">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-blue-600 text-sm mb-4"
      >
        {t('back', lang)}
      </button>

      <h2 className="text-xl font-bold text-gray-900 mb-4">{t('order_title', lang)}</h2>

      {/* Карточка товара */}
      <div className="bg-blue-50 rounded-xl p-4 mb-4 flex items-center gap-3">
        <div className="text-3xl text-blue-600">
          {(() => {
            const TypeIcon = TYPE_ICONS[product.type_product] || ICONS.logo
            return <TypeIcon size={32} />
          })()}
        </div>
        <div>
          <p className="font-semibold text-gray-900">{product.name}</p>
          <p className="text-blue-600 font-bold">{product.price.toLocaleString()} {t('per_unit', lang)}</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Адрес доставки — сразу после товара: что заказываю → куда доставить → как оплатить */}
      <div className="mb-4">
        <DeliveryAddressSummary
          address={form.address}
          latitude={form.latitude}
          longitude={form.longitude}
          selectedAddressId={selectedAddressId}
          savedAddresses={savedAddresses}
          onEdit={() => {
            setShowAddressEditor(true)
            setEditorHighlight(true)
            setTimeout(() => setEditorHighlight(false), 1500)
          }}
          highlightError={addrError}
          lang={lang}
        />
      </div>

      {showAddressEditor && (
        <div id="delivery-address-editor" className={`mb-4 space-y-4 bg-white rounded-2xl shadow-soft border border-gray-100 p-4 ${editorHighlight ? 'address-editor-highlight' : ''}`}>
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
              <ICONS.location size={14} /> {t('delivery_address', lang)}
            </h4>
            <button
              type="button"
              onClick={() => setShowAddressEditor(false)}
              className="text-xs text-gray-500 font-medium"
            >
              {t('cancel', lang)}
            </button>
          </div>

          {/* Сохранённые адреса */}
          {savedAddresses.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('choose_saved_address', lang)}
              </label>
              <div className="space-y-2">
                {savedAddresses.map((addr) => (
                  <button
                    key={addr.id}
                    type="button"
                    onClick={() => handleSelectAddress(addr)}
                    className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                      selectedAddressId === addr.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 bg-white text-gray-700'
                    }`}
                  >
                    {addr.label && <span className="font-medium">{addr.label}: </span>}
                    {addr.address_text || `${addr.latitude}, ${addr.longitude}`}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Адрес: ввод нового */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('delivery_address', lang)}
            </label>
            <input
              type="text"
              name="address"
              value={form.address}
              onChange={(e) => {
                handleChange(e)
                setSelectedAddressId(null)
              }}
              placeholder={t('address_placeholder', lang)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={() => setShowMap(true)}
              className="mt-2 w-full py-2.5 border border-blue-300 text-blue-700 font-medium rounded-lg"
            >
              {t('use_geolocation', lang)}
            </button>
            {(form.latitude != null || form.longitude != null) && (
              <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                <ICONS.location size={12} /> {form.latitude?.toFixed?.(6) ?? form.latitude}, {form.longitude?.toFixed?.(6) ?? form.longitude}
              </p>
            )}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Количество */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('quantity', lang)}
          </label>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setForm((p) => ({ ...p, quantity: Math.max(1, p.quantity - 1) }))}
              className="w-10 h-10 rounded-full bg-gray-200 text-gray-700 font-bold text-lg flex items-center justify-center hover:bg-gray-300"
            >
              −
            </button>
            <span className="text-2xl font-bold text-gray-900 w-12 text-center">
              {form.quantity}
            </span>
            <button
              type="button"
              onClick={() => setForm((p) => ({ ...p, quantity: p.quantity + 1 }))}
              className="w-10 h-10 rounded-full bg-blue-600 text-white font-bold text-lg flex items-center justify-center hover:bg-blue-700"
            >
              +
            </button>
          </div>
        </div>

        {/* Тип оплаты */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {t('payment_type', lang)}
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { value: 'CASH', label: t('pay_cash', lang) },
              { value: 'CARD', label: t('pay_card', lang) },
            ].map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center justify-center p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                  form.payment_type === opt.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                    : 'border-gray-200 bg-white text-gray-700'
                }`}
              >
                <input
                  type="radio"
                  name="payment_type"
                  value={opt.value}
                  checked={form.payment_type === opt.value}
                  onChange={handleChange}
                  className="sr-only"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        {/* Телефон */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('phone', lang)}
          </label>
          <input
            type="tel"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            placeholder={t('phone_placeholder', lang)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Примечание */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('note', lang)}
          </label>
          <textarea
            name="note"
            value={form.note}
            onChange={handleChange}
            rows={2}
            placeholder={t('note_placeholder', lang)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Итого */}
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-600">{t('total', lang)}:</span>
            <span className="text-2xl font-bold text-blue-600">
              {totalPrice.toLocaleString()} сум
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {product.price.toLocaleString()} × {form.quantity} шт.
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-base"
        >
          {loading ? t('processing', lang) : t('confirm_order', lang)}
        </button>
      </form>

      {showMap && (
        <LocationPicker
          initialPosition={
            form.latitude != null && form.longitude != null
              ? { lat: form.latitude, lon: form.longitude }
              : null
          }
          onLocationSelect={handleLocationSelect}
          onClose={() => setShowMap(false)}
          lang={lang}
        />
      )}
    </div>
  )
}
