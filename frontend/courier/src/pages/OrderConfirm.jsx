import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function OrderConfirm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    container_op: 'EXCHANGE',
    payment_type: 'CASH',
    note: ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      // Используем новый endpoint подтверждения заказа
      await api.confirmOrder(id, true, form.container_op, form.note)
      alert('Заказ подтверждён как доставленный!')
      navigate('/trip')
    } catch (error) {
      console.error('Failed to deliver order:', error)
      alert('Ошибка при подтверждении заказа: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Подтверждение заказа #{id}</h2>
        <p className="text-gray-600">Укажите детали доставки</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Действие с тарой
              </label>
              <div className="space-y-2">
                {[
                  { value: 'EXCHANGE', label: 'ОБМЕН', description: 'Полная ушла, пустая получена (+1 пустая в машину)' },
                  { value: 'SELL_WITH', label: 'ПРОДАЖА С ТАРОЙ', description: 'Продана с тарой (0 пустых)' },
                  { value: 'DEFECTIVE', label: 'БРАК', description: 'Брак возвращается (+1 бракованная в машину)' }
                ].map((option) => (
                  <div key={option.value} className="flex items-start">
                    <div className="flex items-center h-5">
                      <input
                        id={`container_op_${option.value}`}
                        name="container_op"
                        type="radio"
                        value={option.value}
                        checked={form.container_op === option.value}
                        onChange={handleChange}
                        className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300"
                      />
                    </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor={`container_op_${option.value}`} className="font-medium text-gray-700">
                        {option.label}
                      </label>
                      <p className="text-gray-500">{option.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Тип оплаты
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { value: 'CASH', label: 'Наличные', color: 'bg-yellow-100 text-yellow-800' },
                  { value: 'CARD', label: 'Карта', color: 'bg-green-100 text-green-800' },
                  { value: 'BONUS', label: 'Бонусы', color: 'bg-blue-100 text-blue-800' }
                ].map((option) => (
                  <div key={option.value} className="relative">
                    <input
                      id={`payment_type_${option.value}`}
                      name="payment_type"
                      type="radio"
                      value={option.value}
                      checked={form.payment_type === option.value}
                      onChange={handleChange}
                      className="sr-only"
                    />
                    <label
                      htmlFor={`payment_type_${option.value}`}
                      className={`cursor-pointer flex items-center justify-center px-3 py-2 border rounded-md text-sm font-medium ${
                        form.payment_type === option.value
                          ? `${option.color} border-transparent`
                          : 'bg-white border-gray-300 text-gray-900 hover:bg-gray-50'
                      }`}
                    >
                      {option.label}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="note" className="block text-sm font-medium text-gray-700 mb-2">
                Примечание (необязательно)
              </label>
              <textarea
                id="note"
                name="note"
                rows={3}
                value={form.note}
                onChange={handleChange}
                className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                placeholder="Например: клиент попросил оставить у двери..."
              />
            </div>
          </div>
        </div>

        <div className="px-4 py-3 bg-gray-50 text-right sm:px-6">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="mr-3 inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {loading ? 'Подтверждение...' : 'Подтвердить доставку'}
          </button>
        </div>
      </form>
    </div>
  )
}