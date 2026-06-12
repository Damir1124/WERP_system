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
  const [bottlePrice, setBottlePrice] = useState(0)

  useEffect(() => {
    loadOrder()
  }, [id])

  useEffect(() => {
    const fetchBottlePrice = async () => {
      try {
        const products = await api.getProducts()
        const bottle = products.find(p => p.type_product === 'BT')
        if (bottle) {
          setBottlePrice(bottle.price)
        }
      } catch (e) {
        console.error('Не удалось загрузить продукты', e)
      }
    }
    fetchBottlePrice()
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

  // Динамический расчёт общей стоимости на основе itemStates
  const totalPrice = useMemo(() => {
    const items = order?.items || []
    return items.reduce((sum, item) => {
      const st = itemStates[item.id] || {}
      const isWater = isBottle20L(item)
      let qty
      if (isWater) {
        // Для воды: сумма exchange_qty + sell_with_qty + defective_qty
        qty = (st.exchange_qty || 0) + (st.sell_with_qty || 0) + (st.defective_qty || 0)
      } else {
        // Для остальных продуктов: quantity (не изменяется)
        qty = item.quantity
      }
      // unit_price = исходная цена позиции / исходное количество
      // Защита от деления на ноль и NaN
      const unitPrice = (item.quantity && item.price) ? (item.price / item.quantity) : 0
      const itemTotal = Math.round(unitPrice * qty)
      
      // Добавляем стоимость тары для sell_with_qty
      let bottleTotal = 0
      if (isWater && bottlePrice > 0) {
        bottleTotal = Math.round(bottlePrice * (st.sell_with_qty || 0))
      }
      
      return sum + itemTotal + bottleTotal
    }, 0)
  }, [order, itemStates, bottlePrice])

  // Детализация по позициям для отображения
  const itemsWithPrices = useMemo(() => {
    const items = order?.items || []
    return items.map(item => {
      const st = itemStates[item.id] || {}
      const isWater = isBottle20L(item)
      let qty, lineTotal, bottleTotal = 0
      // unit_price = исходная цена позиции / исходное количество
      const unitPrice = (item.quantity && item.price) ? (item.price / item.quantity) : 0
      if (isWater) {
        qty = (st.exchange_qty || 0) + (st.sell_with_qty || 0) + (st.defective_qty || 0)
        lineTotal = Math.round(unitPrice * qty)
        // Стоимость тары для sell_with_qty
        if (bottlePrice > 0) {
          bottleTotal = Math.round(bottlePrice * (st.sell_with_qty || 0))
        }
      } else {
        qty = item.quantity
        lineTotal = Math.round(unitPrice * qty)
      }
      return {
        ...item,
        effectiveQty: qty,
        unitPrice: unitPrice,
        lineTotal: lineTotal,
        bottleTotal: bottleTotal,
        totalWithBottle: lineTotal + bottleTotal,
      }
    })
  }, [order, itemStates, bottlePrice])

  const handleConfirm = async () => {
    if (hasErrors) {
      setError('Исправьте ошибки валидации перед подтверждением')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      // Собираем данные: для воды — только container fields, для остальных — только container fields (все нули)
      const items = Object.entries(itemStates).map(([itemId, state]) => {
        const item = order?.items?.find(i => i.id === parseInt(itemId))
        const isWater = item ? isBottle20L(item) : false
        const payload = {
          item_id: parseInt(itemId),
          exchange_qty: state.exchange_qty || 0,
          sell_with_qty: state.sell_with_qty || 0,
          defective_qty: state.defective_qty || 0,
        }
        // Для не-воды quantity не передаём (сервер использует исходное количество)
        // Поля тары для не-воды игнорируются сервером (можно оставить нули)
        return payload
      })
      await api.confirmOrder(parseInt(id), true, items, '')
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

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

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
                {!isWater && ` × ${item.quantity}`}
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
                /* Обычный продукт — количество не редактируется, только информация */
                <div className="simple-row">
                  <span className="sr-lbl">Количество заказано</span>
                  <span className="sr-val">{item.quantity} шт.</span>
                </div>
              )}
            </div>
          </div>
        )
      })}

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
