import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

// Иконки продуктов по типу
function productIcon(typeName = '') {
  const t = typeName.toLowerCase()
  if (t.includes('вода') || t.includes('b20l') || t.includes('water')) return '💧'
  if (t.includes('кулер') || t.includes('cooler')) return '🧊'
  return '📦'
}

// Stepper компонент
function Stepper({ value, onChange, color, onIncrement, onDecrement }) {
  return (
    <div className="stepper">
      <button
        type="button"
        className="st-btn"
        onClick={() => onDecrement ? onDecrement() : onChange(Math.max(0, value - 1))}
      >−</button>
      <span className="st-val" style={color ? { color } : {}}>{value}</span>
      <button
        type="button"
        className="st-btn"
        onClick={() => onIncrement ? onIncrement() : onChange(value + 1)}
      >+</button>
    </div>
  )
}

export default function OrderConfirm() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Состояние позиций: { [itemId]: { quantity, exchange_qty, sell_with_qty, defective_qty } }
  const [itemStates, setItemStates] = useState({})
  const [paymentType, setPaymentType] = useState('CH')
  const [bottlePrice, setBottlePrice] = useState(25000) // Дефолт 25000, перезаписывается из API

  // ── Состояние для добавления новых продуктов ──────────────────────────────────
  const [allProducts, setAllProducts] = useState([])       // все продукты из API
  const [selectedProductId, setSelectedProductId] = useState('')  // выбранный в селекторе
  const [newItemQty, setNewItemQty] = useState(1)          // количество для добавления
  const [extraItems, setExtraItems] = useState([])         // [{ product_id, product_name, price, quantity }]

  useEffect(() => {
    loadOrder()
  }, [id])

  // Загрузка всех продуктов из API (и для цены тары, и для селектора добавления)
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const products = await api.getProducts()
        setAllProducts(products)
        const bottle = products.find(p => p.id === 9 && p.type_product === 'BT')
        if (bottle) {
          setBottlePrice(bottle.price)
        }
      } catch (e) {
        console.error('Не удалось загрузить продукты', e)
      }
    }
    fetchProducts()
  }, [])

  const loadOrder = async () => {
    try {
      // Получаем данные заказа из текущего рейса
      const tripData = await api.getCurrentTrip()
      const orders = tripData?.trip?.orders || []
      const found = orders.find(o => String(o.id) === String(id))
      if (found) {
        setOrder(found)
        setPaymentType(found.payment_type || 'CH')
        // Инициализируем состояние позиций
        const states = {}
        for (const item of (found.items || [])) {
          states[item.id] = {
            quantity: item.quantity,
            exchange_qty: item.exchange_qty || 0,
            sell_with_qty: item.sell_with_qty || 0,
            defective_qty: item.defective_qty || 0,
          }
        }
        setItemStates(states)
      } else {
        setError('Заказ не найден в текущем рейсе')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const updateItem = (itemId, field, value) => {
    setItemStates(prev => ({
      ...prev,
      [itemId]: { ...prev[itemId], [field]: value }
    }))
  }

  // Специальные хэндлеры для контейнерных степперов с валидацией
  const incContainer = (itemId, field) => {
    setItemStates(prev => {
      const current = prev[itemId] || {}
      const val = current[field] || 0
      const updated = { ...current, [field]: val + 1 }

      // sell_with_qty не может превышать exchange_qty
      if (field === 'sell_with_qty' && updated.sell_with_qty > (updated.exchange_qty || 0)) {
        updated.sell_with_qty = updated.exchange_qty || 0
      }

      return { ...prev, [itemId]: updated }
    })
  }

  const decContainer = (itemId, field) => {
    setItemStates(prev => {
      const current = prev[itemId] || {}
      const val = current[field] || 0
      if (val <= 0) return prev

      const updated = { ...current, [field]: val - 1 }
      return { ...prev, [itemId]: updated }
    })
  }

  const isBottle20L = (item) => {
    const type = item.product_type || ''
    return type === '19W' || type === 'B19W'
  }

  // ── Хэндлеры для добавленных продуктов ────────────────────────────────────────

  const handleAddProduct = () => {
    if (!selectedProductId) return
    const product = allProducts.find(p => p.id === parseInt(selectedProductId))
    if (!product) return

    // Проверяем, не добавлен ли уже этот продукт
    const existing = extraItems.findIndex(e => e.product_id === product.id)
    if (existing >= 0) {
      // Если уже есть — увеличиваем количество
      setExtraItems(prev => prev.map((item, idx) =>
        idx === existing ? { ...item, quantity: item.quantity + newItemQty } : item
      ))
    } else {
      // Иначе добавляем новый
      setExtraItems(prev => [...prev, {
        product_id: product.id,
        product_name: product.name,
        product_type: product.type_product,
        price: product.price,
        quantity: newItemQty,
      }])
    }
    // Сбрасываем селектор
    setSelectedProductId('')
    setNewItemQty(1)
  }

  const updateExtraItem = (index, newQty) => {
    if (newQty < 1) {
      // Если количество стало 0 — удаляем позицию
      setExtraItems(prev => prev.filter((_, i) => i !== index))
    } else {
      setExtraItems(prev => prev.map((item, i) =>
        i === index ? { ...item, quantity: newQty } : item
      ))
    }
  }

  const removeExtraItem = (index) => {
    setExtraItems(prev => prev.filter((_, i) => i !== index))
  }

  // Валидация позиций
  const validationErrors = useMemo(() => {
    const errors = {}
    const items = order?.items || []
    for (const item of items) {
      if (isBottle20L(item)) {
        const st = itemStates[item.id] || {}
        const exchange = st.exchange_qty || 0
        const sell = st.sell_with_qty || 0
        const defective = st.defective_qty || 0
        if (exchange === 0) {
          errors[item.id] = 'Обмен тары не может быть нулевым'
        }
        if (sell > exchange) {
          errors[item.id] = 'Продажа с тарой не может превышать обмен'
        }
        if (defective < 0) {
          errors[item.id] = 'Брак не может быть отрицательным'
        }
      }
    }
    return errors
  }, [order, itemStates])

  const hasErrors = Object.keys(validationErrors).length > 0

  // Есть ли уже отдельная позиция тары в заказе (её создаёт бэкенд при подтверждении,
  // Product id=9, type=BT). Если да — цена тары уже учтена в itemTotal этой позиции,
  // и добавлять bottleTotal для воды НЕЛЬЗЯ (иначе двойной счёт).
  const taraItemExists = useMemo(
    () => (order?.items || []).some(i => i.product_type === 'BT'),
    [order]
  )

  // Динамический расчёт общей стоимости на основе itemStates + extraItems
  const totalPrice = useMemo(() => {
    const items = order?.items || []
    const orderTotal = items.reduce((sum, item) => {
      const st = itemStates[item.id] || {}
      const isWater = isBottle20L(item)
      
      // unit_price = исходная цена позиции / исходное количество
      const unitPrice = (item.quantity && item.price) ? (item.price / item.quantity) : 0
      
      // Для воды фактическое количество = exchange_qty (бэкенд при подтверждении
      // ставит quantity = exchange_qty, см. bot_bridge/views.py). Для не-воды —
      // текущее quantity из state.
      const effectiveQty = isWater ? (st.exchange_qty || 0) : (st.quantity || item.quantity)
      
      let itemTotal = Math.round(unitPrice * effectiveQty)
      
      // Добавляем цену тары для визуального отображения ТОЛЬКО если отдельной позиции
      // тары ещё нет в заказе (иначе бэкенд уже учтёт её, и будет двойной счёт)
      let bottleTotal = 0
      if (isWater && bottlePrice > 0 && st.sell_with_qty > 0 && !taraItemExists) {
        bottleTotal = Math.round(bottlePrice * st.sell_with_qty)
      }
      
      return sum + itemTotal + bottleTotal
    }, 0)

    // Добавляем стоимость дополнительных продуктов
    const extraTotal = extraItems.reduce((sum, item) => sum + item.price * item.quantity, 0)

    return orderTotal + extraTotal
  }, [order, itemStates, bottlePrice, taraItemExists, extraItems])

  // Детализация по позициям для отображения
  const itemsWithPrices = useMemo(() => {
    const items = order?.items || []
    return items.map(item => {
      const st = itemStates[item.id] || {}
      const isWater = isBottle20L(item)
      
      const unitPrice = (item.quantity && item.price) ? (item.price / item.quantity) : 0
      const effectiveQty = isWater ? (st.exchange_qty || 0) : (st.quantity || item.quantity)
      const lineTotal = Math.round(unitPrice * effectiveQty)
      
      let bottleTotal = 0
      if (isWater && bottlePrice > 0 && st.sell_with_qty > 0 && !taraItemExists) {
        bottleTotal = Math.round(bottlePrice * st.sell_with_qty)
      }
      
      return {
        ...item,
        effectiveQty: effectiveQty,
        unitPrice: unitPrice,
        lineTotal: lineTotal,
        bottleTotal: bottleTotal,
        totalWithBottle: lineTotal + bottleTotal,
      }
    })
  }, [order, itemStates, bottlePrice, taraItemExists])

  const handleConfirm = async () => {
    if (hasErrors) {
      setError('Исправьте ошибки валидации перед подтверждением')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      // Собираем данные: для воды — container fields, для остальных — quantity
      const items = Object.entries(itemStates).map(([itemId, state]) => {
        const item = order?.items?.find(i => i.id === parseInt(itemId))
        const isWater = item ? isBottle20L(item) : false
        const payload = {
          item_id: parseInt(itemId),
          exchange_qty: state.exchange_qty || 0,
          sell_with_qty: state.sell_with_qty || 0,
          defective_qty: state.defective_qty || 0,
        }
        // Для не-воды передаём quantity (может быть изменено курьером)
        if (!isWater) {
          payload.quantity = state.quantity || 0
        }
        return payload
      })

      // Добавляем новые продукты, если есть
      const newItems = extraItems.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
      }))

      await api.confirmOrder(parseInt(id), true, items, '', newItems)
      navigate('/trip')
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async () => {
    if (!confirm('Отменить заказ?')) return
    setSubmitting(true)
    try {
      await api.confirmOrder(parseInt(id), false, [], '')
      navigate('/trip')
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="spinner">Загрузка заказа...</div>

  if (!order) {
    return (
      <div style={{ padding: '16px' }}>
        <div className="error-box">{error || 'Заказ не найден'}</div>
        <button className="btn outline" style={{ marginTop: '12px' }} onClick={() => navigate('/trip')}>
          ← Назад
        </button>
      </div>
    )
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  // Фильтр: продукты, которые уже есть в заказе или добавлены, не показываем в селекторе
  const productsInOrder = new Set([
    ...(order?.items || []).map(i => i.product_id || i.product),
    ...extraItems.map(i => i.product_id),
  ])

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      {/* Примечание — только если есть */}
      {order.note && (
        <div style={{
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: '10px',
          padding: '10px 12px',
          marginBottom: '12px',
          fontSize: '13px',
          color: 'var(--ink1)',
          lineHeight: '1.4'
        }}>
          <span style={{ fontWeight: '600', color: 'var(--blue)' }}>Примечание:</span>{' '}
          {order.note}
        </div>
      )}

      <div className="sec-lbl">Состав заказа</div>

      {itemsWithPrices.map(item => {
        const st = itemStates[item.id] || {}
        const isWater = isBottle20L(item)
        const error = validationErrors[item.id]

        return (
          <div className="prod-block" key={item.id}>
            <div className="prod-header">
              <span style={{ fontSize: '14px' }}>{productIcon(item.product_name)}</span>
              <span className="ph-name">
                {item.product_name}
                {!isWater && ` × ${item.effectiveQty}`}
              </span>
              <span className="ph-total">{fmt(item.totalWithBottle)} сум</span>
            </div>
            {item.bottleTotal > 0 && (
              <div className="prod-subheader">
                <span className="ph-subtext">включая стоимость тары: {fmt(item.bottleTotal)} сум</span>
              </div>
            )}
            {error && (
              <div className="prod-subheader error">
                <span className="ph-subtext" style={{ color: 'var(--red)' }}>{error}</span>
              </div>
            )}
            <div className="prod-body">
              {isWater ? (
                <>
                  {/* Для воды: только контейнерные поля */}
                  {/* Обмен тары */}
                  <div className="op-row">
                    <span className="op-lbl">Обмен</span>
                    <span className="op-tag exch">тара ←→</span>
                    <Stepper
                      value={st.exchange_qty || 0}
                      onIncrement={() => incContainer(item.id, 'exchange_qty')}
                      onDecrement={() => decContainer(item.id, 'exchange_qty')}
                      color="var(--blue)"
                    />
                  </div>
                  <hr className="div" />
                  {/* Продажа с тарой */}
                  <div className="op-row">
                    <span className="op-lbl">С тарой</span>
                    <span className="op-tag sell">продажа</span>
                    <Stepper
                      value={st.sell_with_qty || 0}
                      onIncrement={() => incContainer(item.id, 'sell_with_qty')}
                      onDecrement={() => decContainer(item.id, 'sell_with_qty')}
                      color="var(--green)"
                    />
                  </div>
                  <hr className="div" />
                  {/* Брак */}
                  <div className="op-row">
                    <span className="op-lbl">Брак</span>
                    <span className="op-tag defect">брак</span>
                    <Stepper
                      value={st.defective_qty || 0}
                      onIncrement={() => incContainer(item.id, 'defective_qty')}
                      onDecrement={() => decContainer(item.id, 'defective_qty')}
                      color="var(--ink3)"
                    />
                  </div>
                </>
              ) : (
                /* Обычный продукт — количество редактируется */
                <div className="op-row">
                  <span className="op-lbl">Количество</span>
                  <span className="op-tag">шт.</span>
                  <Stepper
                    value={st.quantity || 0}
                    onChange={(val) => updateItem(item.id, 'quantity', val)}
                    color="var(--ink2)"
                  />
                </div>
              )}
            </div>
          </div>
        )
      })}

      {/* ── Секция: Добавить новый товар ─────────────────────────────────────── */}
      <div className="sec-lbl">➕ Добавить товар</div>
      <div className="add-product-block">
        <div className="add-product-row">
          <select
            className="add-product-select"
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
          >
            <option value="">— Выберите товар —</option>
            {allProducts
              .filter(p => !productsInOrder.has(p.id))
              .map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} — {fmt(p.price)} сум
                </option>
              ))}
          </select>
          <div className="add-product-stepper">
            <Stepper
              value={newItemQty}
              onChange={(val) => setNewItemQty(Math.max(1, val))}
              color="var(--blue)"
            />
          </div>
          <button
            className="add-product-btn"
            onClick={handleAddProduct}
            disabled={!selectedProductId}
          >
            ➜ Добавить
          </button>
        </div>
      </div>

      {/* ── Список добавленных товаров ────────────────────────────────────────── */}
      {extraItems.length > 0 && (
        <>
          <div className="sec-lbl">🆕 Добавленные товары</div>
          {extraItems.map((item, idx) => (
            <div className="prod-block" key={`extra-${idx}`}>
              <div className="prod-header">
                <span style={{ fontSize: '14px' }}>{productIcon(item.product_type)}</span>
                <span className="ph-name">{item.product_name}</span>
                <span className="ph-total">{fmt(item.price * item.quantity)} сум</span>
              </div>
              <div className="prod-body">
                <div className="op-row">
                  <span className="op-lbl">Количество</span>
                  <span className="op-tag">шт.</span>
                  <Stepper
                    value={item.quantity}
                    onChange={(val) => updateExtraItem(idx, val)}
                    color="var(--blue)"
                  />
                  <button
                    className="remove-item-btn"
                    onClick={() => removeExtraItem(idx)}
                    title="Удалить"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </>
      )}

      {/* Оплата */}
      <div className="sec-lbl">Оплата</div>
      <div className="pay-grid">
        {[
          { code: 'CH', label: 'Наличные', icon: '💵' },
          { code: 'CD', label: 'Карта',    icon: '💳' },
          { code: 'BS', label: 'Бонус',    icon: '🎁' },
        ].map(p => (
          <div
            key={p.code}
            className={`pay-btn${paymentType === p.code ? ' active' : ''}`}
            onClick={() => setPaymentType(p.code)}
          >
            <span className="pb-icon">{p.icon}</span>
            <span className="pb-lbl">{p.label}</span>
          </div>
        ))}
      </div>

      {/* Итого — динамический */}
      <div className="summary-row">
        <span className="sr-lbl">Итого</span>
        <span className="sr-val">{fmt(totalPrice)} сум</span>
      </div>

      {/* Кнопки */}
      <button
        className="confirm-btn"
        onClick={handleConfirm}
        disabled={submitting || hasErrors}
        title={hasErrors ? 'Исправьте ошибки валидации' : ''}
      >
        {submitting ? 'Сохраняем...' : '✓ Подтвердить доставку'}
      </button>
      {hasErrors && (
        <div className="error-box" style={{ marginTop: '8px', fontSize: '14px' }}>
          Нельзя подтвердить заказ: есть ошибки валидации (обмен тары не может быть нулевым и т.д.)
        </div>
      )}

      <button
        className="btn outline"
        onClick={handleCancel}
        disabled={submitting}
        style={{ marginTop: '6px' }}
      >
        Отменить заказ
      </button>
    </div>
  )
}
