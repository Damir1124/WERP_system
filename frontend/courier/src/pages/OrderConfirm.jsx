import { useState, useEffect } from 'react'
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
function Stepper({ value, onChange, color }) {
  return (
    <div className="stepper">
      <button
        type="button"
        className="st-btn"
        onClick={() => onChange(Math.max(0, value - 1))}
      >−</button>
      <span className="st-val" style={color ? { color } : {}}>{value}</span>
      <button
        type="button"
        className="st-btn"
        onClick={() => onChange(value + 1)}
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

  // Состояние позиций: { [itemId]: { exchange_qty, sell_with_qty, defective_qty, quantity } }
  const [itemStates, setItemStates] = useState({})
  const [paymentType, setPaymentType] = useState('CH')

  useEffect(() => {
    loadOrder()
  }, [id])

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

  const isBottle20L = (item) => {
    const name = (item.product_name || '').toLowerCase()
    const type = item.product_type || ''
    // Проверяем, является ли продукт WATER (тип '19W') или содержит "вода" в названии
    return type === '19W' || name.includes('вода') || name.includes('water')
  }

  const handleConfirm = async () => {
    setSubmitting(true)
    setError(null)
    try {
      // Собираем данные о таре из itemStates
      const items = Object.entries(itemStates).map(([itemId, state]) => ({
        item_id: parseInt(itemId),
        exchange_qty: state.exchange_qty || 0,
        sell_with_qty: state.sell_with_qty || 0,
        defective_qty: state.defective_qty || 0,
      }))
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
      // При отмене отправляем пустой массив items
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

  const items = order.items || []
  const totalPrice = order.total_price || 0

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      <div className="sec-lbl">Состав заказа</div>

      {items.map(item => {
        const st = itemStates[item.id] || {}
        const isWater = isBottle20L(item)

        return (
          <div className="prod-block" key={item.id}>
            <div className="prod-header">
              <span style={{ fontSize: '14px' }}>{productIcon(item.product_name)}</span>
              <span className="ph-name">{item.product_name}</span>
              <span className="ph-total">× {item.quantity} шт</span>
            </div>
            <div className="prod-body">
              {isWater ? (
                <>
                  {/* Обмен тары */}
                  <div className="op-row">
                    <span className="op-lbl">Обмен</span>
                    <span className="op-tag exch">тара ←→</span>
                    <Stepper
                      value={st.exchange_qty || 0}
                      onChange={v => updateItem(item.id, 'exchange_qty', v)}
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
                      onChange={v => updateItem(item.id, 'sell_with_qty', v)}
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
                      onChange={v => updateItem(item.id, 'defective_qty', v)}
                      color="var(--ink3)"
                    />
                  </div>
                </>
              ) : (
                /* Обычный продукт — только количество */
                <div className="simple-row">
                  <span className="sr-lbl">Количество</span>
                  <Stepper
                    value={st.quantity || item.quantity}
                    onChange={v => updateItem(item.id, 'quantity', v)}
                  />
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

      {/* Итого */}
      <div className="summary-row">
        <span className="sr-lbl">Итого</span>
        <span className="sr-val">{(totalPrice || 0).toLocaleString('ru-RU')} сум</span>
      </div>

      {/* Кнопки */}
      <button
        className="confirm-btn"
        onClick={handleConfirm}
        disabled={submitting}
      >
        {submitting ? 'Сохраняем...' : '✓ Подтвердить доставку'}
      </button>

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
