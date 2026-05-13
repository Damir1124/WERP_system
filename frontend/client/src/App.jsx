import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { initTelegram, effectiveTgId } from './tg.js'
import { clientApi } from './api.js'
import Catalog from './pages/Catalog.jsx'
import OrderForm from './pages/OrderForm.jsx'
import MyOrders from './pages/MyOrders.jsx'
import Register from './pages/Register.jsx'

function BottomNav() {
  const location = useLocation()
  // Скрываем навигацию на странице оформления заказа
  if (location.pathname.startsWith('/order/')) return null

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="flex">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center py-2 text-xs transition-colors ${
              isActive ? 'text-blue-600' : 'text-gray-500'
            }`
          }
        >
          <span className="text-xl leading-none mb-0.5">🛒</span>
          <span className="font-medium">Каталог</span>
        </NavLink>
        <NavLink
          to="/orders"
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center py-2 text-xs transition-colors ${
              isActive ? 'text-blue-600' : 'text-gray-500'
            }`
          }
        >
          <span className="text-xl leading-none mb-0.5">📦</span>
          <span className="font-medium">Заказы</span>
        </NavLink>
      </div>
    </nav>
  )
}

function AppContent() {
  const [clientStatus, setClientStatus] = useState('loading')
  const [clientData, setClientData] = useState(null)

  useEffect(() => {
    initTelegram()
    checkRegistration()
  }, [])

  const checkRegistration = async () => {
    if (!effectiveTgId) {
      setClientStatus('no_tg')
      return
    }
    try {
      const data = await clientApi.getProfile()
      if (data.registered) {
        setClientData(data)
        setClientStatus('registered')
      } else {
        setClientStatus('unknown')
      }
    } catch (err) {
      if (err.message.includes('404') || err.message.includes('не найден')) {
        setClientStatus('unknown')
      } else {
        setClientStatus('error')
      }
    }
  }

  const handleRegistered = (data) => {
    setClientData(data)
    setClientStatus('registered')
  }

  if (clientStatus === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-5xl mb-3 animate-pulse">💧</div>
          <p className="text-gray-400 text-sm">Загрузка...</p>
        </div>
      </div>
    )
  }

  if (clientStatus === 'no_tg') {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Откройте в Telegram</h2>
          <p className="text-gray-500 text-sm">
            Это приложение работает только внутри Telegram.
          </p>
        </div>
      </div>
    )
  }

  if (clientStatus === 'unknown') {
    return <Register onRegistered={handleRegistered} />
  }

  if (clientStatus === 'error') {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center">
          <div className="text-5xl mb-4">❌</div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Ошибка подключения</h2>
          <p className="text-gray-500 text-sm mb-4">Не удалось подключиться к серверу</p>
          <button
            onClick={checkRegistration}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-medium"
          >
            Повторить
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      {/* Заголовок */}
      <header className="bg-blue-600 text-white px-4 py-3 sticky top-0 z-40">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-base font-bold">💧 Osnova 2.0</h1>
            {clientData && (
              <p className="text-blue-100 text-xs">Привет, {clientData.name}!</p>
            )}
          </div>
        </div>
      </header>

      {/* Контент */}
      <main>
        <Routes>
          <Route path="/" element={<Catalog />} />
          <Route path="/order/:productId" element={<OrderForm clientData={clientData} />} />
          <Route path="/orders" element={<MyOrders />} />
        </Routes>
      </main>

      {/* Нижняя навигация */}
      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  )
}
