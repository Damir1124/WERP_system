import React, { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { initTelegram, tgId } from './tg.js'
import Pool from './pages/Pool.jsx'
import Trip from './pages/Trip.jsx'
import TripClose from './pages/TripClose.jsx'
import OrderConfirm from './pages/OrderConfirm.jsx'
import OrderCreate from './pages/OrderCreate.jsx'
import Shift from './pages/Shift.jsx'
import ShiftClose from './pages/ShiftClose.jsx'
import ShiftHistory from './pages/ShiftHistory.jsx'
import Shifts from './pages/Shifts.jsx'
import Colleagues from './pages/Colleagues.jsx'

// Заголовки для каждого маршрута
const ROUTE_TITLES = {
  '/':            { title: 'Пул заказов',    sub: 'свободные заказы' },
  '/trip':        { title: 'Мой рейс',       sub: 'активный рейс' },
  '/trip/close':  { title: 'Закрытие рейса', sub: 'итоги' },
  '/shift':       { title: '🚛 Текущая смена', sub: 'статистика и рейсы' },
  '/shift/close': { title: 'Закрытие смены', sub: 'итоги' },
  '/shifts':      { title: 'Смены',          sub: 'история' },
  '/colleagues':  { title: 'Коллеги',        sub: 'на смене сегодня' },
}

function TopBar() {
  const location = useLocation()
  const isConfirm = location.pathname.startsWith('/order/')
  const isTripClose = location.pathname === '/trip/close'
  const isShiftClose = location.pathname === '/shift/close'
  if (isConfirm || isTripClose || isShiftClose) return null  // Эти страницы рендерят свой topbar

  const info = ROUTE_TITLES[location.pathname] || { title: 'Osnova 2.0', sub: '' }
  return (
    <div className="topbar">
      <span className="tb-title">{info.title}</span>
      {info.sub && <span className="tb-sub">{info.sub}</span>}
    </div>
  )
}

function BottomNav() {
  const location = useLocation()
  if (location.pathname.startsWith('/order/') || location.pathname === '/trip/close' || location.pathname === '/shift/close') return null

  const items = [
    { to: '/',           label: 'Пул',     icon: '📦' },
    { to: '/trip',       label: 'Рейс',    icon: '🚚' },
    { to: '/shift',      label: 'Смена',   icon: '🌅' },
    { to: '/colleagues', label: 'Коллеги', icon: '👥' },
  ]

  return (
    <nav className="bottom-nav">
      {items.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
        >
          <span className="nav-icon">{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

function FAB() {
  const navigate = useNavigate()
  const location = useLocation()

  // Не показываем FAB на странице создания заказа
  const showFAB = location.pathname !== '/orders/create'

  if (!showFAB) return null

  return (
    <button
      onClick={() => navigate('/orders/create')}
      style={{
        position: 'fixed',
        bottom: '60px',
        right: '20px',
        width: '52px',
        height: '52px',
        borderRadius: '50%',
        background: '#3b82f6',
        color: 'white',
        fontSize: '28px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        zIndex: 1000,
        border: 'none',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: '300',
        lineHeight: '1'
      }}
      title="Создать заказ"
    >
      +
    </button>
  )
}

function AppShell() {
  const location = useLocation()
  const isConfirm = location.pathname.startsWith('/order/')

  return (
    <div className="app-shell">
      <TopBar />

      {/* Для экрана подтверждения — свой topbar внутри страницы */}
      {isConfirm && (
        <div className="topbar">
          <NavLink to="/trip" className="tb-back">←</NavLink>
          <span className="tb-title">Подтверждение доставки</span>
        </div>
      )}

      <Routes>
        <Route path="/"                    element={<Pool />} />
        <Route path="/trip"                element={<Trip />} />
        <Route path="/trip/close"          element={<TripClose />} />
        <Route path="/order/:id/confirm"   element={<OrderConfirm />} />
        <Route path="/orders/create"       element={<OrderCreate />} />
        <Route path="/shift"               element={<Shift />} />
        <Route path="/shift/close"         element={<ShiftClose />} />
        <Route path="/shifts"              element={<Shifts />} />
        <Route path="/shifts/history"      element={<ShiftHistory />} />
        <Route path="/colleagues"          element={<Colleagues />} />
      </Routes>

      <BottomNav />
      <FAB />
    </div>
  )
}

function AccessDenied() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      padding: '20px',
      textAlign: 'center',
      background: '#f8f9fa',
    }}>
      <div style={{ fontSize: '48px', marginBottom: '16px' }}>🚫</div>
      <h1 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>
        Доступ запрещён
      </h1>
      <p style={{ fontSize: '14px', color: '#666', maxWidth: '300px' }}>
        Mini App доступно только для курьеров. Обратитесь к администратору.
      </p>
    </div>
  )
}

export default function App() {
  const [access, setAccess] = React.useState({ loading: true, granted: false })

  useEffect(() => {
    initTelegram()
    checkAccess()
  }, [])

  async function checkAccess() {
    try {
      const { api } = await import('./api.js')
      const data = await api.identify(tgId)
      // Курьерскому приложению доступны роли COURIER и admin (по target_app)
      const allowedRoles = ['COURIER']
      const allowedApps = ['courier', 'admin']
      if (allowedRoles.includes(data.role) || allowedApps.includes(data.target_app)) {
        setAccess({ loading: false, granted: true })
      } else {
        setAccess({ loading: false, granted: false })
        console.warn('[Access] Роль не имеет доступа к курьерскому Mini App:', data.role, data)
      }
    } catch (err) {
      console.error('[Access] Ошибка проверки доступа:', err)
      setAccess({ loading: false, granted: false })
    }
  }

  if (access.loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        fontSize: '16px',
        color: '#666',
      }}>
        Проверка доступа...
      </div>
    )
  }

  if (!access.granted) {
    return <AccessDenied />
  }

  return (
    <Router>
      <AppShell />
    </Router>
  )
}
