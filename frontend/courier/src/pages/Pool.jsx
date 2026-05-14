import { useState, useEffect } from 'react'
import { api } from '../api.js'

// Форма создания нового заказа курьером
function CreateOrderModal({ onClose, onCreated }) {
  const [products, setProducts] = useState([])
  const [clients, setClients] = useState([])
  const [form, setForm] = useState({
    product_id: '',
    client_search: '',
    client_id: '',
    client_name: '',
    quantity: 1,
    payment_type: 'CH',
    note: '',
  })
  const [loading, setLoading] = useState(false)
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      const data = await api.getProducts()
      setProducts(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Ошибка загрузки продуктов:', err)
    } finally {
      setLoadingProducts(false)
    }
  }

  const searchClients = async () => {
    if (!form.client_search.trim()) return
    try {
      const data = await api.searchClients(form.client_search, '')
      setClients(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Ошибка поиска клиентов:', err)
    }
  }

  const selectClient = (client) => {
    setForm(prev => ({
      ...prev,
      client_id: client.id,
      client_name: client.name,
      client_search: client.name,
    }))
    setClients([])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.product_id) {
      setError('Выберите продукт')
      return
    }
    setLoading(true)
    setError(null)
    try {
      // Получаем активный рейс
      const tripData = await api.getCurrentTrip()
      if (!tripData?.active_trip) {
        setError('Нет активного рейса. Сначала откройте смену и рейс.')
        return
      }
      const tripId = tripData.trip?.id
      if (!tripId) {
        setError('Не удалось получить ID рейса')
        return
      }

      await api.createOrder({
        trip: tripId,
        client: form.client_id || null,
        product: parseInt(form.product_id),
        quantity: parseInt(form.quantity),
        payment_type: form.payment_type,
        note: form.note,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-end">
      <div className="bg-white w-full rounded-t-2xl max-h-[90vh] overflow-y-auto">
        {/* Заголовок */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 sticky top-0 bg-white">
          <h3 className="text-base font-bold text-gray-900">Создать заказ</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-600"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Продукт */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Продукт *
            </label>
            {loadingProducts ? (
              <div className="text-sm text-gray-400">Загрузка...</div>
            ) : (
              <select
                value={form.product_id}
                onChange={(e) => setForm(prev => ({ ...prev, product_id: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white"
                required
              >
                <option value="">Выберите продукт</option>
                {products.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {(p.price || 0).toLocaleString()} сум
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Клиент */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Клиент (необязательно)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={form.client_search}
                onChange={(e) => setForm(prev => ({ ...prev, client_search: e.target.value, client_id: '', client_name: '' }))}
                placeholder="Поиск по имени или телефону"
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2.5 text-sm"
              />
              <button
                type="button"
                onClick={searchClients}
                className="px-3 py-2.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"
              >
                🔍
              </button>
            </div>
            {clients.length > 0 && (
              <div className="mt-1 border border-gray-200 rounded-lg overflow-hidden">
                {clients.map(c => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => selectClient(c)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 border-b border-gray-100 last:border-0"
                  >
                    <span className="font-medium">{c.name}</span>
                    <span className="text-gray-400 ml-2">{c.phone}</span>
                  </button>
                ))}
              </div>
            )}
            {form.client_id && (
              <p className="mt-1 text-xs text-green-600">✓ Выбран: {form.client_name}</p>
            )}
          </div>

          {/* Количество */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Количество
            </label>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setForm(p => ({ ...p, quantity: Math.max(1, p.quantity - 1) }))}
                className="w-10 h-10 rounded-full bg-gray-200 text-gray-700 font-bold text-lg flex items-center justify-center"
              >
                −
              </button>
              <span className="text-2xl font-bold text-gray-900 w-10 text-center">
                {form.quantity}
              </span>
              <button
                type="button"
                onClick={() => setForm(p => ({ ...p, quantity: p.quantity + 1 }))}
                className="w-10 h-10 rounded-full bg-indigo-600 text-white font-bold text-lg flex items-center justify-center"
              >
                +
              </button>
            </div>
          </div>

          {/* Тип оплаты */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Тип оплаты
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 'CH', label: '💵 Наличные' },
                { value: 'CD', label: '💳 Карта' },
                { value: 'BS', label: '🎁 Бонус' },
              ].map(opt => (
                <label
                  key={opt.value}
                  className={`flex items-center justify-center p-2.5 rounded-lg border-2 cursor-pointer text-sm transition-colors ${
                    form.payment_type === opt.value
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700 font-medium'
                      : 'border-gray-200 bg-white text-gray-700'
                  }`}
                >
                  <input
                    type="radio"
                    name="payment_type"
                    value={opt.value}
                    checked={form.payment_type === opt.value}
                    onChange={(e) => setForm(prev => ({ ...prev, payment_type: e.target.value }))}
                    className="sr-only"
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          {/* Примечание */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Примечание
            </label>
            <textarea
              value={form.note}
              onChange={(e) => setForm(prev => ({ ...prev, note: e.target.value }))}
              rows={2}
              placeholder="Необязательно..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-indigo-600 text-white font-semibold rounded-xl disabled:opacity-50 text-base"
          >
            {loading ? 'Создаём...' : '✅ Создать заказ'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default function Pool() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [assigning, setAssigning] = useState(null)
  const [showCreateForm, setShowCreateForm] = useState(false)

  useEffect(() => {
    loadPool()
  }, [])

  const loadPool = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getPool()
      setOrders(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAssign = async (orderId) => {
    setAssigning(orderId)
    try {
      const result = await api.assignOrder(orderId)
      loadPool()
    } catch (err) {
      alert('Ошибка: ' + err.message)
    } finally {
      setAssigning(null)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="text-gray-400 text-sm">Загрузка пула заказов...</div>
      </div>
    )
  }

  return (
    <div>
      {/* Заголовок + кнопки */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Пул заказов</h2>
          <p className="text-xs text-gray-500">Свободные заказы от клиентов</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadPool}
            className="w-9 h-9 flex items-center justify-center bg-gray-100 rounded-full text-gray-600"
          >
            🔄
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-1 px-3 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg"
          >
            ＋ Создать
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
          <button onClick={loadPool} className="ml-2 underline">Повторить</button>
        </div>
      )}

      {/* Список заказов */}
      <div className="space-y-2">
        {orders.length === 0 ? (
          <div className="bg-white rounded-xl p-8 text-center">
            <div className="text-4xl mb-2">📭</div>
            <p className="text-gray-500 font-medium">Нет заказов в пуле</p>
            <p className="text-gray-400 text-sm mt-1">Новые заказы от клиентов появятся здесь</p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="mt-4 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg"
            >
              ＋ Создать заказ вручную
            </button>
          </div>
        ) : (
          orders.map((order) => (
            <div key={order.id} className="bg-white rounded-xl p-3 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-xs font-bold text-gray-400">#{order.id}</span>
                    <span className="text-sm font-semibold text-gray-900 truncate">
                      {order.client_name || 'Без клиента'}
                    </span>
                    <PaymentBadge type={order.payment_type} />
                  </div>
                  <p className="text-xs text-gray-500 truncate mb-1">
                    {order.product_name}: {order.quantity} шт.
                  </p>
                  <p className="text-sm font-bold text-indigo-600">
                    {(order.price || 0).toLocaleString()} сум
                  </p>
                </div>
                <button
                  onClick={() => handleAssign(order.id)}
                  disabled={assigning === order.id}
                  className="flex-shrink-0 px-3 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg disabled:opacity-50"
                >
                  {assigning === order.id ? '...' : '✋ Взять'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Модальная форма создания заказа */}
      {showCreateForm && (
        <CreateOrderModal
          onClose={() => setShowCreateForm(false)}
          onCreated={() => {
            loadPool()
            setShowCreateForm(false)
          }}
        />
      )}
    </div>
  )
}

function PaymentBadge({ type }) {
  const map = {
    'CH': { label: 'Нал', cls: 'bg-yellow-100 text-yellow-700' },
    'CD': { label: 'Карта', cls: 'bg-green-100 text-green-700' },
    'BS': { label: 'Бонус', cls: 'bg-blue-100 text-blue-700' },
    'CASH': { label: 'Нал', cls: 'bg-yellow-100 text-yellow-700' },
    'CARD': { label: 'Карта', cls: 'bg-green-100 text-green-700' },
    'BONUS': { label: 'Бонус', cls: 'bg-blue-100 text-blue-700' },
  }
  const s = map[type] || { label: type || '?', cls: 'bg-gray-100 text-gray-600' }
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  )
}
