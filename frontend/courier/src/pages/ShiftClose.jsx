import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function ShiftClose() {
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expenses, setExpenses] = useState([{ reason: '', amount: '' }])

  // Получаем данные из state
  const { shiftStats = {}, shift = {}, shiftId } = location.state || {}

  // Если данных нет, редирект на Shift
  if (!shiftId) {
    navigate('/shift', { replace: true })
    return null
  }

  const fmt = (n) => (n || 0).toLocaleString('ru-RU')

  // ── Расходы ──────────────────────────────────────────────────────────
  const patchExpense = (idx, field, value) => {
    setExpenses(prev => prev.map((e, i) => i === idx ? { ...e, [field]: value } : e))
  }

  const addExpenseRow = () => setExpenses(prev => [...prev, { reason: '', amount: '' }])

  const removeExpenseRow = (idx) => setExpenses(prev => prev.filter((_, i) => i !== idx))

  // Эталонные расходы: непустые строки с корректной стоимостью
  const validExpenses = expenses
    .map(e => ({ reason: (e.reason || '').trim(), amount: parseInt(e.amount, 10) || 0 }))
    .filter(e => e.reason.length > 0 && e.amount > 0)

  const expensesTotal = validExpenses.reduce((s, e) => s + e.amount, 0)

  // Вычисляем итоговую сумму
  const cashTotal = shift.cash_total || 0
  const cardTotal = shift.card_total || 0
  const totalAmount = cashTotal + cardTotal
  const cashToHand = cashTotal - expensesTotal

  const handleCloseShift = async () => {
    setLoading(true)
    setError(null)
    try {
      await api.closeShift(shiftId, validExpenses)
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

  return (
    <div className="page-body" style={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100vh' }}>
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
          {expensesTotal > 0 && (
            <div className="mrow" style={{ marginTop: '8px' }}>
              <span className="mr-lbl" style={{ fontWeight: 600, color: '#e53935' }}>Расходы</span>
              <span className="mr-val" style={{ color: '#e53935', fontWeight: 600 }}>
                − {fmt(expensesTotal)} сум
              </span>
            </div>
          )}
          <div className="mrow" style={{ marginTop: '8px' }}>
            <span className="mr-lbl" style={{ fontWeight: 600, color: '#22c55e' }}>Сдать наличными</span>
            <span className="mr-val" style={{ fontWeight: 700, fontSize: '20px', color: '#22c55e' }}>
              {fmt(cashToHand)} сум
            </span>
          </div>
        </div>

        {/* Секция: Расходы смены (УПРОЩЁННАЯ) */}
        <div className="section" style={{ border: '2px solid red', padding: '16px', background: '#fff5f5' }}>
          <div style={{ fontSize: '18px', fontWeight: 700, color: 'red', marginBottom: '8px' }}>
            💸 РАСХОДЫ ТУТ. ОНИ РАБОТАЮТ!
          </div>
          <div style={{ fontSize: '12px', marginBottom: '8px' }}>
            Укажите расходы. Они вычтутся из наличных к сдаче.
          </div>
          {expenses.map((exp, i) => (
            <div key={i} style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                type="text"
                placeholder="Причина"
                value={exp.reason}
                onChange={(e) => patchExpense(i, 'reason', e.target.value)}
                style={{ flex: 1, minWidth: 0, fontSize: '14px', padding: '8px', borderRadius: '8px', border: '1px solid #d0d0d0' }}
              />
              <input
                type="number"
                inputMode="numeric"
                placeholder="Сумма"
                min="0"
                value={exp.amount}
                onChange={(e) => patchExpense(i, 'amount', e.target.value)}
                style={{ width: '110px', fontSize: '14px', padding: '8px', borderRadius: '8px', border: '1px solid #d0d0d0', textAlign: 'right' }}
              />
              {expenses.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeExpenseRow(i)}
                  style={{ background: 'transparent', border: 'none', color: '#e53935', fontSize: '20px', lineHeight: 1, cursor: 'pointer' }}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addExpenseRow}
            style={{
              width: '100%', background: '#fce4e4', border: '1px dashed #e53935',
              borderRadius: '10px', padding: '10px', color: '#e53935', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
            }}
          >
            + Добавить расход
          </button>
        </div>

        {/* Блок напоминания о сдаче денег */}
        {cashToHand > 0 && (
          <div style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            borderRadius: '10px',
            color: '#22c55e',
            padding: '12px',
            fontSize: '14px',
            lineHeight: '1.4',
          }}>
            💵 Не забудьте сдать {fmt(cashToHand)} сум наличными в кассу
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