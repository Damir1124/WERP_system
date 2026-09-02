import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import OrderCard from '../components/OrderCard/OrderCard.jsx'

const STATUS_OPTIONS = [
  { value: '', label: 'Все' },
  { value: 'PD', label: 'Ожидают' },
  { value: 'DL', label: 'Доставлены' },
  { value: 'CN', label: 'Отменены' },
]

const STATUS_MAP = {
  'PD': { label: 'Ожидает', className: 'tag water' },
  'DL': { label: 'Доставлен', className: 'tag cash' },
  'CN': { label: 'Отменён', className: 'tag' },
}

export default function AllOrders() {
  const navigate = useNavigate()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [actionLoading, setActionLoading] = useState(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const params = statusFilter ? [statusFilter] : []
      const data = await api.getOperatorOrders(params)
      setOrders(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error('[AllOrders] Ошибка загрузки:', e)
      setError(e.message)
      setOrders([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const handleEdit = (order) => {
    if (!order || !order.id) {
      console.error('[AllOrders] Ошибка: order.id не найден', order)
      setError('Ошибка загрузки данных заказа для редактирования')
      return
    }
    navigate(`/orders/${order.id}/edit`)
  }

  const handleDelete = async (order) => {
    if (!window.confirm(`Удалить заказ #${order.display_number || order.id}? Это действие необратимо.`)) return

    setActionLoading(order.id)
    try {
      await api.deleteOperatorOrder(order.id)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setActionLoading(null)
    }
  }

  // Преобразуем данные заказа в формат OrderCard
  const transformOrder = (order) => ({
    id: order.id,
    display_number: order.display_number ?? null,
    created_at: order.created_at,
    delivered_at: order.delivered_at || null,
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
    assigned_courier_name: order.assigned_courier_name || null,
    status: order.status,
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
        <div className="spinner">Загрузка заказов...</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Фиксированная шапка */}
      <div className="page-header-fixed">
        {error && <div className="error-box">{error}</div>}

        {/* Фильтр по статусу */}
        <div style={{
          display: 'flex',
          gap: '6px',
          overflowX: 'auto',
          paddingBottom: '4px',
        }}>
          {STATUS_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              style={{
                padding: '6px 12px',
                borderRadius: '20px',
                border: `1px solid ${statusFilter === opt.value ? 'var(--blue)' : 'var(--border)'}`,
                background: statusFilter === opt.value ? 'var(--blue)' : 'var(--bg)',
                color: statusFilter === opt.value ? '#fff' : 'var(--ink)',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="sec-lbl">
          Всего заказов: {orders.length}
        </div>
      </div>

      {/* Скроллящийся контент */}
      <div className="page-content-scroll">
        {orders.length === 0 ? (
          <div className="empty-state">
            <div className="es-icon">📋</div>
            <p>Заказов не найдено</p>
            <p style={{ fontSize: '12px', marginTop: '4px' }}>
              {statusFilter ? 'Нет заказов с выбранным статусом' : 'В системе пока нет заказов'}
            </p>
          </div>
        ) : (
          orders.map(order => {
            const isPending = order.status === 'PD'
            const isDelivered = order.status === 'DL'

            return (
              <OrderCard
                key={order.id}
                order={transformOrder(order)}
                isDelivered={isDelivered}
                isOperatorView={true}
                onEdit={isPending && order.id ? () => handleEdit(order) : undefined}
                onDelete={isPending && order.id ? () => handleDelete(order) : undefined}
              />
            )
          })
        )}
      </div>
    </div>
  )
}