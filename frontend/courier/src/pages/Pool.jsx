import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'
import CreateOrderModal from './CreateOrder.jsx'
import OrderCard from '../components/OrderCard/OrderCard.jsx'

export default function Pool() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [assigning, setAssigning] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await api.getPool()
      setOrders(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAssign = async (orderId) => {
    setAssigning(orderId)
    try {
      await api.assignOrder(orderId)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setAssigning(null)
    }
  }

  // Преобразуем данные заказа в формат, ожидаемый OrderCard
  const transformOrder = (order) => ({
    id: order.id,
    created_at: order.created_at,
    address: order.client_address || 'Адрес не указан',
    latitude: order.latitude || null,
    longitude: order.longitude || null,
    payment_type: order.payment_type,
    payment_type_label: order.payment_type === 'CD' ? 'Карта' : order.payment_type === 'BS' ? 'Бонус' : 'Наличные',
    items: order.items || [],
    client: {
      name: order.client_name || 'Клиент не указан',
      phone: order.client_phone || null,
    },
    created_by: order.created_by || null,
  })

  if (loading) return <div className="spinner">Загрузка пула...</div>

  return (
    <>
      <div className="page-body">
        {error && <div className="error-box">{error}</div>}

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
              isPoolOrder={true}
              onAccept={() => handleAssign(order.id)}
            />
          ))
        )}

        <hr className="div" />
        <div className="sec-lbl">Новый заказ от клиента</div>
        <div className="ocard">
          <div style={{ fontSize: '12px', color: 'var(--ink2)', marginBottom: '8px' }}>
            Клиент рядом и хочет заказать — оформите заказ сами
          </div>
          <div className="tags" style={{ marginBottom: '8px' }}>
            <span className="tag water">Вода 20л</span>
            <span className="tag cooler">Кулер</span>
            <span className="tag acc">Аксессуар</span>
          </div>
          <button className="create-btn" onClick={() => setShowCreate(true)}>
            + Оформить заказ
          </button>
        </div>
      </div>

      {showCreate && (
        <CreateOrderModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); load() }}
        />
      )}
    </>
  )
}
