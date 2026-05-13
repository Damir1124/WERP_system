// Инициализация Telegram WebApp SDK
const WebApp = window.Telegram?.WebApp

export function initTelegram() {
  if (WebApp) {
    WebApp.ready()
    WebApp.expand()
  }
}

export const tgUser = WebApp?.initDataUnsafe?.user
export const tgId = tgUser?.id ?? null
export const initData = WebApp?.initData ?? ''

// Для разработки вне Telegram — можно задать tg_id вручную
export const devTgId = import.meta.env.VITE_DEV_TG_ID
  ? parseInt(import.meta.env.VITE_DEV_TG_ID)
  : null

// Итоговый tg_id: из Telegram или из .env для разработки
export const effectiveTgId = tgId ?? devTgId
