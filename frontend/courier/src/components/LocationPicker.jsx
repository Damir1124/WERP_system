import { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Фикс иконок Leaflet (они не работают из коробки с Vite/Webpack)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

/**
 * Компонент для выбора координат на карте
 * 
 * @param {Object} props
 * @param {Object} props.initialPosition - Начальная позиция {lat, lon}
 * @param {Function} props.onLocationSelect - Callback при выборе координат (lat, lon)
 * @param {Function} props.onClose - Callback при закрытии карты
 */
export default function LocationPicker({ initialPosition, onLocationSelect, onClose }) {
  const [position, setPosition] = useState(
    initialPosition || { lat: 41.311151, lon: 69.279737 } // Ташкент по умолчанию
  )
  const [isLocating, setIsLocating] = useState(false)
  const [mapCenter, setMapCenter] = useState(
    initialPosition || { lat: 41.311151, lon: 69.279737 }
  )

  // Автоматически запрашиваем геолокацию при монтировании, если нет initialPosition
  useEffect(() => {
    if (!initialPosition && navigator.geolocation) {
      setIsLocating(true)
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const newPos = {
            lat: parseFloat(pos.coords.latitude.toFixed(6)),
            lon: parseFloat(pos.coords.longitude.toFixed(6))
          }
          setPosition(newPos)
          setMapCenter(newPos)
          setIsLocating(false)
        },
        (error) => {
          console.error('Geolocation error:', error)
          // Оставляем Ташкент по умолчанию
          setIsLocating(false)
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      )
    }
  }, [initialPosition])

  // Компонент для обновления центра карты
  function MapUpdater() {
    const map = useMap()
    
    useEffect(() => {
      map.setView([mapCenter.lat, mapCenter.lon], 15)
    }, [map, mapCenter])
    
    return null
  }

  // Компонент для обработки кликов по карте
  function LocationMarker() {
    useMapEvents({
      click(e) {
        const newPos = {
          lat: parseFloat(e.latlng.lat.toFixed(6)),
          lon: parseFloat(e.latlng.lng.toFixed(6))
        }
        setPosition(newPos)
      },
    })

    return position ? (
      <Marker position={[position.lat, position.lon]} />
    ) : null
  }

  // Получить текущую геолокацию
  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert('Геолокация не поддерживается вашим браузером')
      return
    }

    setIsLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const newPos = {
          lat: parseFloat(pos.coords.latitude.toFixed(6)),
          lon: parseFloat(pos.coords.longitude.toFixed(6))
        }
        setPosition(newPos)
        setMapCenter(newPos)
        setIsLocating(false)
      },
      (error) => {
        console.error('Geolocation error:', error)
        alert('Не удалось получить геолокацию')
        setIsLocating(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    )
  }

  // Подтвердить выбор
  const handleConfirm = () => {
    onLocationSelect(position.lat, position.lon)
    onClose()
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 9999,
      background: 'var(--bg1)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Заголовок */}
      <div style={{
        padding: '16px',
        background: 'var(--bg2)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '600',
          color: 'var(--ink1)',
          margin: 0
        }}>
          📍 Выберите место доставки
        </h2>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            fontSize: '24px',
            cursor: 'pointer',
            color: 'var(--ink2)',
            padding: '4px 8px'
          }}
        >
          ✕
        </button>
      </div>

      {/* Карта */}
      <div style={{ flex: 1, position: 'relative' }}>
        <MapContainer
          center={[mapCenter.lat, mapCenter.lon]}
          zoom={15}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapUpdater />
          <LocationMarker />
        </MapContainer>

        {/* Кнопка "Моя локация" */}
        <button
          onClick={handleGetCurrentLocation}
          disabled={isLocating}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            zIndex: 1000,
            padding: '12px',
            background: 'white',
            border: '2px solid var(--border)',
            borderRadius: '8px',
            fontSize: '20px',
            cursor: isLocating ? 'wait' : 'pointer',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            opacity: isLocating ? 0.6 : 1
          }}
          title="Моя локация"
        >
          {isLocating ? '⏳' : '📡'}
        </button>
      </div>

      {/* Информация и кнопки */}
      <div style={{
        padding: '16px',
        background: 'var(--bg2)',
        borderTop: '1px solid var(--border)'
      }}>
        {/* Координаты */}
        <div style={{
          fontSize: '13px',
          color: 'var(--ink2)',
          marginBottom: '12px',
          textAlign: 'center'
        }}>
          Координаты: <strong style={{ color: 'var(--ink1)' }}>
            {position.lat.toFixed(6)}, {position.lon.toFixed(6)}
          </strong>
        </div>

        {/* Подсказка */}
        <div style={{
          fontSize: '12px',
          color: 'var(--ink3)',
          marginBottom: '12px',
          textAlign: 'center'
        }}>
          Нажмите на карту, чтобы выбрать точное место
        </div>

        {/* Кнопки */}
        <div style={{
          display: 'flex',
          gap: '12px'
        }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '14px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              background: 'var(--bg1)',
              color: 'var(--ink1)',
              fontSize: '15px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Отмена
          </button>
          <button
            onClick={handleConfirm}
            style={{
              flex: 2,
              padding: '14px',
              border: 'none',
              borderRadius: '8px',
              background: 'var(--green)',
              color: 'white',
              fontSize: '15px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            ✓ Подтвердить
          </button>
        </div>
      </div>
    </div>
  )
}
