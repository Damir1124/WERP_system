import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Trip() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [openingShift, setOpeningShift] = useState(false)
  const [openingTrip, setOpeningTrip] = useState(false)
  const [fullLoaded, setFullLoaded] = useState(0)

  useEffect(() => {
    loadCurrentTrip()
  }, [])

  const loadCurrentTrip = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.getCurrentTrip()
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenShift = async () => {
    setOpeningShift(true)
    try {
      await api.openShift()
      await loadCurrentTrip()
    } catch (err) {
      alert('Ошибка при открытии смены: ' + err.message)
    } finally {
      setOpeningShift(false)
    }
  }

  const handleOpenTrip = async () => {
    setOpeningTrip(true)
    try {
      await api.openTrip(fullLoaded)
      await loadCurrentTrip()
    } catch (err) {
      alert('Ошибка при открытии рейса: ' + err.message)
    } finally {
      setOpeningTrip(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Загрузка информации о рейсе...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">Ошибка: {error}</div>
        <button onClick={loadCurrentTrip} className="px-4 py-2 bg-indigo-600 text-white rounded-md">
          Повторить
        </button>
      </div>
    )
  }

  // Нет активной смены
  if (!data?.active_shift) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Смена не открыта</h3>
        <p className="text-gray-600 mb-6">Откройте смену, чтобы начать работу</p>
        <button
          onClick={handleOpenShift}
          disabled={openingShift}
          className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
        >
          {openingShift ? 'Открываем...' : '🟢 Открыть смену'}
        </button>
      </div>
    )
  }

  // Смена открыта, но нет активного рейса
  if (!data?.active_trip) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Рейс не открыт</h3>
        <p className="text-gray-600 mb-6">Смена #{data.shift_id} открыта. Укажите количество баклажек и начните рейс.</p>
        <div className="max-w-xs mx-auto mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Загружено полных баклажек
          </label>
          <input
            type="number"
            min="0"
            value={fullLoaded}
            onChange={(e) => setFullLoaded(parseInt(e.target.value) || 0)}
            className="block w-full border border-gray-300 rounded-md shadow-sm px-3 py-2 text-center text-lg font-bold"
          />
        </div>
        <button
          onClick={handleOpenTrip}
          disabled={openingTrip}
          className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
        >
          {openingTrip ? 'Открываем...' : '🚚 Начать рейс'}
        </button>
      </div>
    )
  }

  const trip = data.trip
  const summary = data.summary || {}
  const orders = trip?.orders || []

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Мой рейс #{trip?.id}</h2>
          <p className="text-gray-600">Смена #{data.shift_id} • Активный рейс</p>
        </div>
        <button
          onClick={loadCurrentTrip}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
        >
          🔄 Обновить
        </button>
      </div>

      {/* Счётчики */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-500">Загружено</p>
          <p className="text-3xl font-bold text-blue-600">{summary.full_loaded ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-500">Доставлено</p>
          <p className="text-3xl font-bold text-green-600">{summary.delivered ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-500">Остаток в машине</p>
          <p className="text-3xl font-bold text-yellow-600">{summary.full_remain ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-500">Пустых в машине</p>
          <p className="text-3xl font-bold text-gray-600">{summary.empty_expected ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-500">Наличных</p>
          <p className="text-2xl font-bold text-green-700">{(summary.cash_expected ?? 0).toLocaleString()}</p>
          <p className="text-xs text-gray-400">сум</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <p className="text-sm text-gray-500">По карте</p>
          <p className="text-2xl font-bold text-blue-700">{(summary.card_expected ?? 0).toLocaleString()}</p>
          <p className="text-xs text-gray-400">сум</p>
        </div>
      </div>

      {/* Список заказов рейса */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            Заказы рейса ({orders.length})
          </h3>
        </div>
        <ul className="divide-y divide-gray-200">
          {orders.length === 0 ? (
            <li className="px-6 py-8 text-center text-gray-500">
              Нет заказов в рейсе. Возьмите заказы из пула.
            </li>
          ) : (
            orders.map((order) => (
              <li key={order.id} className="px-4 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900">
                        #{order.id} — {order.client_name || 'Без клиента'}
                      </span>
                      <StatusBadge status={order.status} />
                    </div>
                    <p className="text-sm text-gray-600">
                      {order.product_name} × {order.quantity} шт. — {(order.price || 0).toLocaleString()} сум
                    </p>
                    <p className="text-xs text-gray-400">
                      {order.payment_type_display} {order.container_op_display ? `• ${order.container_op_display}` : ''}
                    </p>
                  </div>
                  {order.status === 'PD' && (
                    <Link
                      to={`/order/${order.id}/confirm`}
                      className="ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                    >
                      Доставить
                    </Link>
                  )}
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    'PD': { label: 'Ожидает', cls: 'bg-yellow-100 text-yellow-800' },
    'DL': { label: 'Доставлен', cls: 'bg-green-100 text-green-800' },
    'CN': { label: 'Отменён', cls: 'bg-red-100 text-red-800' },
  }
  const s = map[status] || { label: status, cls: 'bg-gray-100 text-gray-800' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  )
}
