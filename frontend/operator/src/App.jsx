import React, { useEffect, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { initTelegram } from './tg.js'
import Pool from './pages/Pool.jsx'
import RefreshContext, { useRefresh } from './refreshContext.js'
import Colleagues from './pages/Colleagues.jsx'
import OrderCreate from './pages/OrderCreate.jsx'
import AllOrders from './pages/AllOrders.jsx'
import OrderEdit from './pages/OrderEdit.jsx'

// Заголовки для каждого маршрута
const ROUTE_TITLES = {
  '/':            { title: 'Пул заказов',    sub: 'свободные заказы' },
  '/colleagues':  { title: 'Коллеги',        sub: 'на смене сегодня' },
  '/all-orders':  { title: 'Все заказы',     sub: 'за последние 24 часа' },
  '/orders/:id/edit': { title: 'Редактирование', sub: 'заказ' },
}

function TopBar() {
  const location = useLocation()
  const info = ROUTE_TITLES[location.pathname] || { title: 'Osnova 2.0', sub: '' }
  return (
    <div className="topbar">
      <span className="tb-title">{info.title}</span>
      {info.sub && <span className="tb-sub">{info.sub}</span>}
      <span className="tb-sub" style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.15)', padding: '2px 8px', borderRadius: '10px', fontSize: '10px' }}>
        Оператор
      </span>
    </div>
  )
}

function BottomNav() {
  const location = useLocation()
  if (location.pathname.startsWith('/order/') || location.pathname === '/orders/create' || location.pathname.match(/^\/orders\/\d+\/edit$/)) return null

  const items = [
    { to: '/',           label: 'Пул',     icon: '📦' },
    { to: '/colleagues', label: 'Коллеги', icon: '👥' },
    { to: '/all-orders', label: 'Заказы',  icon: '📋' },
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
  const { refresh } = useRefresh()

  // Не показываем FAB на страницах создания и редактирования заказа
  const showFAB = location.pathname !== '/orders/create' && !location.pathname.match(/^\/orders\/\d+\/edit$/)
  if (!showFAB) return null

  // Refresh-FAB виден на страницах пула (/) и коллег (/colleagues)
  const showRefreshFAB = location.pathname === '/' || location.pathname === '/colleagues'

  return (
    <>
      {showRefreshFAB && (
        <button
          onClick={refresh}
          style={{
            position: 'fixed',
            bottom: '124px',
            right: '20px',
            width: '52px',
            height: '52px',
            borderRadius: '50%',
            background: '#3b82f6',
            color: 'white',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            zIndex: 1000,
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title={location.pathname === '/colleagues' ? 'Обновить коллег' : 'Обновить пул заказов'}
        >
          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <polyline points="21 3 21 9 15 9" />
          </svg>
        </button>
      )}
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
    </>
  )
}

function AppShell() {
  const refreshRef = useRef(null)

  const registerRefresh = (fn) => {
    refreshRef.current = fn
  }

  const refresh = () => {
    if (typeof refreshRef.current === 'function') {
      refreshRef.current()
    }
  }

  return (
    <RefreshContext.Provider value={{ registerRefresh, refresh }}>
    <div className="app-shell">
      <TopBar />

      <Routes>
        <Route path="/"                    element={<Pool />} />
        <Route path="/colleagues"          element={<Colleagues />} />
        <Route path="/orders/create"       element={<OrderCreate />} />
        <Route path="/orders/:id/edit"     element={<OrderEdit />} />
        <Route path="/all-orders"          element={<AllOrders />} />
      </Routes>

      <BottomNav />
      <FAB />
    </div>
    </RefreshContext.Provider>
  )
}

export default function App() {
  useEffect(() => {
    initTelegram()
  }, [])

  // Доступ контролирует backend (permissions.py) на каждом API-эндпоинте.
  // Launcher уже перенаправил пользователя в правильный Mini App.
  return (
    <Router>
      <AppShell />
    </Router>
  )
}