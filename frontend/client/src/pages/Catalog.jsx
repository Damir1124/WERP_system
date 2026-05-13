import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'

const TYPE_LABELS = {
  'WE': 'Вода',
  'B20L': 'Вода 20л с тарой',
  'BT': 'Тара',
  'CL': 'Кулер',
  'AR': 'Аксессуар',
}

const TYPE_ICONS = {
  'WE': '💧',
  'B20L': '🪣',
  'BT': '🫙',
  'CL': '🧊',
  'AR': '🔧',
}

export default function Catalog() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await clientApi.getProducts()
      setProducts(Array.isArray(data) ? data : [])
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
          <div className="text-3xl mb-2">💧</div>
          <p className="text-gray-500">Загрузка каталога...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <div className="text-red-600 mb-3">Ошибка: {error}</div>
        <button onClick={loadProducts} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
          Повторить
        </button>
      </div>
    )
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Каталог товаров</h2>

      {products.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-3">📭</div>
          <p>Товары не найдены</p>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((product) => (
            <div
              key={product.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">
                    {TYPE_ICONS[product.type_product] || '📦'}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{product.name}</h3>
                    <p className="text-xs text-gray-500">
                      {TYPE_LABELS[product.type_product] || product.type_product_display}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-blue-600">
                    {(product.price || 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400">сум / шт.</p>
                </div>
              </div>
              <button
                onClick={() => navigate(`/order/${product.id}`, { state: { product } })}
                className="mt-3 w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors text-sm"
              >
                Заказать
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
