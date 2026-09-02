/**
 * API client for Launcher Mini App.
 */
const API_BASE = '/api/bot';

export async function identify(initData) {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }

  const resp = await fetch(`${API_BASE}/identify/`, { headers });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || err.detail || `Ошибка ${resp.status}`);
  }
  return resp.json();
}

export async function registerClient(phone, initData) {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }

  const resp = await fetch(`${API_BASE}/client/register/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ phone }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || err.detail || `Ошибка ${resp.status}`);
  }
  return resp.json();
}