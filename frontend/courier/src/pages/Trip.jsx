import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function Trip() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const res = await api.getCurrentTrip()
      setData(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleOpenShift = async () => {
    setActionLoading(true)
    try {
      await api.openShift()
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleOpenTrip = async () => {
    const loaded = prompt('Сколько баклажек загружено?', '0')
    if (loaded === null) return
    setActionLoading(true)
    try {
      await api.openTrip(parseInt(loaded) || 0)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <div className="spinner">Загрузка...</div>

  // Нет активной смены
  if (!data?.active_shift) {
    return (
      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {error && <div className="error-box">{error}</div>}
        <div className="empty-state">
          <div className="es-icon">🌅</div>
          <p>Смена не открыта</p>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>Начните рабочий день</p>
        </div>
        <button className="btn primary" onClick={handleOpenShift} disabled={actionLoading}>
          {actionLoading ? 'Открываем...' : 'Открыть смену'}
        </button>
      </div>
    )
  }

  // Смена открыта, но нет активного рейса
  if (!data?.active_trip) {
    return (
      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {error && <div className="error-box">{error}</div>}
        <div className="empty-state">
          <div className="es-icon">🚚</div>
          <p>Смена открыта</p>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>Загрузите машину и начните рейс</p>
        </div>
        <button className="btn primary" onClick={handleOpenTrip} disabled={actionLoading}>
          {actionLoading ? 'Открываем...' : 'Начать рейс'}
        </button>
      </div>
    )
  }

  const trip = data.trip
  const summary = data.summary || {}
  const orders = trip?.orders || []

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      {/* Счётчики */}
      <div className="stats-grid">
        <div className="scard blue">
          <div className="sc-lbl">Загружено</div>
          <div className="sc-val">{summary.full_loaded ?? 0} <span>бак</span></div>
        </div>
        <div className="scard green">
          <div className="sc-lbl">Доставлено</div>
          <div className="sc-val">{summary.delivered ?? 0} <span>бак</span></div>
        </div>
        <div className="scard amber">
          <div className="sc-lbl">Осталось</div>
          <div className="sc-val">{summary.full_remain ?? 0} <span>бак</span></div>
        </div>
        <div className="scard teal">
          <div className="sc-lbl">Пустых в машине</div>
          <div className="sc-val">{summary.empty_expected ?? 0} <span>шт</span></div>
        </div>
      </div>

      {/* Деньги */}
      <div className="mrow">
        <span className="mr-lbl">💵 Наличными</span>
        <span className="mr-val green">{fmt(summary.cash_expected)} сум</span>
      </div>
      <div className="mrow">
        <span className="mr-lbl">💳 Картой</span>
        <span className="mr-val blue">{fmt(summary.card_expected)} сум</span>
      </div>

      <hr className="div" />
      <div className="sec-lbl">Заказы рейса</div>

      {orders.length === 0 && (
        <div className="empty-state" style={{ padding: '20px' }}>
          <p>Заказов пока нет</p>
        </div>
      )}

      {orders.map(order => {
        const delivered = order.status === 'DL'
        const items = order.items || []
        const payLabel = order.payment_type === 'CD' ? 'Карта' : order.payment_type === 'BS' ? 'Бонус' : 'Наличные'
        const payClass = order.payment_type === 'CD' ? 'card' : 'cash'

        return (
          <div className="ocard" key={order.id}>
            <div className="oc-name">{order.client_name || 'Клиент не указан'}</div>
            <div className="oc-addr">{order.client_address || ''}</div>
            <div className="tags">
              {items.map((item, i) => (
                <span key={i} className="tag water">{item.product_name} × {item.quantity}</span>
              ))}
              <span className={`tag ${payClass}`}>{payLabel}</span>
            </div>
            {delivered ? (
              <button className="btn done" disabled>✓ Доставлено</button>
            ) : (
              <button
                className="btn primary"
                onClick={() => navigate(`/order/${order.id}/confirm`)}
              >
                Доставить
              </button>
            )}
          </div>
        )
      })}

      <hr className="div" />
      <button className="create-btn" onClick={() => navigate('/pool')}>
        + Создать заказ на месте
      </button>
    </div>
  )
}
