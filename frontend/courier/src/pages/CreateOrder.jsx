import { useState, useEffect } from 'react'
import { api } from '../api.js'

// Маппинг payment_type для отправки на сервер
const PAY_MAP = { 'CASH': 'CH', 'CARD': 'CD', 'BONUS': 'BS' }

// Улучшенное модальное окно создания заказа с несколькими продуктами
export default function CreateOrderModal({ onClose, onCreated }) {
  const [products, setProducts] = useState([])
  const [clients, setClients] = useState([])
  
  // Форма клиента
  const [clientPhone, setClientPhone] = useState('')
  const [clientAddress, setClientAddress] = useState('')
  const [clientName, setClientName] = useState('')
  const [selectedClient, setSelectedClient] = useState(null)
  
  // Список продуктов в заказе
  const [orderItems, setOrderItems] = useState([
    { product_id: '', quantity: 1 }
  ])
  
  const [paymentType, setPaymentType] = useState('CASH')
  const [note, setNote] = useState('')
  
  const [loading, setLoading] = useState(false)
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [searchingClients, setSearchingClients] = useState(false)
  const [error, setError] = useState(null)

  // Загрузка продуктов при монтировании
  useEffect(() => {
    api.getProducts()
      .then(data => setProducts(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoadingProducts(false))
  }, [])

  // Поиск клиента по телефону
  const searchClient = async () => {
    if (!clientPhone || clientPhone.length < 9) return
    
    setSearchingClients(true)
    try {
      const data = await api.searchClients(clientPhone, '')
      if (Array.isArray(data) && data.length > 0) {
        setClients(data)
        // Автозаполнение первого найденного клиента
        const client = data[0]
        setSelectedClient(client)
        setClientAddress(client.address || '')
        setClientName(client.name || '')
      } else {
        setClients([])
        setSelectedClient(null)
      }
    } catch (e) {
      console.error('Ошибка поиска клиента:', e)
    } finally {
      setSearchingClients(false)
    }
  }

  // Добавить новую позицию продукта
  const addProduct = () => {
    setOrderItems([...orderItems, { product_id: '', quantity: 1 }])
  }

  // Удалить позицию продукта
  const removeProduct = (index) => {
    if (orderItems.length === 1) {
      setError('Должен быть хотя бы один продукт')
      return
    }
    setOrderItems(orderItems.filter((_, i) => i !== index))
  }

  // Обновить продукт в позиции
  const updateProduct = (index, field, value) => {
    const updated = [...orderItems]
    updated[index][field] = value
    setOrderItems(updated)
  }

  // Отправка формы
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Валидация
    if (!clientPhone) {
      setError('Введите номер телефона клиента')
      return
    }
    if (!clientAddress) {
      setError('Введите адрес доставки')
      return
    }
    
    // Проверка что все продукты выбраны
    const hasEmptyProducts = orderItems.some(item => !item.product_id)
    if (hasEmptyProducts) {
      setError('Выберите продукты для всех позиций')
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      // Получаем текущий рейс
      const tripData = await api.getCurrentTrip()
      if (!tripData?.active_trip) {
        setError('Нет активного рейса. Сначала откройте смену и рейс.')
        return
      }
      const tripId = tripData.trip?.id
      if (!tripId) {
        setError('Не удалось получить ID рейса')
        return
      }

      // Формируем данные заказа
      const orderData = {
        trip: tripId,
        client: selectedClient?.id || null,
        client_phone: clientPhone,
        client_address: clientAddress,
        client_name: clientName || `Клиент ${clientPhone}`,
        payment_type: PAY_MAP[paymentType] || 'CH',
        note: note,
        items: orderItems.map(item => ({
          product: parseInt(item.product_id),
          quantity: parseInt(item.quantity),
          exchange_qty: 0,
          sell_with_qty: 0,
          defective_qty: 0,
        })),
      }

      await api.createOrder(orderData)
      onCreated()
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-sheet" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-header">
          <span className="mh-title">Создать заказ</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        
        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="error-box">{error}</div>}

          {/* Секция клиента */}
          <div style={{ marginBottom: '20px' }}>
            <div className="sec-lbl" style={{ marginBottom: '12px' }}>📞 Информация о клиенте</div>
            
            <div className="form-group">
              <label className="form-label">Номер телефона *</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="tel"
                  className="form-input"
                  placeholder="+998901234567"
                  value={clientPhone}
                  onChange={e => setClientPhone(e.target.value)}
                  onBlur={searchClient}
                  required
                  style={{ flex: 1 }}
                />
                {searchingClients && <span style={{ fontSize: '12px', color: 'var(--ink3)' }}>🔍</span>}
              </div>
              {selectedClient && (
                <div style={{ fontSize: '11px', color: 'var(--green)', marginTop: '4px' }}>
                  ✓ Клиент найден в базе
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Адрес доставки *</label>
              <input
                type="text"
                className="form-input"
                placeholder="Улица, дом, квартира"
                value={clientAddress}
                onChange={e => setClientAddress(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">ФИО клиента (опционально)</label>
              <input
                type="text"
                className="form-input"
                placeholder="Иванов Иван Иванович"
                value={clientName}
                onChange={e => setClientName(e.target.value)}
              />
            </div>
          </div>

          {/* Секция продуктов */}
          <div style={{ marginBottom: '20px' }}>
            <div className="sec-lbl" style={{ marginBottom: '12px' }}>🛒 Продукты в заказе</div>
            
            {loadingProducts ? (
              <div style={{ fontSize: '13px', color: 'var(--ink3)', padding: '12px' }}>
                Загрузка продуктов...
              </div>
            ) : (
              <>
                {orderItems.map((item, index) => (
                  <div key={index} style={{
                    background: 'var(--bg2)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '12px',
                    marginBottom: '12px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink1)' }}>
                        Продукт #{index + 1}
                      </span>
                      {orderItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeProduct(index)}
                          style={{
                            background: 'var(--red)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            fontSize: '11px',
                            cursor: 'pointer'
                          }}
                        >
                          🗑️ Удалить
                        </button>
                      )}
                    </div>

                    <div className="form-group" style={{ marginBottom: '8px' }}>
                      <select
                        className="form-select"
                        value={item.product_id}
                        onChange={e => updateProduct(index, 'product_id', e.target.value)}
                        required
                      >
                        <option value="">Выберите продукт</option>
                        {products.map(p => (
                          <option key={p.id} value={p.id}>
                            {p.name} — {(p.price || 0).toLocaleString('ru-RU')} сум
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label" style={{ fontSize: '12px' }}>Количество</label>
                      <div className="qty-row">
                        <div className="stepper">
                          <button
                            type="button"
                            className="st-btn"
                            onClick={() => updateProduct(index, 'quantity', Math.max(1, item.quantity - 1))}
                          >
                            −
                          </button>
                          <span className="st-val">{item.quantity}</span>
                          <button
                            type="button"
                            className="st-btn"
                            onClick={() => updateProduct(index, 'quantity', item.quantity + 1)}
                          >
                            +
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                <button
                  type="button"
                  onClick={addProduct}
                  style={{
                    width: '100%',
                    background: 'var(--green)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '12px',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    marginBottom: '12px'
                  }}
                >
                  ➕ Добавить продукт
                </button>
              </>
            )}
          </div>

          {/* Секция параметров */}
          <div style={{ marginBottom: '20px' }}>
            <div className="sec-lbl" style={{ marginBottom: '12px' }}>⚙️ Параметры заказа</div>
            
            <div className="form-group">
              <label className="form-label">Способ оплаты</label>
              <div className="pay-grid">
                {[
                  { code: 'CASH', label: 'Наличные', icon: '💵' },
                  { code: 'CARD', label: 'Карта', icon: '💳' },
                ].map(p => (
                  <div
                    key={p.code}
                    className={`pay-btn${paymentType === p.code ? ' active' : ''}`}
                    onClick={() => setPaymentType(p.code)}
                  >
                    <span className="pb-icon">{p.icon}</span>
                    <span className="pb-lbl">{p.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Примечание (опционально)</label>
              <textarea
                className="form-input"
                placeholder="Дополнительная информация о заказе"
                value={note}
                onChange={e => setNote(e.target.value)}
                rows={2}
                style={{ resize: 'vertical' }}
              />
            </div>
          </div>

          <button type="submit" className="btn primary" disabled={loading || loadingProducts}>
            {loading ? 'Создаём...' : 'Создать заказ'}
          </button>
        </form>
      </div>
    </div>
  )
}
