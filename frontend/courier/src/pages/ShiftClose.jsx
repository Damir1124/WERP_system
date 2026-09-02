import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function ShiftClose() {
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Получаем данные из state
  const { shiftStats = {}, shift = {}, shiftId } = location.state || {}

  // Если данных нет, редирект на Shift
  if (!shiftId) {
    navigate('/shift', { replace: true })
    return null
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  const handleCloseShift = async () => {
    setLoading(true)
    setError(null)
    try {
      await api.closeShift(shiftId)
      // Успешно закрыли смену — переходим на страницу смены
      navigate('/shift', { replace: true })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    navigate('/shift')
  }

  // Вычисляем итоговую сумму
  const cashTotal = shift.cash_total || 0
  const cardTotal = shift.card_total || 0
  const totalAmount = cashTotal + cardTotal

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
        📋 Итоги смены #{shiftId}
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '20px', flex: 1, overflowY: 'auto' }}>
        {/* Ошибка */}
        {error && <div className="error-box">{error}</div>}

        {/* Секция: Статистика доставки */}
        <div className="section">
          <div className="sec-lbl">📦 Статистика доставки</div>
          <div className="mrow" style={{ marginBottom: '8px' }}>
            <span className="mr-lbl">Воды доставлено</span>
            <span className="mr-val" style={{ color: '#1450A3', fontWeight: 600 }}>{shiftStats.water_delivered || 0} бак</span>
          </div>
          <div className="mrow">
            <span className="mr-lbl">Заказов выполнено</span>
            <span className="mr-val green">{shiftStats.orders_count || 0} шт</span>
          </div>
        </div>

        {/* Секция: Финансы */}
        <div className="section">
          <div className="sec-lbl">💰 Финансы</div>
          <div className="mrow" style={{ marginBottom: '8px' }}>
            <span className="mr-lbl">💵 Наличные</span>
            <span className="mr-val green">{fmt(cashTotal)} сум</span>
          </div>
          {cardTotal > 0 && (
            <div className="mrow" style={{ marginBottom: '8px' }}>
              <span className="mr-lbl">💳 Карта</span>
              <span className="mr-val blue">{fmt(cardTotal)} сум</span>
            </div>
          )}
          <hr className="div" style={{ margin: '12px 0' }} />
          <div className="mrow">
            <span className="mr-lbl" style={{ fontWeight: 600 }}>Итого</span>
            <span className="mr-val" style={{ fontWeight: 600, fontSize: '20px' }}>
              {fmt(totalAmount)} сум
            </span>
          </div>
        </div>

        {/* Блок напоминания о сдаче денег */}
        {cashTotal > 0 && (
          <div
            style={{
              background: 'rgba(34, 197, 94, 0.1)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              borderRadius: '10px',
              color: '#22c55e',
              padding: '12px',
              fontSize: '14px',
              lineHeight: '1.4',
            }}
          >
            💵 Не забудьте сдать {fmt(cashTotal)} сум наличными в кассу
          </div>
        )}

        {/* Информация о дате смены */}
        {shift.date && (
          <div className="section">
            <div className="sec-lbl">📅 Информация о смене</div>
            <div className="mrow">
              <span className="mr-lbl">Дата смены</span>
              <span className="mr-val">{shift.date}</span>
            </div>
          </div>
        )}

        {/* Кнопки */}
        <button
          className="btn primary"
          onClick={handleCloseShift}
          disabled={loading}
          style={{ marginTop: '8px' }}
        >
          {loading ? 'Закрываем...' : '✅ Закрыть смену'}
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
