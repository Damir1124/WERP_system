import WebApp from '@twa-dev/sdk'

// Вызывать один раз при старте приложения
export function initTelegram() {
  WebApp.ready()          // сообщить Telegram что приложение загрузилось
  WebApp.expand()         // раскрыть на весь экран
}

// tg_id текущего пользователя — использовать в каждом API запросе
export const tgUser = WebApp.initDataUnsafe?.user
export const tgId = tgUser?.id
export const initData = WebApp.initData  // подписанная строка — для авторизации на сервере