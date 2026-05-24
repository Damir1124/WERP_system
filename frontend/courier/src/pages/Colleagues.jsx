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

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  const initials = (name = '') => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  if (loading) return <div className="spinner">Загрузка...</div>

  return (
    <div className="page-body">
      {error && <div className="error-box">{error}</div>}

      {colleagues.length === 0 ? (
        <div className="empty-state">
          <div className="es-icon">👥</div>
          <p>Нет коллег на смене</p>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>Сегодня никто больше не работает</p>
        </div>
      ) : (
        <>
          <div className="sec-lbl">На смене сегодня — {colleagues.length} чел.</div>
          {colleagues.map(c => (
            <div className="col-card" key={c.id}>
              <div className="col-avatar">{initials(c.full_name)}</div>
              <div className="col-info">
                <div className="ci-name">{c.full_name}</div>
                <div className="ci-stats">
                  Доставлено: {c.delivered_today || 0} · 
                  Нал: {fmt(c.cash_total)} · 
                  Карта: {fmt(c.card_total)}
                </div>
              </div>
              <span className="col-badge">{c.delivered_today || 0} зак.</span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
