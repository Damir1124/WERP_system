import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'
import { t } from '../i18n.js'
import { isWater, minQty, decrementQty } from '../cart.jsx'
import { ICONS } from '../icons/water-icons.jsx'
import LocationPicker from '../components/LocationPicker.jsx'
import DeliveryAddressSummary from '../components/DeliveryAddressSummary.jsx'
import { resolveDeliveryAddress } from '../utils/address.js'

const FALLBACK_IMG = 'data:image/svg+xml;utf8,' +
  '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">' +
  '<rect width="120" height="120" fill="#e0f2fe"/>' +
  '<text x="60" y="68" font-size="42" text-anchor="middle">💧</text></svg>'

/**
 * Редактирование заказа (только PENDING — пока курьер не назначен).
 * Можно менять состав товаров и количество.
 *
 * Детали заказа берём из истории (OrderSerializer.items содержит product_id и product_name),
 * каталог — из API продуктов.
 */
export default function OrderEdit({ lang = 'ru' }) {
  const { id: orderId } = useParams()
  const navigate = useNavigate()
  const [products, setProducts] = useState([]) // {id, name, price, image_url}
  const [items, setItems] = useState([]) // [{product_id, product_name, price, quantity}]
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  // Адрес и примечание (редактируются в конце формы)
  const [address, setAddress] = useState('')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)
  const [note, setNote] = useState('')
  const [showMap, setShowMap] = useState(false)
  // Подсветка блока адреса при попытке сохранить без адреса (scroll + shake)
  const [addrError, setAddrError] = useState(false)
  // Подсветка карточки ввода адреса при клике «Изменить» (на 1.5 сек)
  const [editorHighlight, setEditorHighlight] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [ordersData, catalog] = await Promise.all([
        clientApi.getOrders(),
        clientApi.getProducts(),
      ])
      const orders = Array.isArray(ordersData) ? ordersData : []
      const catalogList = Array.isArray(catalog) ? catalog : (catalog?.results || [])
      setProducts(catalogList)

      const order = orders.find((o) => String(o.id) === String(orderId))
      if (!order) {
        setError('Заказ не найден')
        setLoading(false)
        return
      }

      if (order.status !== 'PD') {
        setError(t('edit_only_pending', lang))
        setLoading(false)
        return
      }

      // Адрес и примечание текущего заказа
      setAddress(order.delivery_address_text || '')
      setLatitude(order.delivery_latitude != null ? parseFloat(order.delivery_latitude) : null)
      setLongitude(order.delivery_longitude != null ? parseFloat(order.delivery_longitude) : null)
      setNote(order.note || '')

      // Позиции текущего заказа (product = ID товара)
      const existing = (order.items || []).map((it) => ({
        product_id: it.product,
        product_name: it.product_name || '—',
        price: it.quantity > 0 && it.price ? Math.round(it.price / it.quantity) : 0,
        quantity: it.quantity,
      })).filter((e) => e.product_id != null)

      const existingIds = new Set(existing.map((e) => e.product_id))
      const rest = catalogList
        .filter((p) => !existingIds.has(p.id))
        .map((p) => ({
          product_id: p.id,
          product_name: p.name,
          price: p.price,
          quantity: 0,
        }))
      setItems([...existing, ...rest])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const setQty = (productId, qty) => {
    setItems((prev) =>
      prev.map((it) =>
        it.product_id === productId ? { ...it, quantity: Math.max(0, qty) } : it
      )
    )
  }

  const totalPrice = items.reduce((sum, it) => sum + it.price * it.quantity, 0)

  const handleSave = async () => {
    const selected = items.filter((it) => it.quantity > 0)
    if (selected.length === 0) {
      setError(t('cart_empty', lang))
      return
    }
    // Единый резолвер: какой адрес реально уйдёт в заказ
    const resolved = resolveDeliveryAddress({ address, latitude, longitude })
    if (resolved.isEmpty) {
      setAddrError(true)
      document.getElementById('delivery-address-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      setTimeout(() => setAddrError(false), 1500)
      return
    }
    setSaving(true)
    setError(null)
    try {
      await clientApi.updateOrder(orderId, {
        items: selected.map((it) => ({ product_id: it.product_id, quantity: it.quantity })),
        address: resolved.text || '',
        latitude: resolved.lat,
        longitude: resolved.lon,
        note: note || '',
      })
      navigate('/orders', { state: { successMessage: t('order_updated', lang) } })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="text-3xl mb-2"><ICONS.edit size={32} /></div>
          <p className="text-gray-500">{t('loading', lang)}</p>
        </div>
      </div>
    )
  }

  if (error && items.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={() => navigate('/orders')} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
          {t('my_orders', lang)}
        </button>
      </div>
    )
  }

  return (
    <div className="p-4 pb-28">
      <button onClick={() => navigate(-1)} className="text-blue-600 text-sm mb-4">
        {t('back', lang)}
      </button>
      <h2 className="text-xl font-bold text-gray-900 mb-1">{t('edit_order_title', lang)}</h2>
      <p className="text-xs text-gray-400 mb-4">{t('edit_only_pending', lang)}</p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Адрес доставки — сразу под заголовком, до состава заказа */}
      <div className="mb-4 space-y-4">
        <DeliveryAddressSummary
          address={address}
          latitude={latitude}
          longitude={longitude}
          onEdit={() => {
            setShowMap(true)
            setEditorHighlight(true)
            setTimeout(() => setEditorHighlight(false), 1500)
          }}
          highlightError={addrError}
          lang={lang}
        />
        {/* Карточка редактирования адреса (в потоке формы) */}
        <div id="delivery-address-editor" className={`bg-white rounded-2xl shadow-soft border border-gray-100 p-4 ${editorHighlight ? 'address-editor-highlight' : ''}`}>
          <h3 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-1.5">
            <ICONS.location size={16} /> {t('delivery_address', lang)}
          </h3>
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder={t('address_placeholder', lang)}
            className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={() => setShowMap(true)}
            className="mt-2 w-full py-2.5 border border-blue-300 text-blue-700 font-medium rounded-xl text-sm"
          >
            {t('use_geolocation', lang)}
          </button>
          {(latitude != null || longitude != null) && (
            <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
              <ICONS.location size={12} /> {latitude?.toFixed?.(6) ?? latitude}, {longitude?.toFixed?.(6) ?? longitude}
            </p>
          )}
        </div>
      </div>

      {/* Список товаров каталога со степперами */}
      <div className="space-y-3">
        {items.map((it) => {
          const product = products.find((p) => p.id === it.product_id)
          const imgUrl = product?.image_url || FALLBACK_IMG
          return (
            <div key={it.product_id} className="bg-white rounded-2xl shadow-soft border border-gray-100 p-3 flex gap-3 items-center">
              <div className="w-14 h-14 rounded-xl bg-blue-50 overflow-hidden shrink-0">
                <img src={imgUrl} alt={it.product_name} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.src = FALLBACK_IMG }} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 text-sm leading-snug">{it.product_name}</h3>
                <p className="text-blue-600 font-bold text-sm mt-0.5">{it.price.toLocaleString()} сум</p>
              </div>
              <div className="flex items-center gap-1 bg-blue-50 border border-blue-200 rounded-lg p-0.5 shrink-0">
                <button
                  onClick={() => setQty(it.product_id, decrementQty(products.find((p) => p.id === it.product_id), it.quantity))}
                  className="w-7 h-7 rounded-md bg-white text-blue-700 font-bold text-sm shadow-sm active:scale-95 transition-all"
                >
                  −
                </button>
                <span className="w-6 text-center text-sm font-bold text-gray-900">{it.quantity}</span>
                <button
                  onClick={() => setQty(it.product_id, it.quantity + 1)}
                  className="w-7 h-7 rounded-md bg-blue-600 text-white font-bold text-sm shadow-sm active:scale-95 transition-all"
                >
                  +
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Примечание */}
      <div className="mt-4 bg-white rounded-2xl shadow-soft border border-gray-100 p-4">
        <h3 className="text-base font-bold text-gray-900 mb-3">{t('note', lang)}</h3>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          placeholder={t('note_placeholder', lang)}
          className="w-full border border-gray-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      {/* Итого + сохранить */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-soft z-50">
        <div className="flex justify-between items-center mb-3">
          <span className="text-gray-600 text-sm">{t('total', lang)}:</span>
          <span className="text-xl font-extrabold text-blue-600">{totalPrice.toLocaleString()} сум</span>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-3.5 bg-gradient-to-r from-blue-500 to-blue-700 text-white font-bold rounded-xl shadow-soft glow-blue hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all"
        >
          {saving ? t('processing', lang) : (<span className="flex items-center justify-center gap-1.5"><ICONS.save size={14} /> {t('save_changes', lang)}</span>)}
        </button>
      </div>

      {showMap && (
        <LocationPicker
          initialPosition={latitude != null && longitude != null ? { lat: latitude, lon: longitude } : null}
          onLocationSelect={(lat, lon) => { setLatitude(lat); setLongitude(lon) }}
          onClose={() => setShowMap(false)}
          lang={lang}
        />
      )}
    </div>
  )
}