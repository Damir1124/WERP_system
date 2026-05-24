import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Shifts() {
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [closing, setClosing] = useState(null)

  useEffect(() => {
    api.getShifts()
      .then(data => setShifts(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const handleClose = async (shiftId) => {
    if (!confirm('Закрыть смену?')) return
    setClosing(shiftId)
    try {
      await api.closeShift(shiftId)
      const data = await api.getShifts()
      setShifts(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setClosing(null)
    }
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  if (loading) return <div className="spinner">Загрузка смен...</div>

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      {shifts.length === 0 ? (
        <div className="empty-state">
          <div className="es-icon">📋</div>
          <p>Смен пока нет</p>
        </div>
      ) : (
        shifts.map(shift => {
          const isOpen = shift.status === 'OP'
          const trips = shift.trips || []
          const ordersCount = trips.reduce((acc, t) => acc + (t.orders?.length || 0), 0)

          return (
            <div className="shift-card" key={shift.id}>
              <div className="sh-header">
                <span className="sh-date">
                  {shift.date} — Смена #{shift.id}
                </span>
                <span className={`shift-badge ${isOpen ? 'open' : 'closed'}`}>
                  {isOpen ? 'Открыта' : 'Закрыта'}
                </span>
              </div>

              <div className="sh-row">
                <span>Наличные</span>
                <span>{fmt(shift.cash_total)} сум</span>
              </div>
              <div className="sh-row">
                <span>Карта</span>
                <span>{fmt(shift.card_total)} сум</span>
              </div>
              <div className="sh-row">
                <span>Итого</span>
                <span>{fmt((shift.cash_total || 0) + (shift.card_total || 0))} сум</span>
              </div>
              <div className="sh-row">
                <span>Рейсов</span>
                <span>{trips.length}</span>
              </div>
              <div className="sh-row">
                <span>Заказов</span>
                <span>{ordersCount}</span>
              </div>

              {isOpen && (
                <button
                  className="btn outline"
                  style={{ marginTop: '8px' }}
                  onClick={() => handleClose(shift.id)}
                  disabled={closing === shift.id}
                >
                  {closing === shift.id ? 'Закрываем...' : 'Закрыть смену'}
                </button>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}
