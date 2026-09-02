import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function Shift() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [fullLoaded, setFullLoaded] = useState('')

  const load = async () => {
    try {
      setError(null)
      const res = await api.getCurrentShift()
      setData(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

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
    const loaded = parseInt(fullLoaded) || 0
    if (loaded <= 0) {
      alert('Укажите количество загруженных баклажек')
      return
    }
    setActionLoading(true)
    try {
      await api.openTrip(loaded, shift?.id)
      setShowModal(false)
      navigate('/trip')
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(false)
    }
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  if (loading) return <div className="spinner">Загрузка...</div>

  const shift = data?.shift
  const shiftStats = data?.shift_stats || {}
  const trips = data?.trips || []
  const activeTrip = trips.find(t => t.status === 'AC')
  const hasShift = !!shift
  const hasActiveTrip = !!activeTrip

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      {/* Кнопка "История смен" */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
        <button
          className="btn outline"
          style={{ width: 'auto', padding: '6px 12px', fontSize: '11px' }}
          onClick={() => navigate('/shifts/history')}
        >
          📊 История смен
        </button>
      </div>

      {/* БЛОК 1 — Статистика смены */}
      {hasShift && (
        <>
          <div className="sec-lbl">Статистика смены</div>
          <div className="stats-grid">
            <div className="scard blue">
              <div className="sc-lbl">Воды доставлено</div>
              <div className="sc-val">{shiftStats.water_delivered || 0} <span>бак</span></div>
            </div>
            <div className="scard green">
              <div className="sc-lbl">Заказов</div>
              <div className="sc-val">{shiftStats.orders_count || 0}</div>
            </div>
            <div className="scard green">
              <div className="sc-lbl">Наличные</div>
              <div className="sc-val">{fmt(shift.cash_total)} <span>сум</span></div>
            </div>
            <div className="scard blue">
              <div className="sc-lbl">Карта</div>
              <div className="sc-val">{fmt(shift.card_total)} <span>сум</span></div>
            </div>
          </div>
        </>
      )}

      {/* БЛОК 2 — Список рейсов */}
      {hasShift && trips.length > 0 && (
        <>
          <div className="sec-lbl" style={{ marginTop: '12px' }}>Рейсы</div>
          {trips.map(trip => {
            const isDone = trip.status === 'DN'
            const isActive = trip.status === 'AC'
            const summary = trip.summary || {}

            return (
              <div
                key={trip.id}
                className="shift-card"
                style={{
                  opacity: isDone ? 0.7 : 1,
                  borderColor: isActive ? 'var(--blue)' : 'var(--border)',
                  borderWidth: isActive ? '2px' : '1px',
                }}
              >
                <div className="sh-header">
                  <span className="sh-date">Рейс #{trip.id}</span>
                  <span className={`shift-badge ${isActive ? 'open' : 'closed'}`}>
                    {isActive ? 'ACTIVE' : 'DONE'}
                  </span>
                </div>

                <div className="sh-row">
                  <span>📦 Загружено</span>
                  <span>{summary.full_loaded || 0}</span>
                </div>
                <div className="sh-row">
                  <span>✅ Доставлено</span>
                  <span>{summary.delivered || 0}</span>
                </div>
                <div className="sh-row">
                  <span>🔵 Осталось</span>
                  <span>{summary.full_remain || 0}</span>
                </div>
                <div className="sh-row">
                  <span>📭 Пустых собрано</span>
                  <span>{summary.empty_received || 0}</span>
                </div>
              </div>
            )
          })}
        </>
      )}

      {/* БЛОК 3 — Кнопка действия */}
      <div style={{ marginTop: '16px' }}>
        {/* Случай А — нет активной смены */}
        {!hasShift && (
          <button
            className="btn primary"
            onClick={handleOpenShift}
            disabled={actionLoading}
          >
            {actionLoading ? 'Открываем...' : '🌅 Открыть смену'}
          </button>
        )}

        {/* Случай Б — есть смена, нет активного рейса */}
        {hasShift && !hasActiveTrip && (
          <>
            <button
              className="btn primary"
              onClick={() => setShowModal(true)}
              disabled={actionLoading}
              style={{ marginBottom: '8px' }}
            >
              🚚 Начать новый рейс
            </button>
            
            {/* Кнопка закрытия смены */}
            <button
              className="btn outline"
              onClick={() => {
                navigate('/shift/close', {
                  state: {
                    shiftStats: {
                      water_delivered: shiftStats.water_delivered || 0,
                      orders_count: shiftStats.orders_count || 0,
                    },
                    shift: {
                      cash_total: shift.cash_total || 0,
                      card_total: shift.card_total || 0,
                      date: shift.date,
                    },
                    shiftId: shift?.id,
                  }
                })
              }}
              disabled={actionLoading}
            >
              🏁 Закрыть смену
            </button>
          </>
        )}

        {/* Случай В — есть активный рейс */}
        {hasShift && hasActiveTrip && (
          <div style={{ textAlign: 'center', padding: '12px', background: 'var(--blue-bg)', borderRadius: '10px' }}>
            <div style={{ fontSize: '13px', color: 'var(--blue-text)', marginBottom: '8px' }}>
              Рейс #{activeTrip.id} в процессе →
            </div>
            <button
              className="btn primary"
              onClick={() => navigate('/trip')}
            >
              Перейти к рейсу
            </button>
          </div>
        )}
      </div>

      {/* Модальное окно "Начать рейс" */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="mh-title">Начать рейс</span>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Сколько баклажек загружено?</label>
                <input
                  type="number"
                  className="form-input"
                  min="1"
                  value={fullLoaded}
                  onChange={(e) => setFullLoaded(e.target.value)}
                  placeholder="Введите количество"
                  autoFocus
                />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn outline"
                  onClick={() => setShowModal(false)}
                  style={{ flex: 1 }}
                >
                  Отмена
                </button>
                <button
                  className="btn primary"
                  onClick={handleOpenTrip}
                  disabled={actionLoading}
                  style={{ flex: 1 }}
                >
                  {actionLoading ? 'Начинаем...' : 'Начать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
