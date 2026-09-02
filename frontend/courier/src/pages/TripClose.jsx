import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function TripClose() {
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Получаем данные из state
  const { summary = {}, financials = {}, tripId } = location.state || {}

  // Если данных нет, редирект на Trip
  if (!tripId) {
    navigate('/trip', { replace: true })
    return null
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  const handleCloseTrip = async () => {
    setLoading(true)
    setError(null)
    try {
      await api.closeTrip(tripId)
      // Успешно закрыли рейс — переходим на страницу смены
      navigate('/shift', { replace: true })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    navigate('/trip')
  }

  // Вычисляем итоговую сумму
  const cashExpected = financials.cash_expected || 0
  const cardExpected = financials.card_expected || 0
  const totalExpected = cashExpected + cardExpected

  return (
    <div className="page-body" style={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Заголовок с градиентом на весь экран */}
      <div style={{
        background: 'linear-gradient(135deg, #1450A3 0%, #0d3a70 100%)',
        padding: '20px 16px',
        color: 'white',
        fontSize: '20px',
        fontWeight: 600,
        textAlign: 'center',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      }}>
        📋 Итоги рейса #{tripId}
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '20px', flex: 1, overflowY: 'auto' }}>
        {/* Ошибка */}
        {error && <div className="error-box">{error}</div>}

        {/* Секция: Баклажки */}
        <div className="section">
          <div className="sec-lbl">📦 Баклажки</div>
          <div className="mrow" style={{ marginBottom: '8px' }}>
            <span className="mr-lbl">Загружено</span>
            <span className="mr-val" style={{ color: '#1450A3', fontWeight: 600 }}>{summary.full_loaded || 0} бак</span>
          </div>
          <div className="mrow" style={{ marginBottom: '8px' }}>
            <span className="mr-lbl">Доставлено</span>
            <span className="mr-val green">{summary.delivered || 0} бак</span>
          </div>
          <div className="mrow">
            <span className="mr-lbl">Осталось в машине</span>
            <span className="mr-val blue">{summary.full_remain || 0} бак</span>
          </div>
        </div>

        {/* Секция: Тара */}
        <div className="section">
          <div className="sec-lbl">📭 Тара</div>
          <div className="mrow">
            <span className="mr-lbl">Пустых собрано</span>
            <span
              className="mr-val"
              style={{
                color: '#1450a3',
                fontWeight: 600,
                animation: 'pulse 2s ease-in-out infinite',
              }}
            >
              {summary.empty_received || 0} шт
            </span>
          </div>
        </div>

        {/* CSS анимация пульсации */}
        <style>{`
          @keyframes pulse {
            0%, 100% {
              opacity: 0.7;
              text-shadow: 0 0 4px rgba(252, 211, 77, 0.4);
              transform: scale(1);
            }
            50% {
              opacity: 1;
              text-shadow: 0 0 20px rgba(252, 211, 77, 1), 0 0 30px rgba(252, 211, 77, 0.6);
              transform: scale(1.05);
            }
          }
        `}</style>

        {/* Блок напоминания о сдаче пустых баклажек */}
        {(summary.empty_received || 0) > 0 && (
          <div
            style={{
              background: 'rgba(96, 165, 250, 0.1)',
              border: '1px solid rgba(96, 165, 250, 0.3)',
              borderRadius: '10px',
              color: '#60a5fa',
              padding: '12px',
              fontSize: '14px',
              lineHeight: '1.4',
            }}
          >
            📭 При выгрузке на склад сдайте {summary.empty_received} пустых баклажек
          </div>
        )}

        {/* Секция: Финансы */}
        <div className="section">
          <div className="sec-lbl">💰 Финансы</div>
          <div className="mrow" style={{ marginBottom: '8px' }}>
            <span className="mr-lbl">💵 Наличные</span>
            <span className="mr-val green">{fmt(cashExpected)} сум</span>
          </div>
          {cardExpected > 0 && (
            <div className="mrow" style={{ marginBottom: '8px' }}>
              <span className="mr-lbl">💳 Карта</span>
              <span className="mr-val blue">{fmt(cardExpected)} сум</span>
            </div>
          )}
          <hr className="div" style={{ margin: '12px 0' }} />
          <div className="mrow">
            <span className="mr-lbl" style={{ fontWeight: 600 }}>Итого</span>
            <span className="mr-val" style={{ fontWeight: 600, fontSize: '20px' }}>
              {fmt(totalExpected)} сум
            </span>
          </div>
        </div>

        {/* Кнопки */}
        <button
          className="btn primary"
          onClick={handleCloseTrip}
          disabled={loading}
          style={{ marginTop: '8px' }}
        >
          {loading ? 'Закрываем...' : '✅ Закрыть рейс'}
        </button>

        <button
          className="btn secondary"
          onClick={handleBack}
          disabled={loading}
        >
          ← Назад
        </button>
      </div>
    </div>
  )
}
