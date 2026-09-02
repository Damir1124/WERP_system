import React, { useState, useEffect, useCallback } from 'react'
import { fetchOwnerStats } from './api'
import { ready, expand } from './tg'

function formatSum(amount) {
  if (amount == null) return '—'
  return amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' сум'
}

function formatNum(n) {
  if (n == null) return '—'
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function Card({ label, value, small }) {
  return (
    <div className="card">
      <div className="card-title">{label}</div>
      <div className={`card-value ${small ? 'small' : ''}`}>{value}</div>
    </div>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchOwnerStats()
      setData(result)
    } catch (e) {
      setError(e.message || 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    ready()
    expand()
    load()
  }, [load])

  if (loading && !data) {
    return (
      <div className="loading">
        <div>
          <div className="spinner" />
          <div>Загрузка…</div>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div style={{ padding: 16 }}>
        <div className="error-banner">{error}</div>
        <button className="refresh-btn" onClick={load}>
          🔄 Повторить
        </button>
      </div>
    )
  }

  const { today, all_time } = data || {}
  const t = today || {}
  const a = all_time || {}

  return (
    <div style={{ padding: '12px 12px 24px' }}>
      {/* Кнопка обновления */}
      <button className="refresh-btn" onClick={load} disabled={loading}>
        {loading ? '⏳ Обновление…' : '🔄 Обновить'}
      </button>

      {/* Ошибка (если данные уже были загружены) */}
      {error && <div className="error-banner">{error}</div>}

      {/* Блок «Сегодня» */}
      <div className="section-title">📊 Сегодня</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 4 }}>
        <Card label="Доход" value={formatSum(t.income)} />
        <Card label="Доставлено заказов" value={formatNum(t.delivered_orders)} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 4 }}>
        <Card label="Воды доставлено" value={formatNum(t.water_delivered) + ' шт'} small />
        <Card label="Заказов в ожидании" value={formatNum(t.pending_orders)} small />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 4 }}>
        <Card label="Воды в ожидании" value={formatNum(t.pending_water) + ' шт'} small />
        <Card label="Активных рейсов" value={formatNum(t.active_trips)} small />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 4 }}>
        <Card label="В развозе (вода)" value={formatNum(t.in_transit_water) + ' шт'} small />
        <Card label="Наличные" value={formatSum(t.cash)} small />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Card label="Карта" value={formatSum(t.card)} small />
        <div />
      </div>

      {/* Блок «За всё время» */}
      <div className="section-title">📈 За всё время</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Card label="Всего создано заказов" value={formatNum(a.total_orders)} />
        <Card label="Всего продано воды" value={formatNum(a.total_water_sold) + ' шт'} />
      </div>

      {a.historical_included && (
        <div className="historical-note">
          Включая данные до запуска WERP
        </div>
      )}

      {/* Кнопка на полный Dashboard */}
      <a
        href="/dashboard/"
        className="dashboard-btn"
        target="_blank"
        rel="noopener noreferrer"
      >
        📋 Открыть полный Dashboard
      </a>
    </div>
  )
}