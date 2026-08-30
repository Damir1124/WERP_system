import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'
import { useRefresh } from '../refreshContext.js'

export default function Colleagues() {
  const [colleagues, setColleagues] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getColleagues()
      setColleagues(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error('[Colleagues] Ошибка загрузки:', e)
      setError(e.message)
      setColleagues([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Регистрируем load() в контексте, чтобы refresh-FAB мог обновить данные
  const { registerRefresh } = useRefresh()
  useEffect(() => {
    registerRefresh(load)
  }, [registerRefresh, load])

  if (loading) return <div className="spinner">Загрузка...</div>

  return (
    <div className="page-body" style={{ paddingBottom: '80px' }}>
      {error && <div className="error-box">{error}</div>}

      {colleagues.length === 0 ? (
        <div className="empty-state">
          <div className="es-icon">👥</div>
          <p>Нет зарегистрированных курьеров</p>
        </div>
      ) : (
        <>
          <div className="sec-lbl">Курьеры — {colleagues.length} чел.</div>

          {/* Каждая карточка курьера: имя + телефон (если есть), ниже 4 столбца цифр */}
          {colleagues.map(c => (
            <div key={c.id} style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '10px 12px',
              marginBottom: '10px'
            }}>
              {/* Имя + телефон в одну строку */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px'
              }}>
                <span style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: 'var(--ink1)'
                }}>
                  {c.full_name}
                </span>
                {c.phone && (
                  <span style={{
                    fontSize: '12px',
                    color: 'var(--blue)',
                    fontWeight: '500'
                  }}>
                    {c.phone}
                  </span>
                )}
              </div>

              {/* Четыре столбца цифр без эмодзи */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '6px',
                textAlign: 'center'
              }}>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--blue)', lineHeight: '1.2' }}>{c.water_in_car || 0}</div>
                  <div style={{ fontSize: '10px', color: 'var(--ink3)' }}>В машине</div>
                </div>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--ink1)', lineHeight: '1.2' }}>{c.water_needed || 0}</div>
                  <div style={{ fontSize: '10px', color: 'var(--ink3)' }}>Нужно</div>
                </div>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--green)', lineHeight: '1.2' }}>{c.orders_completed || 0}</div>
                  <div style={{ fontSize: '10px', color: 'var(--ink3)' }}>Выполнено</div>
                </div>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--ink1)', lineHeight: '1.2' }}>{c.orders_pending || 0}</div>
                  <div style={{ fontSize: '10px', color: 'var(--ink3)' }}>В работе</div>
                </div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
