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
  getCurrentShift: () => apiFetch('/shifts/current/'),
  getShiftHistory: (dateFrom, dateTo) => apiFetch(`/shifts/history/?date_from=${dateFrom}&date_to=${dateTo}`),
  getShifts:  () => apiFetch('/courier/shifts/'),
  openShift:  () => apiFetch('/shifts/', { method: 'POST' }),
  closeShift: (shiftId) => apiFetch(`/courier/shifts/${shiftId}/close/`, { method: 'POST' }),

  // ── Рейсы ─────────────────────────────────────────────────────────────────
  getTrips:   () => apiFetch('/courier/trips/'),
  openTrip:   (fullLoaded = 0, shiftId = null) => apiFetch('/trips/', {
    method: 'POST',
    body: JSON.stringify({
      full_loaded: fullLoaded,
      ...(shiftId && { shift_id: shiftId })
    }),
  }),
  closeTrip:  (tripId) => apiFetch(`/courier/trips/${tripId}/close/`, { method: 'POST' }),

  // ── Текущий рейс ──────────────────────────────────────────────────────────
  getCurrentTrip: () => apiFetch('/courier/trip/current/'),

  // ── Пул заказов ───────────────────────────────────────────────────────────
  getPool:      () => apiFetch('/courier/pool/'),
  assignOrder:  (orderId) => apiFetch(`/courier/pool/${orderId}/assign/`, { method: 'POST' }),
  returnOrderToPool: (orderId) => apiFetch(`/courier/pool/${orderId}/return/`, { method: 'POST' }),

  // ── Операции с заказами ───────────────────────────────────────────────────
  confirmOrder: (orderId, confirmed = true, items = null, note = '', newItems = null) =>
    apiFetch('/courier/orders/confirm/', {
      method: 'POST',
      body: JSON.stringify({
        order_id: orderId,
        confirmed,
        items: items,
        note,
        ...(newItems && newItems.length > 0 ? { new_items: newItems } : {}),
      }),
    }),

  updateOrderQuantity: (itemId, newQuantity) =>
    apiFetch('/courier/orders/update-quantity/', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, new_quantity: newQuantity }),
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
  
  // ── Поиск клиента по телефону (новый эндпоинт) ───────────────────────────
  searchClientByPhone: (phone) =>
    apiFetch(`/clients/search/?q=${encodeURIComponent(phone)}`),
  
  // ── Работа с адресами клиента ─────────────────────────────────────────────
  getClientAddresses: (phone) =>
    apiFetch(`/clients/addresses/${encodeURIComponent(phone)}/`),
  
  saveClientAddress: (data) =>
    apiFetch('/clients/addresses/save/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ── Оператор: заказы ─────────────────────────────────────────────────────
  getOperatorOrders: (statuses = []) => {
    const params = statuses.map(s => `status=${s}`).join('&')
    return apiFetch(`/operator/orders/${params ? '?' + params : ''}`)
  },

  getOperatorOrder: (orderId) =>
    apiFetch(`/operator/orders/${orderId}/`),

  updateOperatorOrder: (orderId, data) =>
    apiFetch(`/operator/orders/${orderId}/update/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteOperatorOrder: (orderId) =>
    apiFetch(`/operator/orders/${orderId}/delete/`, {
      method: 'DELETE',
    }),
}
