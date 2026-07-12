import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function Colleagues() {
  const [colleagues, setColleagues] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getColleagues()
      .then(data => setColleagues(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const initials = (name = '') => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  if (loading) return <div className="spinner">Загрузка...</div>

  // Разделяем на онлайн и оффлайн
  const onlineColleagues = colleagues.filter(c => c.is_online)
  const offlineColleagues = colleagues.filter(c => !c.is_online)

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      {colleagues.length === 0 ? (
        <div className="empty-state">
          <div className="es-icon">👥</div>
          <p>Нет зарегистрированных курьеров</p>
        </div>
      ) : (
        <>
          {/* Онлайн курьеры */}
          {onlineColleagues.length > 0 && (
            <>
              <div className="sec-lbl">🟢 Онлайн — {onlineColleagues.length} чел.</div>
              {onlineColleagues.map(c => (
                <div className="col-card online" key={c.id}>
                  <div className="col-avatar online">{initials(c.full_name)}</div>
                  <div className="col-info">
                    <div className="ci-name">
                      {c.full_name}
                      <span className="online-badge">●</span>
                    </div>
                    <div className="ci-stat-row">
                      <span>🚗 В машине: <strong>{c.water_in_car || 0}</strong> бак</span>
                    </div>
                    <div className="ci-stat-row">
                      <span>📦 Надо доставить: <strong>{c.water_needed || 0}</strong> бак</span>
                    </div>
                    <div className="ci-stat-row">
                      <span>✅ Выполнено: <strong>{c.orders_completed || 0}</strong> зак</span>
                      <span style={{ marginLeft: '12px' }}>⏳ Осталось: <strong>{c.orders_pending || 0}</strong> зак</span>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Оффлайн курьеры */}
          {offlineColleagues.length > 0 && (
            <>
              <div className="sec-lbl" style={{ marginTop: onlineColleagues.length > 0 ? '16px' : '0' }}>
                ⚪ Оффлайн — {offlineColleagues.length} чел.
              </div>
              {offlineColleagues.map(c => (
                <div className="col-card offline" key={c.id}>
                  <div className="col-avatar offline">{initials(c.full_name)}</div>
                  <div className="col-info">
                    <div className="ci-name">{c.full_name}</div>
                    <div className="ci-stats" style={{ fontSize: '11px', color: '#999' }}>
                      Смена не открыта
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </>
      )}
    </div>
  )
}
