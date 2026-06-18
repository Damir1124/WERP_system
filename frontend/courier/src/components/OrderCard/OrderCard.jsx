import { useState } from 'react'
import FreshnessIndicator from './FreshnessIndicator.jsx'
import './OrderCard.css'

/**
 * Компонент карточки заказа с двумя состояниями: свёрнутое и развёрнутое
 * 
 * @param {Object} order - Данные заказа
 * @param {boolean} isPoolOrder - Показывать кнопку "Взять заказ"
 * @param {boolean} isTripOrder - Показывать кнопку "Подтвердить доставку"
 * @param {Function} onAccept - Callback для взятия заказа
 * @param {Function} onConfirm - Callback для подтверждения доставки
 */
export default function OrderCard({ 
  order, 
  isPoolOrder = false, 
  isTripOrder = false,
  onAccept,
  onConfirm 
}) {
  const [expanded, setExpanded] = useState(false)

  // Определяем количество товара для бейджа
  const getQuantityBadge = () => {
    // Ищем товар с type_product === 'WT'
    const wtItem = order.items?.find(item => item.product_type === 'WT')
    if (wtItem) {
      return `${wtItem.quantity} шт`
    }
    // Если WT нет, берём первый товар
    if (order.items && order.items.length > 0) {
      return `${order.items[0].quantity} шт`
    }
    return '0 шт'
  }

  // Определяем класс и текст для бейджа оплаты
  const getPaymentBadge = () => {
    const type = order.payment_type
    if (type === 'CS' || type === 'cash') {
      return { text: 'Наличные', className: 'payment-badge cash' }
    }
    if (type === 'CD' || type === 'card') {
      return { text: 'Карта', className: 'payment-badge card' }
    }
    if (type === 'TR' || type === 'transfer') {
      return { text: 'Перевод', className: 'payment-badge card' }
    }
    return { text: order.payment_type_label || 'Оплата', className: 'payment-badge' }
  }

  const paymentBadge = getPaymentBadge()

  // Форматирование даты
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
    const day = date.getDate()
    const month = months[date.getMonth()]
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    return `${day} ${month}, ${hours}:${minutes}`
  }

  // Обработка клика на карточку
  const handleToggle = () => {
    setExpanded(!expanded)
  }

  return (
    <div className={`order-card ${expanded ? 'expanded' : ''}`}>
      {/* Свёрнутое состояние - всегда видимо */}
      <div className="order-card-header" onClick={handleToggle}>
        <FreshnessIndicator createdAt={order.created_at} />
        
        <div className="order-id">#{order.id}</div>
        
        <div className="quantity-badge">{getQuantityBadge()}</div>
        
        <div className="address-truncated">{order.address}</div>
        
        <div className={paymentBadge.className}>{paymentBadge.text}</div>
        
        <div className={`chevron ${expanded ? 'rotated' : ''}`}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>

      {/* Развёрнутое состояние */}
      {expanded && (
        <div className="order-card-body">
          {/* Адрес с геолокацией */}
          <div className="detail-section">
            <div className="detail-label">Адрес</div>
            <div className="detail-value">{order.address}</div>
            {order.latitude && order.longitude && (
              <a
                href={`https://maps.google.com/?q=${order.latitude},${order.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="map-link"
              >
                Открыть на карте
              </a>
            )}
          </div>

          {/* Телефон клиента */}
          {order.client?.phone && (
            <div className="detail-section">
              <div className="detail-label">Телефон</div>
              <a href={`tel:${order.client.phone}`} className="phone-link">
                {order.client.phone}
              </a>
            </div>
          )}

          {/* Список товаров */}
          <div className="detail-section">
            <div className="detail-label">Товары</div>
            <div className="items-list">
              {order.items?.map((item, index) => (
                <div key={index} className={`item-row ${item.product_type === 'WT' ? 'highlight' : ''}`}>
                  {item.product_type === 'WT' && <span className="water-icon">💧</span>}
                  <span className="item-name">{item.product_name}</span>
                  <span className="item-quantity">× {item.quantity}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Дата создания */}
          <div className="detail-section">
            <div className="detail-label">Создан</div>
            <div className="detail-value">{formatDate(order.created_at)}</div>
          </div>

          {/* Кто создал */}
          {order.created_by && (
            <div className="detail-section">
              <div className="detail-label">Создал</div>
              <div className="detail-value">{order.created_by}</div>
            </div>
          )}

          {/* Кнопки действий */}
          <div className="order-card-actions">
            {isPoolOrder && onAccept && (
              <button className="action-btn primary" onClick={onAccept}>
                Взять заказ
              </button>
            )}
            
            {isTripOrder && onConfirm && (
              <button className="action-btn primary" onClick={onConfirm}>
                Доставить
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
