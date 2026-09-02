import React, { useState, useEffect, useCallback } from 'react'
import { identify } from './api'

const WebApp = window.Telegram?.WebApp
const initData = WebApp?.initData || ''
const tgId = WebApp?.initDataUnsafe?.user?.id || null

// Сохраняем initData в sessionStorage для передачи в целевой Mini App
if (initData) {
  sessionStorage.setItem('tg_init_data', initData)
}
if (tgId) {
  sessionStorage.setItem('tg_id', String(tgId))
}

// Карта target_app → URL Mini App
const APP_URLS = {
  courier: '/static/miniapp/courier/index.html',
  admin: '/static/miniapp/owner/index.html',
  operator: '/static/miniapp/operator/index.html',
  client: '/static/miniapp/client/index.html',
}

// ─── Экран загрузки ──────────────────────────────────────────────────────────
function LoadingScreen({ message }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      padding: '20px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: '48px', marginBottom: '16px' }}>💧</div>
      <div style={{
        width: '40px',
        height: '40px',
        border: '3px solid #e5e7eb',
        borderTopColor: '#3b82f6',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
        marginBottom: '16px',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <p style={{ fontSize: '16px', color: '#6b7280' }}>{message || 'Загрузка...'}</p>
    </div>
  )
}

// ─── Экран ошибки ────────────────────────────────────────────────────────────
function ErrorScreen({ error, onRetry }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      padding: '20px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: '48px', marginBottom: '16px' }}>❌</div>
      <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
        Ошибка подключения
      </h2>
      <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '24px', maxWidth: '300px' }}>
        {error || 'Не удалось подключиться к серверу'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '12px 32px',
            background: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '12px',
            fontSize: '16px',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          🔄 Повторить
        </button>
      )}
    </div>
  )
}

// ─── Главный компонент Launcher ─────────────────────────────────────────────
export default function App() {
  const [state, setState] = useState('loading') // loading | redirect | error
  const [error, setError] = useState(null)

  const callIdentify = useCallback(async () => {
    setState('loading')
    setError(null)
    try {
      const result = await identify(initData)
      // Новый клиент (target_app='client' или 'registration') сразу идёт
      // в клиентский Mini App, где происходит бесшовный вход по tg_id.
      const target = result.target_app === 'registration' ? 'client' : result.target_app

      if (target && APP_URLS[target]) {
        setState('redirect')
        // Небольшая задержка, чтобы пользователь увидел "Загрузка..."
        setTimeout(() => {
          // Передаём tg_id через query-параметр (sessionStorage не переживает переход в Telegram WebView)
          const sep = APP_URLS[target].includes('?') ? '&' : '?'
          const url = tgId
            ? `${APP_URLS[target]}${sep}tg_id=${tgId}`
            : APP_URLS[target]
          window.location.href = url
        }, 500)
      } else {
        setState('error')
        setError(`Неизвестный target_app: ${result.target_app}`)
      }
    } catch (err) {
      setState('error')
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    // Сообщаем Telegram, что приложение загружено
    WebApp?.ready()
    WebApp?.expand()
    callIdentify()
  }, [callIdentify])

  if (state === 'loading') {
    return <LoadingScreen message="Определяем ваш профиль..." />
  }

  if (state === 'error') {
    return <ErrorScreen error={error} onRetry={callIdentify} />
  }

  if (state === 'redirect') {
    return <LoadingScreen message="Перенаправление..." />
  }

  return <LoadingScreen message="Загрузка..." />
}