import { useState } from 'react'
import FreshnessIndicator from './FreshnessIndicator.jsx'
import './OrderCard.css'

/**
 * Компонент карточки заказа с двумя состояниями: свёрнутое и развёрнутое
 *
 * @param {Object} order - Данные заказа
 * @param {boolean} isPoolOrder - Показывать кнопку "Взять заказ"
 * @param {boolean} isTripOrder - Показывать кнопку "Подтвердить доставку"
 * @param {boolean} isDelivered - Заказ доставлен (визуальное состояние)
 * @param {boolean} isOperatorView - Режим оператора (показывать кнопки ред./удал.)
 * @param {Function} onAccept - Callback для взятия заказа
 * @param {Function} onConfirm - Callback для подтверждения доставки
 * @param {Function} onReturnToPool - Callback для возврата заказа в пул (снять с рейса)
 * @param {Function} onEdit - Callback для редактирования заказа (оператор)
 * @param {Function} onDelete - Callback для удаления заказа (оператор)
 */
export default function OrderCard({
  order,
  isPoolOrder = false,
  isTripOrder = false,
  isDelivered = false,
  isOperatorView = false,
  onAccept,
  onConfirm,
  onReturnToPool,
  onEdit,
  onDelete
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

  // Форматирование телефона с +
  const formatPhone = (phone) => {
    if (!phone) return null
    return phone.startsWith('+') ? phone : `+${phone}`
  }

  // Обработка клика на карточку
  const handleToggle = () => {
    setExpanded(!expanded)
  }

  return (
    <div className={`order-card ${expanded ? 'expanded' : ''} ${isDelivered ? 'order-card--delivered' : ''}`}>
      {/* Свёрнутое состояние - всегда видимо */}
      <div className="order-card-header" onClick={handleToggle}>
        {isDelivered ? (
          <div className="delivered-checkmark">✅</div>
        ) : (
          <FreshnessIndicator createdAt={order.created_at} />
        )}

        <div className="order-id">{order.display_number != null ? String(order.display_number).padStart(3, '0') : String(order.id)}</div>

        <div className="quantity-badge">{getQuantityBadge()}</div>

        <div className="address-truncated">
          {order.delivery_address_display || order.delivery_address_text || '📍 Локация'}
        </div>

        <div className={paymentBadge.className}>{paymentBadge.text}</div>

        <div className={`chevron ${expanded ? 'rotated' : ''}`}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>

      {/* Развёрнутое состояние */}
      <div className={`order-card-body ${expanded ? 'expanded' : 'collapsed'}`}>
        <div className="order-card-body-content">
          {/* Адрес с кнопкой локации */}
          <div className="detail-section detail-row">
            <div className="detail-col">
              <div className="detail-label">Адрес</div>
              <div className="detail-value">
                {order.delivery_address_display || order.delivery_address_text || 'Адрес не указан'}
              </div>
            </div>
            {order.delivery_latitude && order.delivery_longitude && (
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${order.delivery_latitude},${order.delivery_longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="call-button"
                style={{ background: 'var(--blue)' }}
              >
                📍 Локация
              </a>
            )}
          </div>

          {/* Телефон клиента с кнопкой звонка */}
          {order.client?.phone && (
            <div className="detail-section detail-row">
              <div className="detail-col">
                <div className="detail-label">Телефон</div>
                <div className="detail-value">{formatPhone(order.client.phone)}</div>
              </div>
              <a href={`tel:${formatPhone(order.client.phone)}`} className="call-button">
                📞 Позвонить
              </a>
            </div>
          )}

          {/* Список товаров в одну строку */}
          <div className="detail-section">
            <div className="detail-label">Товары</div>
            <div className="detail-value items-inline">
              {order.items?.map((item, index) => (
                <span key={index}>
                  {item.product_name} × {item.quantity}
                  {index < order.items.length - 1 && ' | '}
                </span>
              ))}
            </div>
          </div>

          {/* Примечание (в развёрнутом состоянии) */}
          {order.note && (
            <div className="detail-section">
              <div className="detail-label">Примечание</div>
              <div className="detail-value">{order.note}</div>
            </div>
          )}

          {/* Дата создания и кто создал в одну строку */}
          <div className="detail-section detail-row">
            <div className="detail-col">
              <div className="detail-label">Создан</div>
              <div className="detail-value">{formatDate(order.created_at)}</div>
            </div>
            {order.created_by && (
              <div className="detail-col">
                <div className="detail-label">Создал</div>
                <div className="detail-value">{order.created_by}</div>
              </div>
            )}
          </div>

          {/* Курьер (только для оператора) */}
          {isOperatorView && order.assigned_courier_name && (
            <div className="detail-section detail-row">
              <div className="detail-col">
                <div className="detail-label">Курьер</div>
                <div className="detail-value">{order.assigned_courier_name}</div>
              </div>
            </div>
          )}

          {/* Статус доставки или кнопки действий */}
          {isDelivered ? (
            <div className="delivered-status">
              <div className="delivered-icon">✅</div>
              <div className="delivered-text">
                Доставлен — {order.delivered_at ? formatDate(order.delivered_at) : 'дата неизвестна'}
              </div>
            </div>
          ) : (
            <div className={`order-card-actions ${isTripOrder ? 'trip-actions' : ''}`}>
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

              {isTripOrder && onReturnToPool && (
                <button
                  type="button"
                  className="action-btn square return-btn"
                  onClick={onReturnToPool}
                  title="Вернуть заказ в пул"
                  aria-label="Вернуть заказ в пул"
                >
                  ↩
                </button>
              )}

              {/* Кнопки оператора — только для PENDING заказов */}
              {isOperatorView && (
                <div className="operator-actions">
                  {onEdit && (
                    <button className="action-btn edit-btn" onClick={onEdit}>
                      ✏️ Ред.
                    </button>
                  )}
                  {onDelete && (
                    <button className="action-btn delete-btn" onClick={onDelete}>
                      🗑️ Уд.
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
