import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { initTelegram } from './tg.js'
import Pool from './pages/Pool.jsx'
import Trip from './pages/Trip.jsx'
import OrderConfirm from './pages/OrderConfirm.jsx'
import Shifts from './pages/Shifts.jsx'
import Colleagues from './pages/Colleagues.jsx'

// Заголовки для каждого маршрута
const ROUTE_TITLES = {
  '/':           { title: 'Пул заказов',    sub: 'свободные заказы' },
  '/trip':       { title: 'Мой рейс',       sub: 'активный рейс' },
  '/shifts':     { title: 'Смены',          sub: 'история' },
  '/colleagues': { title: 'Коллеги',        sub: 'на смене сегодня' },
}

function TopBar() {
  const location = useLocation()
  const isConfirm = location.pathname.startsWith('/order/')
  if (isConfirm) return null  // OrderConfirm рендерит свой topbar через page-body

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
  if (location.pathname.startsWith('/order/')) return null

  const items = [
    { to: '/',           label: 'Пул',     icon: '📦' },
    { to: '/trip',       label: 'Рейс',    icon: '🚚' },
    { to: '/shifts',     label: 'Смены',   icon: '📋' },
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
        <Route path="/order/:id/confirm"   element={<OrderConfirm />} />
        <Route path="/shifts"              element={<Shifts />} />
        <Route path="/colleagues"          element={<Colleagues />} />
      </Routes>

      <BottomNav />
    </div>
  )
}

export default function App() {
  useEffect(() => {
    initTelegram()
  }, [])

  return (
    <Router>
      <AppShell />
    </Router>
  )
}
