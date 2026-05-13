import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Shifts() {
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [opening, setOpening] = useState(false)

  useEffect(() => {
    loadShifts()
  }, [])

  const loadShifts = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getShifts()
      setShifts(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenShift = async () => {
    setOpening(true)
    try {
      const result = await api.openShift()
      alert(result.message || 'Смена открыта!')
      loadShifts()
    } catch (err) {
      alert('Ошибка при открытии смены: ' + err.message)
    } finally {
      setOpening(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Загрузка истории смен...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">Ошибка: {error}</div>
        <button onClick={loadShifts} className="px-4 py-2 bg-indigo-600 text-white rounded-md">
          Повторить
        </button>
      </div>
    )
  }

  const hasOpenShift = shifts.some(s => s.status === 'OP')

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Мои смены</h2>
          <p className="text-gray-600">История смен и рейсов</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadShifts}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            🔄
          </button>
          {!hasOpenShift && (
            <button
              onClick={handleOpenShift}
              disabled={opening}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
            >
              {opening ? 'Открываем...' : '🟢 Открыть смену'}
            </button>
          )}
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {shifts.length === 0 ? (
            <li className="px-6 py-8 text-center">
              <div className="text-gray-500 text-lg">У вас ещё нет смен</div>
              <button
                onClick={handleOpenShift}
                disabled={opening}
                className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
              >
                {opening ? 'Открываем...' : '🟢 Открыть первую смену'}
              </button>
            </li>
          ) : (
            shifts.map((shift) => (
              <li key={shift.id}>
                <div className="px-4 py-4 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-medium text-gray-900">
                          Смена #{shift.id} от {new Date(shift.date).toLocaleDateString('ru-RU')}
                        </p>
                        {/* status: 'OP' = открыта, 'CL' = закрыта */}
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          shift.status === 'OP'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {shift.status === 'OP' ? '🟢 Открыта' : '⚫ Закрыта'}
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-500">Наличные</p>
                          <p className="text-lg font-semibold text-gray-900">
                            {(shift.cash_total || 0).toLocaleString()} сум
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Безнал</p>
                          <p className="text-lg font-semibold text-gray-900">
                            {(shift.card_total || 0).toLocaleString()} сум
                          </p>
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-gray-400">
                        Открыта: {new Date(shift.opened_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                        {shift.closed_at && ` • Закрыта: ${new Date(shift.closed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <div className="text-right">
                        <p className="text-sm font-bold text-gray-900">
                          {((shift.cash_total || 0) + (shift.card_total || 0)).toLocaleString()} сум
                        </p>
                        <p className="text-xs text-gray-400">итого</p>
                      </div>
                    </div>
                  </div>

                  {/* Рейсы смены */}
                  {shift.trips && shift.trips.length > 0 && (
                    <div className="mt-3 border-t border-gray-100 pt-3">
                      <p className="text-xs text-gray-500 mb-2">Рейсы ({shift.trips.length}):</p>
                      <div className="space-y-1">
                        {shift.trips.map((trip) => (
                          <div key={trip.id} className="flex items-center justify-between text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
                            <span>Рейс #{trip.id} — загружено: {trip.full_loaded} шт.</span>
                            <span className={`px-1.5 py-0.5 rounded text-xs ${
                              trip.status === 'AC' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                            }`}>
                              {trip.status === 'AC' ? 'В пути' : 'Завершён'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
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
