import { initData as tgInitData, tgId as tgWebTgId } from './tg.js'

// initData: из Telegram WebApp или из sessionStorage (передан от Launcher)
const initData = tgInitData || sessionStorage.getItem('tg_init_data') || ''

// tgId: из Telegram WebApp или из sessionStorage (передан от Launcher)
const tgId = tgWebTgId || sessionStorage.getItem('tg_id') || ''

// Базовый URL API.
// По умолчанию — относительный путь /api/bot (запросы идут на тот же домен,
// откуда загружен Mini App — ngrok/домен). Это работает и на мобильном,
// где localhost недоступен. Для локальной разработки можно задать VITE_API_URL.
let BASE_URL = import.meta.env.VITE_API_URL
if (!BASE_URL || BASE_URL === 'undefined') {
  BASE_URL = '/api/bot'
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

  // ── Пул заказов (просмотр) ────────────────────────────────────────────────
  getPool:      () => apiFetch('/courier/pool/'),

  // ── Коллеги ───────────────────────────────────────────────────────────────
  getColleagues: () => apiFetch('/courier/colleagues/'),

  // ── Продукты и клиенты ────────────────────────────────────────────────────
  getProducts:   () => apiFetch('/products/'),

  searchClientByPhone: (phone) =>
    apiFetch(`/clients/search/?q=${encodeURIComponent(phone)}`),

  getClientAddresses: (phone) =>
    apiFetch(`/clients/addresses/${encodeURIComponent(phone)}/`),

  saveClientAddress: (data) =>
    apiFetch('/clients/addresses/save/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createOrder: (data) =>
    apiFetch('/courier/orders/create/', {
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