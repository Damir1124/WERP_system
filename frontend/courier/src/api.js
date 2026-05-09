import { initData, tgId } from './tg.js'

const BASE_URL = import.meta.env.VITE_API_URL  // берётся из .env файла

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-ID': tgId,           // идентификация курьера
      'X-Telegram-Init-Data': initData, // валидация на сервере
      ...options.headers,
    },
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  getPool:        ()       => apiFetch('/api/bot/courier/pool/'),
  getCurrentTrip: ()       => apiFetch('/api/bot/courier/trip/current/'),
  deliverOrder:   (id, data) => apiFetch(`/api/bot/orders/${id}/deliver/`, {
    method: 'PATCH', body: JSON.stringify(data)
  }),
  getColleagues:  ()       => apiFetch('/api/bot/courier/colleagues/'),
  getShifts:      ()       => apiFetch('/api/bot/courier/shifts/'),
  openShift:      ()       => apiFetch('/api/bot/shifts/', { method: 'POST' }),
  openTrip:       (data)   => apiFetch('/api/bot/trips/', { method: 'POST', body: JSON.stringify(data) }),
}