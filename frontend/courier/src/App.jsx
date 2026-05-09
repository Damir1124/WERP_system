import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { initTelegram } from './tg.js'
import Pool from './pages/Pool.jsx'
import Trip from './pages/Trip.jsx'
import OrderConfirm from './pages/OrderConfirm.jsx'
import Shifts from './pages/Shifts.jsx'
import Colleagues from './pages/Colleagues.jsx'

function App() {
  useEffect(() => {
    initTelegram()
  }, [])

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-xl font-bold text-gray-900">Osnova 2.0 — Курьер</h1>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link to="/" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Пул заказов
                  </Link>
                  <Link to="/trip" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Мой рейс
                  </Link>
                  <Link to="/shifts" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Смены
                  </Link>
                  <Link to="/colleagues" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Коллеги
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Pool />} />
            <Route path="/trip" element={<Trip />} />
            <Route path="/order/:id/confirm" element={<OrderConfirm />} />
            <Route path="/shifts" element={<Shifts />} />
            <Route path="/colleagues" element={<Colleagues />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App