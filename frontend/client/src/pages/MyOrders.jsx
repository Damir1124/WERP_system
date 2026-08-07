import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { clientApi } from '../api.js'

const STATUS_MAP = {
  'PD': { label: 'Ожидает', icon: '⏳', cls: 'bg-yellow-100 text-yellow-800' },
  'DL': { label: 'Доставлен', icon: '✅', cls: 'bg-green-100 text-green-800' },
  'CN': { label: 'Отменён', icon: '❌', cls: 'bg-red-100 text-red-800' },
}

const PAYMENT_MAP = {
  'CH': 'Наличные',
  'CD': 'Карта',
  'BS': 'Бонус',
  'CASH': 'Наличные',
  'CARD': 'Карта',
  'BONUS': 'Бонус',
}

export default function MyOrders() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const location = useLocation()
  const successMessage = location.state?.successMessage

  useEffect(() => {
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

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="text-3xl mb-2">📦</div>
          <p className="text-gray-500">Загрузка заказов...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-900">Мои заказы</h2>
        <button
          onClick={loadOrders}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          🔄 Обновить
        </button>
      </div>

      {successMessage && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 font-medium">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          Ошибка: {error}
        </div>
      )}

      {orders.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-5xl mb-3">📭</div>
          <p className="text-gray-500 font-medium">У вас пока нет заказов</p>
          <p className="text-gray-400 text-sm mt-1">Перейдите в каталог, чтобы сделать заказ</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => {
            const statusInfo = STATUS_MAP[order.status] || { label: order.status, icon: '?', cls: 'bg-gray-100 text-gray-800' }
            return (
              <div key={order.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-xs text-gray-400">Заказ {order.display_number != null ? String(order.display_number).padStart(3, '0') : String(order.id)}</span>
                    <h3 className="font-semibold text-gray-900 mt-0.5">
                      {order.product_name}
                    </h3>
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${statusInfo.cls}`}>
                    {statusInfo.icon} {statusInfo.label}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-400">Количество:</span>
                    <span className="ml-1 font-medium text-gray-900">{order.quantity} шт.</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Сумма:</span>
                    <span className="ml-1 font-bold text-blue-600">
                      {(order.price || 0).toLocaleString()} сум
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Оплата:</span>
                    <span className="ml-1 text-gray-700">
                      {PAYMENT_MAP[order.payment_type] || order.payment_type_display}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Дата:</span>
                    <span className="ml-1 text-gray-700">
                      {new Date(order.created_at).toLocaleDateString('ru-RU')}
                    </span>
                  </div>
                </div>

                {order.status === 'PD' && (
                  <div className="mt-3 p-2 bg-yellow-50 rounded-lg text-xs text-yellow-700">
                    ⏳ Ваш заказ ожидает назначения курьера
                  </div>
                )}

                {order.status === 'DL' && order.delivered_at && (
                  <div className="mt-3 p-2 bg-green-50 rounded-lg text-xs text-green-700">
                    ✅ Доставлен {new Date(order.delivered_at).toLocaleString('ru-RU', {
                      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
                    })}
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
