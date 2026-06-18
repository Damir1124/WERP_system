import { useState, useEffect } from 'react'
import { ORDER_FRESHNESS_CONFIG } from '../../config/orderFreshness.js'

/**
 * Индикатор свежести заказа (цветная точка)
 * Обновляется каждые 60 секунд
 */
export default function FreshnessIndicator({ createdAt }) {
  const [color, setColor] = useState('#22c55e')

  useEffect(() => {
    const updateColor = () => {
      const now = new Date()
      const created = new Date(createdAt)
      const minutesElapsed = Math.floor((now - created) / 1000 / 60)

      if (minutesElapsed >= ORDER_FRESHNESS_CONFIG.redAfterMinutes) {
        setColor('#ef4444') // красный
      } else if (minutesElapsed >= ORDER_FRESHNESS_CONFIG.yellowAfterMinutes) {
        setColor('#f59e0b') // жёлтый
      } else {
        setColor('#22c55e') // зелёный
      }
    }

    // Первоначальное обновление
    updateColor()

    // Обновление каждые 60 секунд
    const interval = setInterval(updateColor, 60000)

    return () => clearInterval(interval)
  }, [createdAt])

  const isRed = color === '#ef4444'

  return (
    <div
      className={`freshness-indicator ${isRed ? 'pulse' : ''}`}
      style={{ backgroundColor: color }}
    />
  )
}
