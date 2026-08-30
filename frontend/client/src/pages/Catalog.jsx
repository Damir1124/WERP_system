import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { clientApi } from '../api.js'
import { t, tF } from '../i18n.js'
import { useCart, isWater, minQty, decrementQty } from '../cart.jsx'
import { ICONS, TYPE_ICONS } from '../icons/water-icons.jsx'

const FALLBACK_IMG = 'data:image/svg+xml;utf8,' +
  '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">' +
  '<rect width="120" height="120" fill="#e0f2fe"/>' +
  '<text x="60" y="68" font-size="42" text-anchor="middle">💧</text></svg>'

const PAGE_SIZE = 20

export default function Catalog({ lang = 'ru' }) {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const navigate = useNavigate()
  const cart = useCart()

  // Регистрируем товары в корзине (для отображения данных позиций)
  useEffect(() => {
    if (products.length > 0) cart.registerProducts(products)
  }, [products])

  const loadProducts = async (loadOffset = 0, append = false) => {
    setLoading(true)
    setError(null)
    try {
      const data = await clientApi.getProductsPaginated(loadOffset, PAGE_SIZE)
      const list = Array.isArray(data) ? data : (data?.results || [])
      setProducts((prev) => (append ? [...prev, ...list] : list))
      setHasMore(Array.isArray(data) ? false : !!data?.next)
      setOffset(loadOffset)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts(0, false)
  }, [])

  const loadMore = () => {
    if (!hasMore || loading) return
    loadProducts(offset + PAGE_SIZE, true)
  }

  const productQty = (id) => cart.cart[id] || 0

  return (
    <div className="p-4 pb-24">
      <h2 className="text-xl font-bold text-gray-900 mb-4">{t('catalog_title', lang)}</h2>

      {error && (
        <div className="p-4 text-center">
          <div className="text-red-600 mb-3">{t('catalog_error', lang)}: {error}</div>
          <button onClick={() => loadProducts(0, false)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
            {t('retry', lang)}
          </button>
        </div>
      )}

      {loading && products.length === 0 ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="text-3xl mb-2"><ICONS.logo size={32} /></div>
            <p className="text-gray-500">{t('catalog_loading', lang)}</p>
          </div>
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-3"><ICONS.empty size={40} /></div>
          <p>{t('catalog_empty', lang)}</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {products.map((product) => {
            const qty = productQty(product.id)
            const imgUrl = product.image_url || FALLBACK_IMG
            return (
              <div
                key={product.id}
                className="bg-white rounded-2xl shadow-soft border border-gray-100 overflow-hidden flex flex-col"
              >
                {/* Фото */}
                <div className="aspect-square bg-blue-50 flex items-center justify-center overflow-hidden relative">
                  <img
                    src={imgUrl}
                    alt={product.name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={(e) => { e.currentTarget.src = FALLBACK_IMG }}
                  />
                  {/* Иконка типа товара */}
                  {(() => {
                    const TypeIcon = TYPE_ICONS[product.type_product] || ICONS.logo
                    return (
                      <span className="absolute top-2 left-2 w-8 h-8 rounded-full bg-white/90 shadow-sm flex items-center justify-center text-blue-600">
                        <TypeIcon size={18} />
                      </span>
                    )
                  })()}
                </div>

                {/* Название */}
                <div className="p-3 flex-1">
                  <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">
                    {product.name}
                  </h3>
                  <p className="text-lg font-extrabold text-blue-600 mt-1">
                    {(product.price || 0).toLocaleString()}
                    <span className="text-xs font-medium text-gray-400 ml-1">сум</span>
                  </p>
                </div>

                {/* Кнопка Купить / степпер. Вода 19л (19W) — минимум 2 бутылки */}
                <div className="px-3 pb-3">
                  {qty === 0 ? (
                    <button
                      onClick={() => cart.add(product, minQty(product))}
                      className="w-full py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-xl shadow-soft glow-blue hover:opacity-90 active:scale-[0.98] transition-all"
                    >
                      {t('buy', lang)}
                    </button>
                  ) : (
                    <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-xl p-1">
                      <button
                        onClick={() => cart.setQuantity(product.id, decrementQty(product, qty))}
                        className="w-9 h-9 rounded-lg bg-white text-blue-700 font-bold text-lg shadow-sm hover:bg-gray-50 active:scale-95 transition-all"
                      >
                        −
                      </button>
                      <span className="text-base font-bold text-gray-900 min-w-6 text-center">
                        {qty}
                      </span>
                      <button
                        onClick={() => cart.add(product, 1)}
                        className="w-9 h-9 rounded-lg bg-blue-600 text-white font-bold text-lg shadow-sm hover:bg-blue-700 active:scale-95 transition-all"
                      >
                        +
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Пагинация — кнопка «Загрузить ещё» */}
      {hasMore && !loading && (
        <button
          onClick={loadMore}
          className="mt-4 w-full py-3 bg-white border border-blue-200 text-blue-600 font-medium rounded-xl shadow-soft hover:bg-blue-50 transition-all"
        >
          {t('load_more', lang)}…
        </button>
      )}
      {loading && products.length > 0 && (
        <div className="text-center text-gray-400 text-sm py-4"><ICONS.logo size={16} /> {t('catalog_loading', lang)}</div>
      )}

      {/* Плавающая кнопка корзины — выше нижней навигации */}
      {!cart.isEmpty && (
        <button
          onClick={() => navigate('/cart')}
          className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-6 py-3.5 bg-gradient-to-r from-blue-500 to-blue-700 text-white font-bold rounded-full shadow-lg glow-blue active:scale-95 transition-transform"
        >
          <span className="text-xl"><ICONS.cart size={20} /></span>
          <span>{tF('cart_items', lang, { n: cart.totalCount })}</span>
        </button>
      )}
    </div>
  )
}
