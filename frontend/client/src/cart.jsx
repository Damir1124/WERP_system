import { createContext, useContext, useEffect, useState } from 'react'

// ─── Вода 19л (type_product='19W') — минимальный заказ 2 бутылки ────────────
export const MIN_WATER_QTY = 2
export function isWater(product) {
  return product?.type_product === '19W'
}
export function minQty(product) {
  return isWater(product) ? MIN_WATER_QTY : 1
}
// «−» в степпере: не опускаемся ниже минимума (на минимуме — удаляем позицию)
export function decrementQty(product, currentQty) {
  const min = minQty(product)
  if (currentQty <= min) return 0
  return currentQty - 1
}

// ─── Корзина на клиенте (localStorage + глобальный Context) ────────────────
// Формат хранения: { productId: quantity }
// Дополнительно хранит snapshot товара для отображения: { products: { [id]: product } }

const CART_KEY = 'client_cart'
const PRODUCTS_KEY = 'client_cart_products'

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || {}
  } catch {
    return {}
  }
}

function readProducts() {
  try {
    return JSON.parse(localStorage.getItem(PRODUCTS_KEY)) || {}
  } catch {
    return {}
  }
}

function writeCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart))
}

function writeProducts(products) {
  localStorage.setItem(PRODUCTS_KEY, JSON.stringify(products))
}

// ─── Context ─────────────────────────────────────────────────────────────────
const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [cart, setCart] = useState(readCart)
  const [products, setProducts] = useState(readProducts)

  useEffect(() => {
    writeCart(cart)
  }, [cart])

  useEffect(() => {
    writeProducts(products)
  }, [products])

  const registerProducts = (productList) => {
    setProducts((prev) => {
      const next = { ...prev }
      for (const p of productList) {
        next[p.id] = p
      }
      return next
    })
  }

  const add = (product, qty = 1) => {
    setCart((prev) => ({
      ...prev,
      [product.id]: (prev[product.id] || 0) + qty,
    }))
    setProducts((prev) => ({ ...prev, [product.id]: product }))
  }

  const setQuantity = (productId, qty) => {
    setCart((prev) => {
      const next = { ...prev }
      if (qty <= 0) {
        delete next[productId]
      } else {
        next[productId] = qty
      }
      return next
    })
  }

  const remove = (productId) => {
    setCart((prev) => {
      const next = { ...prev }
      delete next[productId]
      return next
    })
  }

  const clear = () => {
    setCart({})
    setProducts({})
  }

  // Товары в корзине с данными
  const items = Object.entries(cart)
    .map(([id, qty]) => {
      const product = products[Number(id)]
      return product ? { product, quantity: qty } : null
    })
    .filter(Boolean)

  const totalCount = items.reduce((sum, it) => sum + it.quantity, 0)
  const totalPrice = items.reduce((sum, it) => sum + it.product.price * it.quantity, 0)
  const isEmpty = totalCount === 0

  const value = {
    cart,
    items,
    totalCount,
    totalPrice,
    isEmpty,
    add,
    setQuantity,
    remove,
    clear,
    registerProducts,
  }

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

// Хук для доступа к глобальной корзине (общий экземпляр для всего приложения)
export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) {
    throw new Error('useCart must be used within CartProvider')
  }
  return ctx
}