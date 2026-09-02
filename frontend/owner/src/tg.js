/**
 * Telegram WebApp integration.
 */
const tg = window.Telegram?.WebApp;

export function getInitData() {
  return tg?.initData || '';
}

export function getInitDataUnsafe() {
  return tg?.initDataUnsafe || {};
}

export function ready() {
  tg?.ready();
}

export function expand() {
  tg?.expand();
}

export function close() {
  tg?.close();
}

export function showAlert(msg) {
  tg?.showAlert(msg);
}

export function getUser() {
  return tg?.initDataUnsafe?.user || null;
}