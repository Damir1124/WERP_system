import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'
import OrderCard from '../components/OrderCard/OrderCard.jsx'
import { useRefresh } from '../refreshContext.js'

/**
 * Пул заказов для оператора — только просмотр, без кнопки «Взять заказ».
 */
export default function Pool() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getPool()
      setOrders(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error('[Pool] Ошибка загрузки:', e)
      setError(e.message)
      setOrders([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Регистрируем load() в контексте, чтобы refresh-FAB мог обновить пул
  const { registerRefresh } = useRefresh()
  useEffect(() => {
    registerRefresh(load)
  }, [registerRefresh, load])

  // Преобразуем данные заказа в формат OrderCard
  const transformOrder = (order) => ({
    id: order.id,
    display_number: order.display_number ?? null,
    created_at: order.created_at,
    note: order.note || null,
    delivery_address_text: order.delivery_address_text || 'Адрес не указан',
    delivery_address_display: order.delivery_address_display || order.delivery_address_text || 'Адрес не указан',
    delivery_latitude: order.delivery_latitude || null,
    delivery_longitude: order.delivery_longitude || null,
    payment_type: order.payment_type,
    payment_type_label: order.payment_type === 'CD' ? 'Карта' : order.payment_type === 'BS' ? 'Бонус' : 'Наличные',
    items: order.items || [],
    client: {
      name: order.client_name || 'Клиент не указан',
      phone: order.client_phone || null,
    },
    created_by: order.created_by || null,
  })

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '200px',
        padding: '20px'
      }}>
        <div className="spinner">Загрузка пула...</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header-fixed">
        {error && <div className="error-box">{error}</div>}
        <div className="sec-lbl">Пул заказов</div>

        {/* Счётчики: всего заказов и воды в пуле */}
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '12px'
        }}>
          <div style={{
            flex: 1,
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '10px 12px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--ink1)' }}>{orders.length}</div>
            <div style={{ fontSize: '11px', color: 'var(--ink3)' }}>Заказов в пуле</div>
          </div>
          <div style={{
            flex: 1,
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '10px 12px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--blue)' }}>
              {orders.reduce((sum, o) => sum + (o.items || []).reduce((s, it) => s + (it.product_type === '19W' ? (it.quantity || 0) : 0), 0), 0)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--ink3)' }}>Воды в пуле (шт)</div>
          </div>
        </div>
      </div>

      <div className="page-content-scroll">
        {orders.length === 0 ? (
          <div className="empty-state">
            <div className="es-icon">📭</div>
            <p>Свободных заказов нет</p>
            <p style={{ fontSize: '12px', marginTop: '4px' }}>Все заказы разобраны</p>
          </div>
        ) : (
          orders.map(order => (
            <OrderCard
              key={order.id}
              order={transformOrder(order)}
              isPoolOrder={false}
              isOperatorView={false}
            />
          ))
        )}
      </div>
    </div>
  )
}