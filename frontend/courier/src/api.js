import { initData, tgId } from './tg.js'

// Базовый URL API, берется из переменной окружения VITE_API_URL
let BASE_URL = import.meta.env.VITE_API_URL
if (!BASE_URL || BASE_URL === 'undefined') {
  console.warn('VITE_API_URL не задан, используем http://localhost:8000/api/bot')
  BASE_URL = 'http://localhost:8000/api/bot'
}
BASE_URL = BASE_URL.replace(/\/$/, '')
console.log('API BASE_URL:', BASE_URL)

async function apiFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`
  console.log(`[API] ${options.method || 'GET'} ${url}`)

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  // Добавляем Telegram заголовки только если они доступны
  if (tgId) {
    headers['X-Telegram-ID'] = String(tgId)
  }
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }

  const res = await fetch(url, { ...options, headers })

  if (!res.ok) {
    // Клонируем ответ, чтобы можно было прочитать тело несколько раз
    const responseClone = res.clone()
    let errorText = ''
    try {
      const errJson = await responseClone.json()
      errorText = errJson.error || errJson.detail || JSON.stringify(errJson)
    } catch {
      // Если не JSON, читаем как текст
      errorText = await res.text()
    }
    console.error(`[API] Ошибка ${res.status}:`, errorText)
    throw new Error(errorText || `HTTP ${res.status}`)
  }

  return res.json()
}

export const api = {
  // ── Идентификация ──────────────────────────────────────────────────────────
  identify: (tgIdParam) =>
    apiFetch(`/identify/?tg_id=${tgIdParam}`, { headers: {} }),

  // ── Профиль курьера ────────────────────────────────────────────────────────
  getProfile: () => apiFetch('/courier/profile/'),

  // ── Смены ─────────────────────────────────────────────────────────────────
  getShifts:  () => apiFetch('/courier/shifts/'),
  openShift:  () => apiFetch('/courier/shifts/', { method: 'POST' }),
  closeShift: (shiftId) => apiFetch(`/courier/shifts/${shiftId}/close/`, { method: 'POST' }),

  // ── Рейсы ─────────────────────────────────────────────────────────────────
  getTrips:   () => apiFetch('/courier/trips/'),
  openTrip:   (fullLoaded = 0) => apiFetch('/courier/trips/', {
    method: 'POST',
    body: JSON.stringify({ full_loaded: fullLoaded }),
  }),

  // ── Текущий рейс ──────────────────────────────────────────────────────────
  getCurrentTrip: () => apiFetch('/courier/trip/current/'),

  // ── Пул заказов ───────────────────────────────────────────────────────────
  getPool:      () => apiFetch('/courier/pool/'),
  assignOrder:  (orderId) => apiFetch(`/courier/pool/${orderId}/assign/`, { method: 'POST' }),

  // ── Операции с заказами ───────────────────────────────────────────────────
  confirmOrder: (orderId, confirmed = true, containerOp = null, note = '') =>
    apiFetch('/courier/orders/confirm/', {
      method: 'POST',
      body: JSON.stringify({
        order_id: orderId,
        confirmed,
        container_op: containerOp,
        note,
      }),
    }),

  updateOrderQuantity: (orderId, newQuantity) =>
    apiFetch('/courier/orders/update-quantity/', {
      method: 'POST',
      body: JSON.stringify({ order_id: orderId, new_quantity: newQuantity }),
    }),

  createOrder: (data) =>
    apiFetch('/courier/orders/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getTripOrders: (tripId) => apiFetch(`/courier/trips/${tripId}/orders/`),

  // ── Коллеги ───────────────────────────────────────────────────────────────
  getColleagues: () => apiFetch('/courier/colleagues/'),

  // ── Продукты и клиенты ────────────────────────────────────────────────────
  getProducts:   () => apiFetch('/products/'),
  searchClients: (phone = '', address = '') =>
    apiFetch(`/clients/?phone=${encodeURIComponent(phone)}&address=${encodeURIComponent(address)}`),
}
