import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { initTelegram } from './tg.js'
import Pool from './pages/Pool.jsx'
import Trip from './pages/Trip.jsx'
import OrderConfirm from './pages/OrderConfirm.jsx'
import Shifts from './pages/Shifts.jsx'
import Colleagues from './pages/Colleagues.jsx'

function BottomNav() {
  const navItems = [
    { to: '/', label: 'Пул', icon: '📦' },
    { to: '/trip', label: 'Рейс', icon: '🚚' },
    { to: '/shifts', label: 'Смены', icon: '📋' },
    { to: '/colleagues', label: 'Коллеги', icon: '👥' },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50 safe-area-bottom">
      <div className="flex">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2 text-xs transition-colors ${
                isActive
                  ? 'text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`
            }
          >
            <span className="text-xl leading-none mb-0.5">{icon}</span>
            <span className="font-medium">{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

function App() {
  useEffect(() => {
    initTelegram()
  }, [])

  return (
    <Router>
      <div className="min-h-screen bg-gray-50 pb-16">
        {/* Заголовок */}
        <header className="bg-indigo-600 text-white px-4 py-3 sticky top-0 z-40">
          <h1 className="text-base font-bold">Osnova 2.0 — Курьер</h1>
        </header>

        {/* Контент */}
        <main className="px-3 py-4">
          <Routes>
            <Route path="/" element={<Pool />} />
            <Route path="/trip" element={<Trip />} />
            <Route path="/order/:id/confirm" element={<OrderConfirm />} />
            <Route path="/shifts" element={<Shifts />} />
            <Route path="/colleagues" element={<Colleagues />} />
          </Routes>
        </main>

        {/* Нижняя навигация */}
        <BottomNav />
      </div>
    </Router>
  )
}

export default App
