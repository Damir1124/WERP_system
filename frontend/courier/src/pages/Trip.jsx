import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Trip() {
  const [trip, setTrip] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCurrentTrip()
  }, [])

  const loadCurrentTrip = async () => {
    try {
      const data = await api.getCurrentTrip()
      setTrip(data)
    } catch (error) {
      console.error('Failed to load current trip:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Загрузка информации о рейсе...</div>
      </div>
    )
  }

  if (!trip) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900">Нет активного рейса</h3>
        <p className="mt-2 text-gray-600">Создайте новый рейс в смене</p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Мой рейс</h2>
        <p className="text-gray-600">Информация о текущем рейсе и счётчики</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Загружено полных</h3>
          <p className="text-3xl font-bold text-blue-600">{trip.full_loaded || 0}</p>
          <p className="text-sm text-gray-500 mt-2">Баклажек в машине</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Доставлено</h3>
          <p className="text-3xl font-bold text-green-600">{trip.delivered_count || 0}</p>
          <p className="text-sm text-gray-500 mt-2">Заказов выполнено</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Остаток в машине</h3>
          <p className="text-3xl font-bold text-yellow-600">
            {(trip.full_loaded || 0) - (trip.delivered_count || 0) - (trip.full_returned || 0)}
          </p>
          <p className="text-sm text-gray-500 mt-2">Полных баклажек осталось</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Пустых в машине</h3>
          <p className="text-3xl font-bold text-gray-600">{trip.empty_received || 0}</p>
          <p className="text-sm text-gray-500 mt-2">Из EXCHANGE-заказов</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Брак</h3>
          <p className="text-3xl font-bold text-red-600">{trip.defective_received || 0}</p>
          <p className="text-sm text-gray-500 mt-2">Из DEFECTIVE-заказов</p>
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Расчётные показатели</h3>
        </div>
        <div className="border-t border-gray-200 px-4 py-5 sm:p-0">
          <dl className="sm:divide-y sm:divide-gray-200">
            <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Пустых должно быть</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {trip.empty_expected || 0} (кол-во EXCHANGE заказов в рейсе)
              </dd>
            </div>
            <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Наличных должно быть</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {(trip.cash_expected || 0).toLocaleString()} сум
              </dd>
            </div>
            <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">По карте должно быть</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {(trip.card_expected || 0).toLocaleString()} сум
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  )
}