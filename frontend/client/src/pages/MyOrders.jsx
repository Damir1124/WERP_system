import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'
import { t } from '../i18n.js'
import { useCart } from '../cart.jsx'
import { ICONS, STATUS_ICONS } from '../icons/water-icons.jsx'

const STATUS_MAP = {
  'PD': { key: 'status_pending', icon: STATUS_ICONS.pending, cls: 'bg-yellow-100 text-yellow-800' },
  'DL': { key: 'status_delivered', icon: STATUS_ICONS.delivered, cls: 'bg-green-100 text-green-800' },
  'CN': { key: 'status_cancelled', icon: STATUS_ICONS.cancelled, cls: 'bg-red-100 text-red-800' },
}

const PAYMENT_MAP = {
  'CH': 'pay_cash_short',
  'CD': 'pay_card_short',
  'BS': 'pay_bonus_short',
  'CASH': 'pay_cash_short',
  'CARD': 'pay_card_short',
  'BONUS': 'pay_bonus_short',
}

export default function MyOrders({ lang = 'ru' }) {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)
  const location = useLocation()
  const navigate = useNavigate()
  const cart = useCart()
  const successMessage = location.state?.successMessage

  useEffect(() => {
    // Если пришли сюда после оформления заказа (есть successMessage) —
    // гарантированно очищаем корзину (страховка, если cart.clear() в Cart не сработал)
    if (successMessage) {
      cart.clear()
    }
    loadOrders()
  }, [])

  const loadOrders = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await clientApi.getOrders()
      setOrders(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (order) => {
    if (!window.confirm(t('confirm_delete_order', lang))) return
    try {
      await clientApi.deleteOrder(order.id)
      setMessage(t('order_deleted', lang))
      setOrders((prev) => prev.filter((o) => o.id !== order.id))
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="text-3xl mb-2"><ICONS.orders size={32} /></div>
          <p className="text-gray-500">{t('orders_loading', lang)}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 pb-24">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-900">{t('my_orders', lang)}</h2>
        <button onClick={loadOrders} className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1.5">
          <ICONS.refresh size={14} /> {t('refresh', lang)}
        </button>
      </div>

      {(successMessage || message) && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 font-medium">
          {message || successMessage}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {t('catalog_error', lang)}: {error}
        </div>
      )}

      {orders.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-5xl mb-3"><ICONS.empty size={48} /></div>
          <p className="text-gray-500 font-medium">{t('no_orders', lang)}</p>
          <p className="text-gray-400 text-sm mt-1">{t('no_orders_hint', lang)}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => {
            const statusInfo = STATUS_MAP[order.status] || { key: null, label: order.status, icon: '?', cls: 'bg-gray-100 text-gray-800' }
            const statusLabel = statusInfo.key ? t(statusInfo.key, lang) : statusInfo.label
            const num = order.display_number != null ? String(order.display_number).padStart(3, '0') : String(order.id)
            const address = order.delivery_address_display || order.delivery_address_text || order.client_address || 'Location'
            const isPending = order.status === 'PD'
            return (
              <div key={order.id} className="bg-white rounded-2xl shadow-soft border border-gray-100 p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    {/* Номер заказа — крупно и жирно */}
                    <p className="text-lg font-extrabold text-gray-900">
                      {t('order_num', lang)}{' '}
                      <span className="text-blue-600">{num}</span>
                    </p>
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${statusInfo.cls}`}>
                    {(() => {
                      const StatusIcon = statusInfo.icon
                      return <StatusIcon size={12} />
                    })()}
                    {statusLabel}
                  </span>
                </div>

                {/* Состав (названия товаров) */}
                <div className="mb-2">
                  {Array.isArray(order.items) && order.items.length > 0 ? (
                    order.items.map((it) => (
                      <p key={it.id || it.product} className="text-sm text-gray-700">
                        • {it.product_name || it.product} × {it.quantity}
                      </p>
                    ))
                  ) : (
                    <p className="text-sm text-gray-700">• {order.product_name || '—'}</p>
                  )}
                </div>

                {/* Адрес доставки */}
                <div className="text-sm text-gray-600 mb-2">
                  <span className="text-gray-400">{t('address', lang)}:</span>{' '}
                  <span className="font-medium">{address}</span>
                </div>

                {/* Примечание — только если есть */}
                {order.note && (
                  <div className="text-sm text-gray-600 mb-2 flex items-start gap-1">
                    <span className="text-gray-400 shrink-0">{t('note', lang)}:</span>{' '}
                    <span className="font-medium">{order.note}</span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-400">{t('payment', lang)}:</span>{' '}
                    <span className="text-gray-700">{t(PAYMENT_MAP[order.payment_type] || 'pay_cash_short', lang)}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">{t('date', lang)}:</span>{' '}
                    <span className="text-gray-700">{new Date(order.created_at).toLocaleDateString('ru-RU')}</span>
                  </div>
                </div>

                {/* Сумма — крупно */}
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-gray-500 text-sm">{t('total', lang)}:</span>
                  <span className="text-xl font-extrabold text-blue-600">
                    {(order.total_price || 0).toLocaleString()} сум
                  </span>
                </div>

                {isPending && (
                  <div className="mt-2 p-2 bg-yellow-50 rounded-lg text-xs text-yellow-700">
                    {t('pending_hint', lang)}
                  </div>
                )}

                {order.status === 'DL' && order.delivered_at && (
                  <div className="mt-2 p-2 bg-green-50 rounded-lg text-xs text-green-700">
                    {t('delivered_at', lang)} {new Date(order.delivered_at).toLocaleString('ru-RU', {
                      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
                    })}
                  </div>
                )}

                {/* Редактировать / Удалить — только для PENDING */}
                {isPending && (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => navigate(`/order/${order.id}/edit`)}
                      className="flex-1 py-2.5 border border-blue-300 text-blue-700 font-medium rounded-xl text-sm hover:bg-blue-50 transition-colors flex items-center justify-center gap-1.5"
                    >
                      <ICONS.edit size={14} /> {t('edit_order', lang)}
                    </button>
                    <button
                      onClick={() => handleDelete(order)}
                      className="flex-1 py-2.5 border border-red-200 text-red-600 font-medium rounded-xl text-sm hover:bg-red-50 transition-colors flex items-center justify-center gap-1.5"
                    >
                      <ICONS.delete size={14} /> {t('delete_order', lang)}
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
