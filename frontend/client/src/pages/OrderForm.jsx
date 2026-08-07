import { useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'

export default function OrderForm({ clientData }) {
  const { productId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const product = location.state?.product

  const [form, setForm] = useState({
    quantity: 1,
    payment_type: 'CASH',
    address: clientData?.address || '',
    note: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const totalPrice = product ? product.price * form.quantity : 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await clientApi.createOrder({
        product_id: parseInt(productId),
        quantity: parseInt(form.quantity),
        payment_type: form.payment_type,
        address: form.address,
        note: form.note,
      })
      const displayNum = result.display_number != null ? String(result.display_number).padStart(3, '0') : String(result.order_id)
      navigate('/orders', {
        state: { successMessage: `Заказ ${displayNum} создан! Ожидайте курьера.` }
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!product) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500 mb-4">Товар не найден</p>
        <button onClick={() => navigate('/')} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
          В каталог
        </button>
      </div>
    )
  }

  return (
    <div className="p-4">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-blue-600 text-sm mb-4"
      >
        ← Назад
      </button>

      <h2 className="text-xl font-bold text-gray-900 mb-4">Оформление заказа</h2>

      {/* Карточка товара */}
      <div className="bg-blue-50 rounded-xl p-4 mb-4 flex items-center gap-3">
        <div className="text-3xl">🪣</div>
        <div>
          <p className="font-semibold text-gray-900">{product.name}</p>
          <p className="text-blue-600 font-bold">{product.price.toLocaleString()} сум / шт.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Количество */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Количество
          </label>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setForm(p => ({ ...p, quantity: Math.max(1, p.quantity - 1) }))}
              className="w-10 h-10 rounded-full bg-gray-200 text-gray-700 font-bold text-lg flex items-center justify-center hover:bg-gray-300"
            >
              −
            </button>
            <span className="text-2xl font-bold text-gray-900 w-12 text-center">
              {form.quantity}
            </span>
            <button
              type="button"
              onClick={() => setForm(p => ({ ...p, quantity: p.quantity + 1 }))}
              className="w-10 h-10 rounded-full bg-blue-600 text-white font-bold text-lg flex items-center justify-center hover:bg-blue-700"
            >
              +
            </button>
          </div>
        </div>

        {/* Тип оплаты */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Способ оплаты
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { value: 'CASH', label: '💵 Наличные' },
              { value: 'CARD', label: '💳 Карта' },
            ].map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center justify-center p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                  form.payment_type === opt.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                    : 'border-gray-200 bg-white text-gray-700'
                }`}
              >
                <input
                  type="radio"
                  name="payment_type"
                  value={opt.value}
                  checked={form.payment_type === opt.value}
                  onChange={handleChange}
                  className="sr-only"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        {/* Адрес */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Адрес доставки
          </label>
          <input
            type="text"
            name="address"
            value={form.address}
            onChange={handleChange}
            placeholder="Введите адрес"
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Примечание */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Примечание (необязательно)
          </label>
          <textarea
            name="note"
            value={form.note}
            onChange={handleChange}
            rows={2}
            placeholder="Например: позвоните за 10 минут..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Итого */}
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Итого:</span>
            <span className="text-2xl font-bold text-blue-600">
              {totalPrice.toLocaleString()} сум
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {product.price.toLocaleString()} × {form.quantity} шт.
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-base"
        >
          {loading ? 'Оформляем...' : '✅ Подтвердить заказ'}
        </button>
      </form>
    </div>
  )
}
