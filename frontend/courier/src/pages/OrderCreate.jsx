import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import WebApp from '@twa-dev/sdk'
import LocationPicker from '../components/LocationPicker.jsx'

/**
 * Форма создания заказа курьером (OrderCreate.jsx)
 * 
 * Функционал:
 * 1. Поиск клиента по телефону с автогенерацией имени для новых
 * 2. Работа с адресом и геолокацией (текст или координаты)
 * 3. Предзаполнение "Вода 19л" x2
 * 4. Выбор типа оплаты (Наличные/Карта/Бонус)
 * 5. Валидация и отправка на backend
 */
export default function OrderCreate() {
  const navigate = useNavigate()
  
  // ─── Состояние формы ────────────────────────────────────────────────────────
  const [products, setProducts] = useState([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  
  // Клиент
  const [phone, setPhone] = useState('')
  const [phoneChecked, setPhoneChecked] = useState(false)
  const [clientFound, setClientFound] = useState(false)
  const [clientData, setClientData] = useState(null)
  const [searchingClient, setSearchingClient] = useState(false)
  
  // Имя (автогенерируется или из БД)
  const [clientName, setClientName] = useState('')
  
  // Адрес
  const [address, setAddress] = useState('')
  const [geoLocation, setGeoLocation] = useState(null) // {lat, lon}
  
  // Сохранённые адреса клиента (до 3-х)
  const [savedAddresses, setSavedAddresses] = useState([])
  const [selectedAddressId, setSelectedAddressId] = useState(null)
  
  // Товары (предзаполнение Вода 19л)
  const [orderItems, setOrderItems] = useState([])
  
  // Параметры
  const [paymentType, setPaymentType] = useState('CH') // CH/CD/BS
  const [note, setNote] = useState('')
  
  // UI
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showMapPicker, setShowMapPicker] = useState(false)
  
  // ─── Загрузка продуктов ─────────────────────────────────────────────────────
  useEffect(() => {
    api.getProducts()
      .then(data => {
        const productList = Array.isArray(data) ? data : []
        setProducts(productList)
        
        // Фильтруем продукты: 19W (вода), B19W (вода+тара), BT (тара), CL (кулеры), AR (аксессуары)
        const allowedTypes = ['19W', 'B19W', 'BT', 'CL', 'AR']
        const filtered = productList.filter(p => allowedTypes.includes(p.type_product))
        
        // Находим "Вода 19л" (type_product='19W' или 'B19W')
        const waterProduct = filtered.find(p => p.type_product === '19W' || p.type_product === 'B19W')
        
        if (waterProduct) {
          // Предзаполняем одну строку: Вода 19л x2
          setOrderItems([{ product_id: waterProduct.id, quantity: 2 }])
        } else {
          // Если нет воды, пустая строка
          setOrderItems([{ product_id: '', quantity: 1 }])
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoadingProducts(false))
  }, [])
  
  // ─── Автопоиск при вводе телефона ───────────────────────────────────────────
  useEffect(() => {
    // phone всегда хранит только "тело" номера без +998 (0-9 цифр)
    if (phone.length === 9) {
      // Запускаем поиск с задержкой 500мс
      const timer = setTimeout(() => {
        handlePhoneBlur()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [phone])

  // ─── Коды операторов Узбекистана (2 цифры сразу после +998) ────────────────
  // При появлении новых операторов/кодов достаточно дополнить этот список
  const UZ_OPERATOR_CODES = [
    '90', '91', '93', '94', '95', '97', '98', '99', // основные мобильные операторы
    '33', '88', '20', '77', '50'                     // доп. коды (Uzmobile, Perfectum, MVNO и т.п.)
  ]

  // ─── Приведение произвольного ввода к "телу" номера (9 цифр) ────────────────
  // Обрабатывает вставку в любом виде: "+998 95 555 55 55", "998955555555",
  // "895555555" (старый формат с 8), "955555555", с пробелами/скобками/дефисами и т.д.
  const extractPhoneBody = (rawInput) => {
    let digits = rawInput.replace(/\D/g, '')

    if (digits.startsWith('998') && digits.length > 9) {
      // Убираем код страны 998, если он был вставлен вместе с номером
      digits = digits.slice(3)
    } else if (digits.length === 10 && digits.startsWith('8')) {
      // Старый формат: 8 + 9 цифр
      digits = digits.slice(1)
    }

    return digits.slice(0, 9)
  }

  // ─── Форматирование тела номера для отображения: "95 555 55 55" ────────────
  const formatUzPhoneBody = (digits) => {
    const parts = []
    if (digits.length > 0) parts.push(digits.slice(0, 2))
    if (digits.length > 2) parts.push(digits.slice(2, 5))
    if (digits.length > 5) parts.push(digits.slice(5, 7))
    if (digits.length > 7) parts.push(digits.slice(7, 9))
    return parts.join(' ')
  }

  // ─── Проверка корректности тела номера (9 цифр + допустимый код оператора) ──
  const isValidUzPhoneBody = (digits) => {
    if (digits.length !== 9) return false
    return UZ_OPERATOR_CODES.includes(digits.slice(0, 2))
  }

  // ─── Обработка изменения поля телефона ──────────────────────────────────────
  const handlePhoneChange = (e) => {
    setPhone(extractPhoneBody(e.target.value))
  }

  // ─── Валидация и нормализация телефона: "+998XXXXXXXXX" либо null ──────────
  const validateAndNormalizePhone = () => {
    if (!isValidUzPhoneBody(phone)) return null
    return '+998' + phone
  }
  
  // ─── Поиск клиента по телефону ──────────────────────────────────────────────
  const handlePhoneBlur = async () => {
    if (phone.length === 0) {
      // Поле ещё пустое — не показываем ошибку раньше времени
      return
    }

    const normalized = validateAndNormalizePhone()
    
    if (!normalized) {
      if (phone.length < 9) {
        setError('Номер телефона должен содержать 9 цифр')
      } else {
        setError('Неверный код оператора. Проверьте номер телефона')
      }
      setPhoneChecked(false)
      return
    }
    
    setError(null)
    setSearchingClient(true)
    setPhoneChecked(false)
    setClientFound(false)
    setClientData(null)
    setSavedAddresses([])
    setSelectedAddressId(null)
    
    try {
      const result = await api.searchClientByPhone(normalized)
      
      // Backend возвращает либо объект клиента, либо {error: ...}
      if (result && result.id) {
        // Клиент найден
        setClientFound(true)
        setClientData(result)
        setClientName(result.name || '')
        
        // Загружаем сохранённые адреса клиента
        try {
          const addressesData = await api.getClientAddresses(normalized)
          const addresses = addressesData.addresses || []
          setSavedAddresses(addresses)
          
          // Сохранённые адреса загружены. Основное поле ввода остаётся ПУСТЫМ —
          // адрес подставляется только при явном выборе из выпадающего списка
          // (см. обработчик <select> ниже). По умолчанию выбран пункт "➕ Новый адрес".
          setAddress('')
          setGeoLocation(null)
          setSelectedAddressId(null)
        } catch (addrError) {
          console.error('Ошибка загрузки адресов:', addrError)
          // Fallback на старый адрес
          setAddress(result.address || '')
          if (result.latitude && result.longitude) {
            setGeoLocation({ lat: result.latitude, lon: result.longitude })
          }
        }
      } else {
        // Клиент не найден
        setClientFound(false)
        setClientData(null)
        setSavedAddresses([])
        
        // Автогенерация имени: "Клиент " + последние 4 цифры
        const last4 = normalized.slice(-4)
        setClientName(`Клиент ${last4}`)
        
        // Очищаем адрес для нового клиента
        setAddress('')
        setGeoLocation(null)
      }
      
      setPhoneChecked(true)
    } catch (e) {
      console.error('Ошибка поиска клиента:', e)
      // Если 404 или другая ошибка — считаем что не найден
      setClientFound(false)
      setClientData(null)
      setSavedAddresses([])
      
      const last4 = normalized.slice(-4)
      setClientName(`Клиент ${last4}`)
      
      // Очищаем адрес для нового клиента
      setAddress('')
      setGeoLocation(null)
      
      setPhoneChecked(true)
    } finally {
      setSearchingClient(false)
    }
  }
  
  // ─── Запрос геолокации ──────────────────────────────────────────────────────
  const handleRequestLocation = () => {
    // Используем стандартный HTML5 Geolocation API
    if (!navigator.geolocation) {
      setError('Геолокация не поддерживается вашим браузером')
      return
    }
    
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = parseFloat(position.coords.latitude.toFixed(6))
        const lon = parseFloat(position.coords.longitude.toFixed(6))
        setGeoLocation({ lat, lon })
        
        console.log('Location received:', { lat, lon })
      },
      (error) => {
        console.error('Geolocation error:', error)
        let errorMessage = 'Не удалось получить геолокацию'
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Доступ к геолокации запрещён. Разрешите доступ в настройках браузера.'
            break
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Информация о местоположении недоступна'
            break
          case error.TIMEOUT:
            errorMessage = 'Превышено время ожидания запроса геолокации'
            break
        }
        
        setError(errorMessage)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    )
  }
  
  // ─── Открыть выбор метки на карте ───────────────────────────────────────────
  const handleSelectLocationOnMap = () => {
    setShowMapPicker(true)
  }
  
  // ─── Обработка выбора координат на карте ────────────────────────────────────
  const handleLocationSelect = (lat, lon) => {
    setGeoLocation({ lat, lon })
    // Не заполняем адрес координатами - пользователь сам введёт текстовый адрес
  }
  
  // ─── Открыть карту (если координаты уже есть) ───────────────────────────────
  const handleOpenMap = () => {
    if (clientData && clientData.latitude && clientData.longitude) {
      const url = `https://www.google.com/maps/search/?api=1&query=${clientData.latitude},${clientData.longitude}`
      WebApp.openLink(url)
    }
  }
  
  // ─── Управление товарами ────────────────────────────────────────────────────
  const addProduct = () => {
    setOrderItems([...orderItems, { product_id: '', quantity: 1 }])
  }
  
  const removeProduct = (index) => {
    if (orderItems.length === 1) {
      setError('Должен быть хотя бы один продукт')
      return
    }
    setOrderItems(orderItems.filter((_, i) => i !== index))
  }
  
  const updateProduct = (index, field, value) => {
    const updated = [...orderItems]
    updated[index][field] = value
    setOrderItems(updated)
  }
  
  // ─── Подсчёт итоговой суммы ─────────────────────────────────────────────────
  const calculateTotal = () => {
    return orderItems.reduce((sum, item) => {
      const product = products.find(p => p.id === parseInt(item.product_id))
      if (product && product.price) {
        return sum + (product.price * item.quantity)
      }
      return sum
    }, 0)
  }
  
  // ─── Отправка формы ─────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    
    // Валидация и нормализация телефона
    const normalized = validateAndNormalizePhone()
    if (!normalized) {
      if (phone.length < 9) {
        setError('Номер телефона должен содержать 9 цифр')
      } else {
        setError('Неверный код оператора. Проверьте номер телефона')
      }
      return
    }
    
    // Проверка адреса: текст ИЛИ координаты
    if (!address && !geoLocation) {
      setError('Укажите адрес доставки')
      return
    }
    
    // Проверка товаров
    const hasEmptyProducts = orderItems.some(item => !item.product_id)
    if (hasEmptyProducts) {
      setError('Выберите продукты для всех позиций')
      return
    }
    
    if (orderItems.length === 0) {
      setError('Добавьте хотя бы один товар')
      return
    }
    
    setLoading(true)
    
    try {
      // Формируем данные для отправки
      const orderData = {
        client_name: clientName || `Клиент ${normalized.slice(-4)}`,
        client_phone: normalized,
        client_address: address || null,
        client_lat: geoLocation?.lat ? parseFloat(geoLocation.lat.toFixed(6)) : null,
        client_lon: geoLocation?.lon ? parseFloat(geoLocation.lon.toFixed(6)) : null,
        payment_type: paymentType,
        note: note || '',
        items: orderItems.map(item => ({
          product_id: parseInt(item.product_id),
          quantity: parseInt(item.quantity)
        }))
      }
      
      // Добавляем client_id только если клиент найден
      if (clientData?.id) {
        orderData.client_id = clientData.id
      }
      
      const orderResponse = await api.createOrder(orderData)
      
      // Сохраняем адрес в историю клиента
      // Для существующего клиента используем clientData.id
      // Для нового клиента получаем id из ответа: orderResponse.client.id
      const clientIdForAddress = clientData?.id || orderResponse?.client?.id
      
      console.log('Client ID для сохранения адреса:', clientIdForAddress)
      console.log('Адрес:', address)
      console.log('Координаты:', geoLocation)
      
      if (clientIdForAddress && (address || geoLocation)) {
        try {
          await api.saveClientAddress({
            client_id: clientIdForAddress,
            address_text: address || '',
            latitude: geoLocation?.lat || null,
            longitude: geoLocation?.lon || null
          })
          console.log('✅ Адрес успешно сохранён в ClientAddress')
        } catch (addrError) {
          console.error('❌ Ошибка сохранения адреса:', addrError)
          // Не блокируем создание заказа из-за ошибки сохранения адреса
        }
      } else {
        console.warn('⚠️ Адрес НЕ сохранён. Client ID:', clientIdForAddress, 'Address:', address, 'Geo:', geoLocation)
      }
      
      // Показываем уведомление и переходим в пул
      WebApp.showAlert('✅ Заказ создан', () => {
        navigate('/')
      })
    } catch (e) {
      setError(e.message || 'Ошибка при создании заказа')
    } finally {
      setLoading(false)
    }
  }
  
  // ─── Рендер ─────────────────────────────────────────────────────────────────
  // Показываем загрузку
  if (loadingProducts) {
    return (
      <div style={{ padding: '16px', display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
        <div className="spinner">Загрузка...</div>
      </div>
    )
  }
  
  // Фильтруем продукты для отображения
  const allowedTypes = ['19W', 'B19W', 'BT', 'CL', 'AR']
  const filteredProducts = products.filter(p => allowedTypes.includes(p.type_product))
  
  return (
    <div style={{ padding: '16px', paddingBottom: '80px' }}>
      {/* TopBar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        marginBottom: '20px',
        gap: '12px'
      }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '18px',
            cursor: 'pointer',
            color: 'var(--ink1)'
          }}
        >
          ←
        </button>
        <h1 style={{
          fontSize: '20px',
          fontWeight: '600',
          color: 'var(--ink1)',
          margin: 0
        }}>
          Новый заказ
        </h1>
      </div>
      
      {error && (
        <div style={{
          background: 'var(--red)',
          color: 'white',
          padding: '12px',
          borderRadius: '8px',
          marginBottom: '16px',
          fontSize: '14px'
        }}>
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        {/* ═══ СЕКЦИЯ 1: Клиент ═══ */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            fontSize: '16px',
            fontWeight: '600',
            color: 'var(--ink1)',
            marginBottom: '12px'
          }}>
            📞 Информация о клиенте
          </div>
          
          {/* Телефон */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              color: 'var(--ink2)',
              marginBottom: '6px'
            }}>
              Номер телефона *
            </label>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <div style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                background: 'var(--bg2)',
                overflow: 'hidden'
              }}>
                <span style={{
                  padding: '10px 8px 10px 12px',
                  fontSize: '14px',
                  fontWeight: '600',
                  color: 'var(--ink2)',
                  borderRight: '1px solid var(--border)',
                  userSelect: 'none'
                }}>
                  +998
                </span>
                <input
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel-national"
                  placeholder="95 555 55 55"
                  value={formatUzPhoneBody(phone)}
                  onChange={handlePhoneChange}
                  onBlur={handlePhoneBlur}
                  required
                  style={{
                    flex: 1,
                    padding: '10px 12px 10px 8px',
                    border: 'none',
                    outline: 'none',
                    fontSize: '14px',
                    background: 'transparent',
                    color: 'var(--ink1)'
                  }}
                />
              </div>
              {searchingClient && <span style={{ fontSize: '18px' }}>🔍</span>}
            </div>
            {phoneChecked && clientFound && (
              <div style={{
                fontSize: '12px',
                color: 'var(--green)',
                marginTop: '4px'
              }}>
                ✓ Клиент найден в базе
              </div>
            )}
            {phoneChecked && !clientFound && (
              <div style={{
                fontSize: '12px',
                color: 'var(--ink3)',
                marginTop: '4px'
              }}>
                Новый клиент
              </div>
            )}
          </div>
          
          {/* Имя (всегда видно) */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              color: 'var(--ink2)',
              marginBottom: '6px'
            }}>
              Имя клиента
            </label>
            <input
              type="text"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="Автоматически после проверки телефона"
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                fontSize: '14px',
                background: 'var(--bg2)',
                color: 'var(--ink1)'
              }}
            />
          </div>
          
          {/* Адрес (всегда видно) */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              color: 'var(--ink2)',
              marginBottom: '6px'
            }}>
              Адрес доставки *
            </label>
            
            {/* Dropdown выбора адреса (если есть сохранённые) */}
            {savedAddresses.length > 0 && (
              <select
                value={selectedAddressId || 'new'}
                onChange={(e) => {
                  const value = e.target.value
                  if (value === 'new') {
                    // Новый адрес - очищаем поля
                    setSelectedAddressId(null)
                    setAddress('')
                    setGeoLocation(null)
                  } else {
                    // Выбран существующий адрес
                    const addr = savedAddresses.find(a => a.id === parseInt(value))
                    if (addr) {
                      setSelectedAddressId(addr.id)
                      setAddress(addr.address_text || '')
                      if (addr.latitude && addr.longitude) {
                        setGeoLocation({
                          lat: parseFloat(addr.latitude),
                          lon: parseFloat(addr.longitude)
                        })
                      } else {
                        setGeoLocation(null)
                      }
                    }
                  }
                }}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '14px',
                  background: 'var(--bg2)',
                  color: 'var(--ink1)',
                  marginBottom: '8px'
                }}
              >
                <option value="new">➕ Новый адрес</option>
                {savedAddresses.map((addr, idx) => (
                  <option key={addr.id} value={addr.id}>
                    {idx === 0 ? '🕐 Последний' : `Адрес ${idx + 1}`}: {addr.address_text || 'Только координаты'}
                  </option>
                ))}
              </select>
            )}
            
            {/* Поле ввода адреса (всегда редактируемое) */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                type="text"
                placeholder="Введите адрес доставки"
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value)
                  // При изменении текста сбрасываем выбор на "Новый адрес"
                  if (selectedAddressId) {
                    const selectedAddr = savedAddresses.find(a => a.id === selectedAddressId)
                    if (selectedAddr && selectedAddr.address_text !== e.target.value) {
                      setSelectedAddressId(null)
                    }
                  }
                }}
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '14px',
                  background: 'var(--bg2)',
                  color: 'var(--ink1)'
                }}
              />
            </div>
            
            {/* Кнопки геолокации */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <button
                type="button"
                onClick={handleRequestLocation}
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  background: 'var(--bg2)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  color: 'var(--ink1)'
                }}
                title="Получить текущую геолокацию"
              >
                <span style={{ fontSize: '16px' }}>📡</span>
                <span>Моя локация</span>
              </button>
              <button
                type="button"
                onClick={handleSelectLocationOnMap}
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  background: 'var(--bg2)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  color: 'var(--ink1)'
                }}
                title="Выбрать метку на карте"
              >
                <span style={{ fontSize: '16px' }}>🗺️</span>
                <span>На карте</span>
              </button>
            </div>
            
            {/* Индикатор координат */}
            {geoLocation && (
              <div style={{
                padding: '8px 12px',
                background: 'rgba(52, 199, 89, 0.1)',
                border: '1px solid var(--green)',
                borderRadius: '6px',
                fontSize: '12px',
                color: 'var(--green)',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <span>✓</span>
                <span>Координаты: {geoLocation.lat.toFixed(6)}, {geoLocation.lon.toFixed(6)}</span>
              </div>
            )}
          </div>
        </div>
        
        {/* ═══ СЕКЦИЯ 2: Товары ═══ */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            fontSize: '16px',
            fontWeight: '600',
            color: 'var(--ink1)',
            marginBottom: '12px'
          }}>
            🛒 Товары в заказе
          </div>
          
          {loadingProducts ? (
            <div style={{
              padding: '20px',
              textAlign: 'center',
              color: 'var(--ink3)',
              fontSize: '14px'
            }}>
              Загрузка продуктов...
            </div>
          ) : (
            <>
              {orderItems.map((item, index) => (
                <div key={index} style={{
                  background: 'var(--bg2)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '12px',
                  marginBottom: '12px'
                }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '8px'
                  }}>
                    <span style={{
                      fontSize: '13px',
                      fontWeight: '600',
                      color: 'var(--ink1)'
                    }}>
                      Продукт #{index + 1}
                    </span>
                    {orderItems.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeProduct(index)}
                        style={{
                          background: 'var(--red)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '4px 8px',
                          fontSize: '11px',
                          cursor: 'pointer'
                        }}
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                  
                  {/* Выбор продукта */}
                  <select
                    value={item.product_id}
                    onChange={(e) => updateProduct(index, 'product_id', e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      fontSize: '14px',
                      background: 'var(--bg2)',
                      color: 'var(--ink1)',
                      marginBottom: '8px'
                    }}
                  >
                    <option value="">Выберите продукт</option>
                    {filteredProducts.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.name} — {(p.price || 0).toLocaleString('ru-RU')} сум
                      </option>
                    ))}
                  </select>
                  
                  {/* Количество */}
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '12px',
                      color: 'var(--ink2)',
                      marginBottom: '6px'
                    }}>
                      Количество
                    </label>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <button
                        type="button"
                        onClick={() => updateProduct(index, 'quantity', Math.max(1, item.quantity - 1))}
                        style={{
                          padding: '8px 12px',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          background: 'var(--bg2)',
                          fontSize: '16px',
                          cursor: 'pointer',
                          color: 'var(--ink1)'
                        }}
                      >
                        −
                      </button>
                      <span style={{
                        fontSize: '16px',
                        fontWeight: '600',
                        color: 'var(--ink1)',
                        minWidth: '30px',
                        textAlign: 'center'
                      }}>
                        {item.quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => updateProduct(index, 'quantity', item.quantity + 1)}
                        style={{
                          padding: '8px 12px',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          background: 'var(--bg2)',
                          fontSize: '16px',
                          cursor: 'pointer',
                          color: 'var(--ink1)'
                        }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              
              <button
                type="button"
                onClick={addProduct}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid var(--green)',
                  borderRadius: '8px',
                  background: 'transparent',
                  color: 'var(--green)',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  marginBottom: '12px'
                }}
              >
                ➕ Добавить продукт
              </button>
              
              {/* Итого */}
              <div style={{
                padding: '12px',
                background: 'var(--bg2)',
                borderRadius: '8px',
                fontSize: '16px',
                fontWeight: '600',
                color: 'var(--ink1)',
                textAlign: 'right'
              }}>
                Итого: {calculateTotal().toLocaleString('ru-RU')} сум
              </div>
            </>
          )}
        </div>
        
        {/* ═══ СЕКЦИЯ 3: Параметры ═══ */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            fontSize: '16px',
            fontWeight: '600',
            color: 'var(--ink1)',
            marginBottom: '12px'
          }}>
            ⚙️ Параметры заказа
          </div>
          
          {/* Тип оплаты */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              color: 'var(--ink2)',
              marginBottom: '8px'
            }}>
              Способ оплаты
            </label>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '8px'
            }}>
              {[
                { code: 'CH', label: 'Наличные', icon: '💵' },
                { code: 'CD', label: 'Карта', icon: '💳' },
                { code: 'BS', label: 'Бонус', icon: '🎁' }
              ].map(p => (
                <button
                  key={p.code}
                  type="button"
                  onClick={() => setPaymentType(p.code)}
                  style={{
                    padding: '12px 8px',
                    border: `2px solid ${paymentType === p.code ? 'var(--blue)' : 'var(--border)'}`,
                    borderRadius: '8px',
                    background: paymentType === p.code ? 'var(--blue)' : 'var(--bg2)',
                    color: paymentType === p.code ? 'white' : 'var(--ink1)',
                    fontSize: '13px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontSize: '20px' }}>{p.icon}</span>
                  <span>{p.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Примечание */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '13px',
              color: 'var(--ink2)',
              marginBottom: '6px'
            }}>
              Примечание (опционально)
            </label>
            <textarea
              placeholder="Примечание к заказу..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                fontSize: '14px',
                background: 'var(--bg2)',
                color: 'var(--ink1)',
                resize: 'vertical',
                fontFamily: 'inherit'
              }}
            />
          </div>
        </div>
        
        {/* Кнопка создания */}
        <button
          type="submit"
          disabled={loading || loadingProducts}
          style={{
            position: 'fixed',
            bottom: '80px',
            left: '16px',
            right: '16px',
            padding: '14px',
            border: 'none',
            borderRadius: '12px',
            background: loading || loadingProducts ? 'var(--ink3)' : 'var(--green)',
            color: 'white',
            fontSize: '16px',
            fontWeight: '600',
            cursor: loading || loadingProducts ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: 999
          }}
        >
          {loading ? 'Создаём...' : '✅ Создать заказ'}
        </button>
      </form>
      
      {/* Модальное окно с картой */}
      {showMapPicker && (
        <LocationPicker
          initialPosition={
            geoLocation ||
            (clientData?.latitude && clientData?.longitude
              ? { lat: parseFloat(clientData.latitude), lon: parseFloat(clientData.longitude) }
              : null)
          }
          onLocationSelect={handleLocationSelect}
          onClose={() => setShowMapPicker(false)}
        />
      )}
    </div>
  )
}
