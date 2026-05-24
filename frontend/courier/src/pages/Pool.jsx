import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'

// Маппинг payment_type для отправки на сервер
const PAY_MAP = { 'CASH': 'CH', 'CARD': 'CD', 'BONUS': 'BS' }

// Модальное окно создания заказа курьером
function CreateOrderModal({ onClose, onCreated }) {
  const [products, setProducts] = useState([])
  const [form, setForm] = useState({ product_id: '', quantity: 1, payment_type: 'CASH' })
  const [loading, setLoading] = useState(false)
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getProducts()
      .then(data => setProducts(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoadingProducts(false))
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.product_id) { setError('Выберите продукт'); return }
    setLoading(true)
    setError(null)
    try {
      const tripData = await api.getCurrentTrip()
      if (!tripData?.active_trip) {
        setError('Нет активного рейса. Сначала откройте смену и рейс.')
        return
      }
      const tripId = tripData.trip?.id
      if (!tripId) { setError('Не удалось получить ID рейса'); return }

      await api.createOrder({
        trip: tripId,
        client: null,
        payment_type: PAY_MAP[form.payment_type] || 'CH',
        note: '',
        items: [{
          product: parseInt(form.product_id),
          quantity: parseInt(form.quantity),
          exchange_qty: 0,
          sell_with_qty: 0,
          defective_qty: 0,
        }],
      })
      onCreated()
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-sheet">
        <div className="modal-header">
          <span className="mh-title">Создать заказ</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="error-box">{error}</div>}

          <div className="form-group">
            <label className="form-label">Продукт *</label>
            {loadingProducts ? (
              <div style={{ fontSize: '13px', color: 'var(--ink3)' }}>Загрузка...</div>
            ) : (
              <select
                className="form-select"
                value={form.product_id}
                onChange={e => setForm(p => ({ ...p, product_id: e.target.value }))}
                required
              >
                <option value="">Выберите продукт</option>
                {products.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {(p.price || 0).toLocaleString('ru-RU')} сум
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Количество</label>
            <div className="qty-row">
              <div className="stepper">
                <button type="button" className="st-btn"
                  onClick={() => setForm(p => ({ ...p, quantity: Math.max(1, p.quantity - 1) }))}>−</button>
                <span className="st-val">{form.quantity}</span>
                <button type="button" className="st-btn"
                  onClick={() => setForm(p => ({ ...p, quantity: p.quantity + 1 }))}>+</button>
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Оплата</label>
            <div className="pay-grid">
              {[
                { code: 'CASH', label: 'Наличные', icon: '💵' },
                { code: 'CARD', label: 'Карта',    icon: '💳' },
              ].map(p => (
                <div
                  key={p.code}
                  className={`pay-btn${form.payment_type === p.code ? ' active' : ''}`}
                  onClick={() => setForm(prev => ({ ...prev, payment_type: p.code }))}
                >
                  <span className="pb-icon">{p.icon}</span>
                  <span className="pb-lbl">{p.label}</span>
                </div>
              ))}
            </div>
          </div>

          <button type="submit" className="btn primary" disabled={loading}>
            {loading ? 'Создаём...' : 'Создать заказ'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default function Pool() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [assigning, setAssigning] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getPool()
      setOrders(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAssign = async (orderId) => {
    setAssigning(orderId)
    try {
      await api.assignOrder(orderId)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setAssigning(null)
    }
  }

  const payLabel = (pt) => {
    if (pt === 'CD') return 'Карта'
    if (pt === 'BS') return 'Бонус'
    return 'Наличные'
  }

  if (loading) return <div className="spinner">Загрузка пула...</div>

  return (
    <>
      <div className="page-body">
        {error && <div className="error-box">{error}</div>}

        {orders.length === 0 ? (
          <div className="empty-state">
            <div className="es-icon">📭</div>
            <p>Свободных заказов нет</p>
            <p style={{ fontSize: '12px', marginTop: '4px' }}>Все заказы разобраны</p>
          </div>
        ) : (
          orders.map(order => {
            const items = order.items || []
            return (
              <div className="pool-card" key={order.id}>
                <div className="pc-name">{order.client_name || 'Клиент не указан'}</div>
                <div className="pool-meta">
                  <span className="pm-addr">{order.client_address || 'Адрес не указан'}</span>
                </div>
                <div className="tags">
                  {items.map((item, i) => (
                    <span key={i} className="tag water">
                      {item.product_name} × {item.quantity}
                    </span>
                  ))}
                  <span className="tag cash">{payLabel(order.payment_type)}</span>
                </div>
                <button
                  className="take-btn"
                  onClick={() => handleAssign(order.id)}
                  disabled={assigning === order.id}
                >
                  {assigning === order.id ? 'Берём...' : 'Взять'}
                </button>
              </div>
            )
          })
        )}

        <hr className="div" />
        <div className="sec-lbl">Новый заказ от клиента</div>
        <div className="ocard">
          <div style={{ fontSize: '12px', color: 'var(--ink2)', marginBottom: '8px' }}>
            Клиент рядом и хочет заказать — оформите заказ сами
          </div>
          <div className="tags" style={{ marginBottom: '8px' }}>
            <span className="tag water">Вода 20л</span>
            <span className="tag cooler">Кулер</span>
            <span className="tag acc">Аксессуар</span>
          </div>
          <button className="create-btn" onClick={() => setShowCreate(true)}>
            + Оформить заказ
          </button>
        </div>
      </div>

      {showCreate && (
        <CreateOrderModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); load() }}
        />
      )}
    </>
  )
}
