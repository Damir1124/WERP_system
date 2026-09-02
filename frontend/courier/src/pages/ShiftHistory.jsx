import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function ShiftHistory() {
  const navigate = useNavigate()
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // Фильтр по датам (последние 7 дней по умолчанию)
  const today = new Date().toISOString().split('T')[0]
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  
  const [dateFrom, setDateFrom] = useState(sevenDaysAgo)
  const [dateTo, setDateTo] = useState(today)
  
  // Состояние раскрытых аккордеонов
  const [expandedShifts, setExpandedShifts] = useState(new Set())
  const [expandedTrips, setExpandedTrips] = useState(new Set())

  const loadHistory = async () => {
    setLoading(true)
    try {
      const data = await api.getShiftHistory(dateFrom, dateTo)
      setShifts(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadHistory() }, [])

  const toggleShift = (shiftId) => {
    const newExpanded = new Set(expandedShifts)
    if (newExpanded.has(shiftId)) {
      newExpanded.delete(shiftId)
    } else {
      newExpanded.add(shiftId)
    }
    setExpandedShifts(newExpanded)
  }

  const toggleTrip = (tripId) => {
    const newExpanded = new Set(expandedTrips)
    if (newExpanded.has(tripId)) {
      newExpanded.delete(tripId)
    } else {
      newExpanded.add(tripId)
    }
    setExpandedTrips(newExpanded)
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  const getStatusDot = (status) => {
    if (status === 'DL') return '🟢' // DELIVERED
    if (status === 'CN') return '🔴' // CANCELLED
    return '🟡' // PENDING
  }

  const getItemsSummary = (items) => {
    if (!items || items.length === 0) return 'Нет позиций'
    return items.map(item => `${item.product_name}×${item.quantity}`).join(', ')
  }

  if (loading) return <div className="spinner">Загрузка истории...</div>

  return (
    <div className="page-body">
      {/* Кнопка назад */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <button
          className="btn outline"
          style={{ width: 'auto', padding: '6px 12px', fontSize: '13px' }}
          onClick={() => navigate('/shift')}
        >
          ← Назад
        </button>
        <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--ink)' }}>
          📊 История смен
        </span>
      </div>

      {error && <div className="error-box">{error}</div>}

      {/* Фильтр по датам */}
      <div style={{ 
        background: 'var(--bg)', 
        border: '1px solid var(--border)', 
        borderRadius: '10px', 
        padding: '10px 12px',
        marginBottom: '12px'
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--ink3)', display: 'block', marginBottom: '4px' }}>
              С
            </label>
            <input
              type="date"
              className="form-input"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              style={{ padding: '6px 8px', fontSize: '12px' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--ink3)', display: 'block', marginBottom: '4px' }}>
              По
            </label>
            <input
              type="date"
              className="form-input"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              style={{ padding: '6px 8px', fontSize: '12px' }}
            />
          </div>
        </div>
        <button
          className="btn primary"
          onClick={loadHistory}
          style={{ padding: '6px', fontSize: '12px' }}
        >
          Применить
        </button>
      </div>

      {/* Список смен */}
      {shifts.length === 0 ? (
        <div className="empty-state">
          <div className="es-icon">📋</div>
          <p>Смен за этот период не найдено</p>
        </div>
      ) : (
        shifts.map(shift => {
          const isExpanded = expandedShifts.has(shift.id)
          const isOpen = shift.status === 'OP'
          const total = (shift.cash_total || 0) + (shift.card_total || 0)
          const stats = shift.stats || {}
          const trips = shift.trips || []

          return (
            <div key={shift.id} style={{ marginBottom: '8px' }}>
              {/* Заголовок смены */}
              <div
                className="shift-card"
                onClick={() => toggleShift(shift.id)}
                style={{ cursor: 'pointer' }}
              >
                <div className="sh-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                    <span style={{ fontSize: '16px' }}>{isExpanded ? '▼' : '▶'}</span>
                    <span className="sh-date">Смена {shift.date}</span>
                    <span className={`shift-badge ${isOpen ? 'open' : 'closed'}`}>
                      {isOpen ? 'Открыта' : 'Закрыта'}
                    </span>
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--ink)' }}>
                    {fmt(total)} сум
                  </span>
                </div>
              </div>

              {/* Раскрытое содержимое смены */}
              {isExpanded && (
                <div style={{ 
                  background: 'var(--bg2)', 
                  border: '1px solid var(--border)', 
                  borderTop: 'none',
                  borderRadius: '0 0 10px 10px',
                  padding: '10px 12px',
                  marginTop: '-8px'
                }}>
                  {/* Статистика смены */}
                  <div style={{ marginBottom: '10px' }}>
                    <div className="sh-row">
                      <span>💵 Наличные</span>
                      <span>{fmt(shift.cash_total)} сум</span>
                    </div>
                    <div className="sh-row">
                      <span>💳 Карта</span>
                      <span>{fmt(shift.card_total)} сум</span>
                    </div>
                    <div className="sh-row">
                      <span>📦 Воды</span>
                      <span>{stats.water_delivered || 0} шт</span>
                    </div>
                    <div className="sh-row">
                      <span>📋 Заказов</span>
                      <span>{stats.orders_count || 0}</span>
                    </div>
                  </div>

                  {/* Список рейсов */}
                  {trips.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {trips.map(trip => {
                        const isTripExpanded = expandedTrips.has(trip.id)
                        const isTripActive = trip.status === 'AC'
                        const summary = trip.summary || {}
                        const orders = trip.orders || []

                        return (
                          <div key={trip.id}>
                            {/* Заголовок рейса */}
                            <div
                              style={{
                                background: 'var(--bg)',
                                border: '1px solid var(--border)',
                                borderRadius: '8px',
                                padding: '8px 10px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between'
                              }}
                              onClick={() => toggleTrip(trip.id)}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '14px' }}>{isTripExpanded ? '▼' : '▶'}</span>
                                <span style={{ fontSize: '12px', fontWeight: '500' }}>Рейс #{trip.id}</span>
                                <span className={`shift-badge ${isTripActive ? 'open' : 'closed'}`}>
                                  {isTripActive ? 'ACTIVE' : 'DONE'}
                                </span>
                              </div>
                              <span style={{ fontSize: '12px', color: 'var(--ink3)' }}>
                                {summary.delivered || 0} шт
                              </span>
                            </div>

                            {/* Раскрытое содержимое рейса */}
                            {isTripExpanded && (
                              <div style={{
                                background: 'var(--bg3)',
                                border: '1px solid var(--border)',
                                borderTop: 'none',
                                borderRadius: '0 0 8px 8px',
                                padding: '8px 10px',
                                marginTop: '-6px'
                              }}>
                                {orders.length === 0 ? (
                                  <div style={{ fontSize: '11px', color: 'var(--ink3)', textAlign: 'center', padding: '4px' }}>
                                    Заказов нет
                                  </div>
                                ) : (
                                  orders.map(order => (
                                    <div
                                      key={order.id}
                                      style={{
                                        fontSize: '11px',
                                        padding: '6px 0',
                                        borderBottom: '1px solid var(--border)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px'
                                      }}
                                    >
                                      <span>{getStatusDot(order.status)}</span>
                                      <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: '500', color: 'var(--ink)' }}>
                                          {order.client_name || 'Клиент не указан'}
                                        </div>
                                        <div style={{ color: 'var(--ink3)', marginTop: '2px' }}>
                                          {getItemsSummary(order.items)}
                                        </div>
                                      </div>
                                      <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: '10px', color: 'var(--ink3)' }}>
                                          {order.payment_type === 'CD' ? '💳' : order.payment_type === 'BS' ? '🎁' : '💵'}
                                        </div>
                                        <div style={{ fontWeight: '500', color: 'var(--ink)' }}>
                                          {fmt(order.total_price)} сум
                                        </div>
                                      </div>
                                    </div>
                                  ))
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}
