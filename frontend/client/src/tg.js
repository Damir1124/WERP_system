// Инициализация Telegram WebApp SDK
let WebApp = window.Telegram?.WebApp

export function initTelegram() {
  // Перечитаем SDK после загрузки скрипта (SDK может подгрузиться чуть позже)
  WebApp = window.Telegram?.WebApp || WebApp
  if (WebApp) {
    WebApp.ready()
    WebApp.expand()
    try {
      WebApp.setHeaderColor?.('#2563eb')
    } catch {
      // не критично
    }
  }
}

// Имя пользователя Telegram (first_name + last_name, либо username).
// Используется как имя клиента при создании.
export function getTgUserName() {
  const user = window.Telegram?.WebApp?.initDataUnsafe?.user
  if (!user) return ''
  const first = user.first_name || ''
  const last = user.last_name || ''
  const full = `${first} ${last}`.trim()
  if (full) return full
  return user.username || ''
}

// Динамическое чтение tg_id (после инициализации SDK), а не на этапе импорта.
export function getTgId() {
  // 1. Из Telegram WebApp
  const user = window.Telegram?.WebApp?.initDataUnsafe?.user
  if (user?.id) return user.id

  // 2. Из sessionStorage (передано от Launcher / сохранено ранее)
  const stored = sessionStorage.getItem('tg_id')
  if (stored) {
    const n = parseInt(stored, 10)
    if (!isNaN(n)) return n
  }

  // 3. Из .env для разработки вне Telegram
  const devTgId = import.meta.env.VITE_DEV_TG_ID
  if (devTgId) {
    const n = parseInt(devTgId, 10)
    if (!isNaN(n)) return n
  }

  return null
}

// Подписанная строка initData (для авторизации на сервере)
export const initData = WebApp?.initData ?? ''

// Совместимость: значение вычисляем лениво через getter
export const tgId = getTgId()
export const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user || null

// Для dev: считается один раз при импорте — не критично, т.к. app.jsx использует getTgId()
export const devTgId = import.meta.env.VITE_DEV_TG_ID
  ? parseInt(import.meta.env.VITE_DEV_TG_ID)
  : null

// Итоговый tg_id — читаем явно (для App используется getTgId())
export const effectiveTgId = tgId ?? devTgId
