import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { t } from '../i18n.js'
import { ICONS, STATUS_ICONS } from '../icons/water-icons.jsx'

// Фикс иконок Leaflet (они не работают из коробки с Vite/Webpack)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

/**
 * Выбор геолокации на карте (как в courier OrderCreate).
 * Без ручного ввода координат — только карта + кнопка «Моя локация».
 *
 * @param {Object} props
 * @param {Object} props.initialPosition - Начальная позиция {lat, lon}
 * @param {Function} props.onLocationSelect - Callback при выборе координат (lat, lon)
 * @param {Function} props.onClose - Callback при закрытии
 * @param {string} props.lang - Текущий язык (ru/uz/en)
 */
export default function LocationPicker({ initialPosition, onLocationSelect, onClose, lang = 'ru' }) {
  const [position, setPosition] = useState(
    initialPosition || { lat: 39.6542, lon: 66.9597 } // Самарканд по умолчанию
  )
  const [mapCenter, setMapCenter] = useState(
    initialPosition || { lat: 39.6542, lon: 66.9597 }
  )
  const [isLocating, setIsLocating] = useState(false)

  // Автоматически запрашиваем геолокацию при монтировании, если нет initialPosition
  useEffect(() => {
    if (!initialPosition && navigator.geolocation) {
      setIsLocating(true)
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const newPos = {
            lat: parseFloat(pos.coords.latitude.toFixed(6)),
            lon: parseFloat(pos.coords.longitude.toFixed(6)),
          }
          setPosition(newPos)
          setMapCenter(newPos)
          setIsLocating(false)
        },
        () => setIsLocating(false),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
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
          lon: parseFloat(e.latlng.lng.toFixed(6)),
        }
        setPosition(newPos)
      },
    })
    return position ? <Marker position={[position.lat, position.lon]} /> : null
  }

  // Получить текущую геолокацию
  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) return
    setIsLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const newPos = {
          lat: parseFloat(pos.coords.latitude.toFixed(6)),
          lon: parseFloat(pos.coords.longitude.toFixed(6)),
        }
        setPosition(newPos)
        setMapCenter(newPos)
        setIsLocating(false)
      },
      () => setIsLocating(false),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const handleConfirm = () => {
    onLocationSelect(position.lat, position.lon)
    onClose()
  }

  // Отправить текущую геолокацию сразу, без ожидания карты
  const handleSendCurrentLocation = () => {
    if (!navigator.geolocation) return
    setIsLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const newPos = {
          lat: parseFloat(pos.coords.latitude.toFixed(6)),
          lon: parseFloat(pos.coords.longitude.toFixed(6)),
        }
        onLocationSelect(newPos.lat, newPos.lon)
        onClose()
      },
      () => setIsLocating(false),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  return (
    <div className="fixed inset-0 z-50 bg-white flex flex-col">
      {/* Заголовок */}
      <div className="bg-blue-600 text-white px-4 py-3 flex items-center justify-between">
        <h2 className="text-base font-bold flex items-center gap-1.5"><ICONS.location size={16} /> {t('use_geolocation', lang)}</h2>
        <button onClick={onClose} className="text-xl leading-none px-2 flex items-center"><ICONS.close size={18} /></button>
      </div>

      {/* Карта — контейнер с явной высотой, чтобы leaflet корректно инициализировался.
          Явный светлый фон: в тёмной теме Telegram --tg-theme-bg-color чёрный, и если
          тайлы OSM не загрузились (нет сети в WebView), вместо карты виден чёрный экран. */}
      <div className="flex-1 relative min-h-0 bg-gray-100">
        <div className="absolute inset-0">
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
        </div>

        {/* Кнопка "Моя локация" */}
        <button
          onClick={handleGetCurrentLocation}
          disabled={isLocating}
          className="absolute top-4 right-4 z-[1000] w-11 h-11 rounded-lg bg-white border-2 border-gray-200 text-xl shadow-md flex items-center justify-center disabled:opacity-60"
          title={t('my_location', lang)}
        >
          {isLocating ? <STATUS_ICONS.pending size={20} /> : <ICONS.myLocation size={20} />}
        </button>
      </div>

      {/* Информация и кнопки */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className="text-center text-sm text-gray-500 mb-3">
          {t('coordinates', lang)}: <strong className="text-gray-900">
            {position.lat.toFixed(6)}, {position.lon.toFixed(6)}
          </strong>
        </div>
        <div className="text-center text-xs text-gray-400 mb-3">
          {t('pick_on_map_hint', lang)}
        </div>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 border border-gray-300 rounded-xl text-gray-700 font-medium"
          >
            {t('cancel', lang)}
          </button>
          <button
            onClick={handleConfirm}
            className="flex-2 py-3 bg-green-600 text-white font-semibold rounded-xl flex items-center justify-center gap-1.5"
          >
            <ICONS.confirm size={16} /> {t('confirm', lang)}
          </button>
        </div>
        {/* Отправить текущую локацию — работает без карты (если тайлы не загрузились) */}
        <button
          onClick={handleSendCurrentLocation}
          disabled={isLocating}
          className="mt-3 w-full py-3 bg-blue-600 text-white font-semibold rounded-xl flex items-center justify-center gap-1.5 disabled:opacity-60"
        >
          {isLocating ? <STATUS_ICONS.pending size={16} /> : <ICONS.myLocation size={16} />}
          {t('send_current_location', lang)}
        </button>
      </div>
    </div>
  )
}