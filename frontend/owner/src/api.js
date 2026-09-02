/**
 * API client for Owner Mini App.
 */
const API_BASE = '/api/bot';

// initData: из Telegram WebApp или из sessionStorage (передан от Launcher)
const initData =
  window.Telegram?.WebApp?.initData ||
  sessionStorage.getItem('tg_init_data') ||
  '';

// tg_id: из Telegram WebApp или из sessionStorage (передан от Launcher)
const tgId =
  window.Telegram?.WebApp?.initDataUnsafe?.user?.id ||
  sessionStorage.getItem('tg_id') ||
  '';

export async function fetchOwnerStats() {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }
  if (tgId) {
    headers['X-Telegram-ID'] = String(tgId);
  }

  const resp = await fetch(`${API_BASE}/owner/stats/`, { headers });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || err.detail || `Ошибка ${resp.status}`);
  }
  return resp.json();
}