import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Shifts() {
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadShifts()
  }, [])

  const loadShifts = async () => {
    try {
      const data = await api.getShifts()
      setShifts(data)
    } catch (error) {
      console.error('Failed to load shifts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenShift = async () => {
    try {
      await api.openShift()
      alert('Смена открыта!')
      loadShifts()
    } catch (error) {
      console.error('Failed to open shift:', error)
      alert('Ошибка при открытии смены')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Загрузка истории смен...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Мои смены</h2>
          <p className="text-gray-600">История смен и рейсов</p>
        </div>
        <button
          onClick={handleOpenShift}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Открыть новую смену
        </button>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {shifts.length === 0 ? (
            <li className="px-6 py-8 text-center">
              <div className="text-gray-500">У вас ещё нет смен</div>
              <button
                onClick={handleOpenShift}
                className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                Открыть первую смену
              </button>
            </li>
          ) : (
            shifts.map((shift) => (
              <li key={shift.id}>
                <div className="px-4 py-4 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <div className="ml-3">
                          <div className="flex items-center">
                            <p className="text-sm font-medium text-gray-900">
                              Смена от {new Date(shift.date).toLocaleDateString('ru-RU')}
                            </p>
                            <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              shift.status === 'OPEN' 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {shift.status === 'OPEN' ? 'Открыта' : 'Закрыта'}
                            </span>
                          </div>
                          <div className="mt-2 grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-sm text-gray-500">Наличные</p>
                              <p className="text-lg font-semibold text-gray-900">
                                {shift.cash_total?.toLocaleString() || 0} сум
                              </p>
                            </div>
                            <div>
                              <p className="text-sm text-gray-500">Безнал</p>
                              <p className="text-lg font-semibold text-gray-900">
                                {shift.card_total?.toLocaleString() || 0} сум
                              </p>
                            </div>
                          </div>
                          <div className="mt-2 text-sm text-gray-500">
                            <p>
                              Открыта: {new Date(shift.opened_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                              {shift.closed_at && ` • Закрыта: ${new Date(shift.closed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <button
                        onClick={() => alert(`Детали смены #${shift.id}`)}
                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        Детали
                      </button>
                    </div>
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