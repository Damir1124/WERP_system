import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Colleagues() {
  const [colleagues, setColleagues] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadColleagues()
  }, [])

  const loadColleagues = async () => {
    try {
      const data = await api.getColleagues()
      setColleagues(data)
    } catch (error) {
      console.error('Failed to load colleagues:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Загрузка списка коллег...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Мои коллеги</h2>
        <p className="text-gray-600">Курьеры с открытой сменой сегодня</p>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {colleagues.length === 0 ? (
            <li className="px-6 py-8 text-center">
              <div className="text-gray-500">Сегодня нет активных курьеров</div>
              <p className="mt-2 text-sm text-gray-500">Будьте первым кто откроет смену!</p>
            </li>
          ) : (
            colleagues.map((colleague) => (
              <li key={colleague.id}>
                <div className="px-4 py-4 sm:px-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                            <span className="text-indigo-800 font-medium">
                              {colleague.full_name?.charAt(0) || 'К'}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="flex items-center">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {colleague.full_name || 'Курьер'}
                            </p>
                            <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              ONLINE
                            </span>
                          </div>
                          <div className="mt-1 flex flex-col sm:flex-row sm:flex-wrap sm:space-x-6">
                            <div className="flex items-center text-sm text-gray-500">
                              <svg className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                              </svg>
                              {colleague.delivered_today || 0} доставлено сегодня
                            </div>
                            {colleague.phone && (
                              <div className="flex items-center text-sm text-gray-500 mt-1 sm:mt-0">
                                <svg className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                  <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
                                </svg>
                                {colleague.phone}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">
                          {colleague.cash_total?.toLocaleString() || 0} сум
                        </p>
                        <p className="text-xs text-gray-500">наличные</p>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">Как это работает?</h3>
            <div className="mt-2 text-sm text-blue-700">
              <p>В этом списке отображаются только курьеры у которых сегодня открыта смена (status=OPEN).</p>
              <p className="mt-1">Данные обновляются в реальном времени — вы видите актуальные показатели коллег.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}