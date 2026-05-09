import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Pool() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPool()
  }, [])

  const loadPool = async () => {
    try {
      const data = await api.getPool()
      setOrders(data)
    } catch (error) {
      console.error('Failed to load pool:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAssign = async (orderId) => {
    try {
      // Здесь будет вызов API для взятия заказа
      alert(`Заказ ${orderId} взят в работу`)
      loadPool()
    } catch (error) {
      console.error('Failed to assign order:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Загрузка пула заказов...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Пул заказов</h2>
        <p className="text-gray-600">Заказы ожидающие назначения курьеру</p>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {orders.length === 0 ? (
            <li className="px-6 py-4 text-center text-gray-500">
              Нет заказов в пуле
            </li>
          ) : (
            orders.map((order) => (
              <li key={order.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">
                          {order.client?.name || 'Без имени'}
                        </p>
                        <p className="text-sm text-gray-500">
                          {order.client?.address || 'Адрес не указан'}
                        </p>
                        <div className="mt-1 flex items-center space-x-4">
                          <span className="text-sm text-gray-700">
                            {order.product?.name}: {order.quantity} шт.
                          </span>
                          <span className="text-sm font-medium text-gray-900">
                            {order.price?.toLocaleString()} сум
                          </span>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            order.payment_type === 'CASH' 
                              ? 'bg-yellow-100 text-yellow-800' 
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {order.payment_type === 'CASH' ? 'Наличные' : 'Карта'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <button
                      onClick={() => handleAssign(order.id)}
                      className="ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      Взять заказ
                    </button>
                  </div>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}