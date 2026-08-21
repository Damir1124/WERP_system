import { effectiveTgId as tgEffectiveTgId, initData as tgInitData } from './tg.js'

// initData: из Telegram WebApp или из sessionStorage (передан от Launcher)
const initData = tgInitData || sessionStorage.getItem('tg_init_data') || ''

// effectiveTgId: из Telegram WebApp или из sessionStorage (передан от Launcher)
const effectiveTgId =
  tgEffectiveTgId ||
  (sessionStorage.getItem('tg_id') ? parseInt(sessionStorage.getItem('tg_id')) : null)

let BASE_URL = import.meta.env.VITE_API_URL
if (!BASE_URL || BASE_URL === 'undefined') {
  BASE_URL = '/api/bot'
}
BASE_URL = BASE_URL.replace(/\/$/, '')
console.log('[Client API] BASE_URL:', BASE_URL)

async function apiFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`
  console.log(`[Client API] ${options.method || 'GET'} ${url}`)

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (effectiveTgId) {
    headers['X-Telegram-ID'] = String(effectiveTgId)
  }
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }

  const res = await fetch(url, { ...options, headers })

  if (!res.ok) {
    let errorText = ''
    try {
      const errJson = await res.json()
      errorText = errJson.error || errJson.detail || JSON.stringify(errJson)
    } catch {
      errorText = await res.text()
    }
    console.error(`[Client API] Ошибка ${res.status}:`, errorText)
    throw new Error(errorText || `HTTP ${res.status}`)
  }

  return res.json()
}

export const clientApi = {
  // Идентификация / профиль
  identify: (tgIdParam) =>
    apiFetch(`/identify/?tg_id=${tgIdParam}`, { headers: {} }),

  getProfile: () =>
    apiFetch(`/client/profile/?tg_id=${effectiveTgId}`, { headers: {} }),

  // Регистрация
  register: (data) =>
    apiFetch('/client/register/', {
      method: 'POST',
      body: JSON.stringify({ tg_id: effectiveTgId, ...data }),
    }),

  // Каталог товаров
  getProducts: () => apiFetch('/client/products/', { headers: {} }),

  // Заказы
  createOrder: (data) =>
    apiFetch('/client/order/', {
      method: 'POST',
      body: JSON.stringify({ client_tg_id: effectiveTgId, ...data }),
    }),

  getOrders: () =>
    apiFetch(`/client/orders/?tg_id=${effectiveTgId}`, { headers: {} }),

  getOrderStatus: (orderId) =>
    apiFetch(`/client/order/${orderId}/status/?tg_id=${effectiveTgId}`, { headers: {} }),
}
