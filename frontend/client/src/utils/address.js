// src/utils/address.js
// Единая функция: что именно будет отправлено как адрес доставки заказа.
// Используется в Cart.jsx, OrderForm.jsx, OrderEdit.jsx — везде, где есть
// address / latitude / longitude / selectedAddressId / savedAddresses.

// Нормализация координат: из API они могут прийти строками ("39.6542"),
// а toFixed() работает только с числами.
function toNumber(value) {
  if (value == null || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

export function resolveDeliveryAddress({ address, latitude, longitude, selectedAddressId, savedAddresses = [] }) {
  if (selectedAddressId) {
    const saved = savedAddresses.find((a) => a.id === selectedAddressId)
    if (saved) {
      return {
        text: saved.address_text || null,
        lat: toNumber(saved.latitude),
        lon: toNumber(saved.longitude),
        label: saved.label || null,
        isEmpty: false,
      }
    }
  }
  if (address && address.trim()) {
    return { text: address.trim(), lat: toNumber(latitude), lon: toNumber(longitude), label: null, isEmpty: false }
  }
  const lat = toNumber(latitude)
  const lon = toNumber(longitude)
  if (lat != null && lon != null) {
    return { text: null, lat, lon, label: null, isEmpty: false }
  }
  return { text: null, lat: null, lon: null, label: null, isEmpty: true }
}

// Готовая строка для UI
export function formatDeliveryAddress(resolved) {
  if (!resolved || resolved.isEmpty) return null
  if (resolved.text) return resolved.label ? `${resolved.label}: ${resolved.text}` : resolved.text
  if (resolved.lat != null && resolved.lon != null) {
    return `Точка на карте · ${resolved.lat.toFixed(5)}, ${resolved.lon.toFixed(5)}`
  }
  return null
}