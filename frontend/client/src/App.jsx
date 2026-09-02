import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { initTelegram, getTgId, getTgUserName } from './tg.js'
import { clientApi } from './api.js'
import { detectLanguage, setLanguage, t } from './i18n.js'
import { useCart } from './cart.jsx'
import { ICONS } from './icons/water-icons.jsx'
import Catalog from './pages/Catalog.jsx'
import Cart from './pages/Cart.jsx'
import OrderForm from './pages/OrderForm.jsx'
import OrderEdit from './pages/OrderEdit.jsx'
import MyOrders from './pages/MyOrders.jsx'
import MyAddresses from './pages/MyAddresses.jsx'
import LanguageSelect from './pages/LanguageSelect.jsx'

function BottomNav({ lang }) {
  const location = useLocation()
  const path = location.pathname
  // Скрываем навигацию на страницах, где есть собственный нижний блок:
  // - оформление заказа (/order/:productId)
  // - корзина (/cart)
  // - редактирование заказа (/order/:id/edit)
  if (path.startsWith('/order/') || path === '/cart') return null

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
          <span className="text-xl leading-none mb-0.5"><ICONS.cart size={22} /></span>
          <span className="font-medium">{t('nav_catalog', lang)}</span>
        </NavLink>
        <NavLink
          to="/orders"
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center py-2 text-xs transition-colors ${
              isActive ? 'text-blue-600' : 'text-gray-500'
            }`
          }
        >
          <span className="text-xl leading-none mb-0.5"><ICONS.orders size={22} /></span>
          <span className="font-medium">{t('nav_orders', lang)}</span>
        </NavLink>
        <NavLink
          to="/addresses"
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center py-2 text-xs transition-colors ${
              isActive ? 'text-blue-600' : 'text-gray-500'
            }`
          }
        >
          <span className="text-xl leading-none mb-0.5"><ICONS.location size={22} /></span>
          <span className="font-medium">{t('nav_addresses', lang)}</span>
        </NavLink>
      </div>
    </nav>
  )
}

function AppContent() {
  const [clientStatus, setClientStatus] = useState('loading')
  const [clientData, setClientData] = useState(null)
  const [lang, setLang] = useState(detectLanguage())
  const cart = useCart()

  useEffect(() => {
    initTelegram()
    // Даём Telegram WebApp SDK время на инициализацию initDataUnsafe,
    // затем определяем tg_id и бесшовно входим.
    const timer = setTimeout(checkRegistration, 300)
    return () => clearTimeout(timer)
  }, [])

  // Бесшовный вход по tg_id: если клиент есть — загружаем профиль,
  // если нет — создаём на сервере (без ввода телефона).
  const loginByTgId = async (tgIdParam) => {
    try {
      // Передаём имя пользователя Telegram для создания клиента
      const tgName = getTgUserName()
      const data = await clientApi.loginByTgId(tgIdParam, tgName)
      // Пользователь является сотрудником (приоритет Worker над Client) —
      // перенаправляем в Launcher, чтобы он определил правильный профиль
      // (courier / operator / owner) и не создавал дубль Client.
      if (data.status === 'worker') {
        window.location.href = '/static/miniapp/launcher/index.html'
        return
      }
      setClientData({ id: data.client_id, name: data.name || tgName, phone: '', registered: true })
      // Новый клиент (status='created') — очищаем корзину прошлого пользователя
      // localStorage корзины общий для TWA, поэтому на другой аккаунт не должен переходить
      if (data.status === 'created') {
        cart.clear()
      }
      setClientStatus('registered')
    } catch (err) {
      setClientStatus('error')
    }
  }

  const checkRegistration = async () => {
    // Определяем tg_id ПОСЛЕ initTelegram() — SDK Telegram WebApp
    // инициализируется асинхронно, поэтому читаем динамически.
    const tgId = getTgId()

    if (!tgId) {
      // Вне Telegram — приложение работает только внутри Telegram
      setClientStatus('no_tg')
      return
    }

    // Сначала пробуем получить профиль (быстрый путь для существующих клиентов)
    try {
      const data = await clientApi.getProfile()
      if (data.registered) {
        setClientData(data)
        setClientStatus('registered')
        return
      }
    } catch (err) {
      // 404 — клиент не найден, создадим через loginByTgId
      if (!(err.message.includes('404') || err.message.includes('не найден'))) {
        setClientStatus('error')
        return
      }
    }
    // Клиент не найден — создаём по tg_id (без телефона)
    await loginByTgId(tgId)
  }

  const handleLanguageSelect = (code) => {
    setLanguage(code)
    setLang(code)
  }

  if (clientStatus === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-5xl mb-3 animate-pulse"><ICONS.logo size={48} /></div>
          <p className="text-gray-400 text-sm">{t('loading', lang)}</p>
        </div>
      </div>
    )
  }

  if (clientStatus === 'no_tg') {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center">
          <div className="text-5xl mb-4"><ICONS.warning size={48} /></div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">{t('open_in_telegram', lang)}</h2>
          <p className="text-gray-500 text-sm">
            {t('works_in_telegram', lang)}
          </p>
        </div>
      </div>
    )
  }

  if (clientStatus === 'error') {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center">
          <div className="text-5xl mb-4"><ICONS.error size={48} /></div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">{t('connection_error', lang)}</h2>
          <p className="text-gray-500 text-sm mb-4">{t('connection_error_hint', lang)}</p>
          <button
            onClick={checkRegistration}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-medium"
          >
            {t('retry', lang)}
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
            <h1 className="text-base font-bold">{t('app_title', lang)}</h1>
            {clientData && (
              <p className="text-blue-100 text-xs">{t('hello', lang)}, {clientData.name}!</p>
            )}
          </div>
          <button
            onClick={() => setClientStatus('lang_select')}
            className="text-sm px-2 py-1 bg-white/20 rounded-lg"
            title={t('choose_language', lang)}
          >
            <ICONS.language size={18} />
          </button>
        </div>
      </header>

      {/* Контент */}
      <main>
        <Routes>
          <Route path="/" element={<Catalog lang={lang} />} />
          <Route path="/cart" element={<Cart clientData={clientData} lang={lang} />} />
          <Route path="/order/:productId" element={<OrderForm clientData={clientData} lang={lang} />} />
          <Route path="/order/:id/edit" element={<OrderEdit lang={lang} />} />
          <Route path="/orders" element={<MyOrders lang={lang} />} />
          <Route path="/addresses" element={<MyAddresses clientData={clientData} lang={lang} />} />
        </Routes>
      </main>

      {/* Нижняя навигация */}
      <BottomNav lang={lang} />

      {/* Экран выбора языка */}
      {clientStatus === 'lang_select' && (
        <div className="fixed inset-0 z-50 bg-white/95 overflow-y-auto">
          <LanguageSelect onSelect={handleLanguageSelect} />
          <button
            onClick={() => setClientStatus('registered')}
            className="fixed bottom-4 left-0 right-0 mx-auto w-40 py-2.5 bg-gray-200 text-gray-700 rounded-xl font-medium"
          >
            {t('cancel', lang)}
          </button>
        </div>
      )}
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
