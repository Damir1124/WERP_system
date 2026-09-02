import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import WebApp from '@twa-dev/sdk'
import LocationPicker from '../components/LocationPicker.jsx'

/**
 * Форма редактирования заказа оператором (OrderEdit.jsx)
 *
 * Функционал:
 * 1. Загрузка текущих данных заказа
 * 2. Редактирование телефона клиента (с поиском/созданием)
 * 3. Редактирование адреса (с выбором из сохранённых)
 * 4. Редактирование товаров (добавление/удаление/изменение количества)
 */
export default function OrderEdit() {
  const { id } = useParams()
  const orderId = id
  const navigate = useNavigate()

  // ─── Состояние формы ────────────────────────────────────────────────────────
  const [products, setProducts] = useState([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [loadingOrder, setLoadingOrder] = useState(true)

  // Клиент
  const [phone, setPhone] = useState('')
  const [phoneChecked, setPhoneChecked] = useState(false)
  const [clientFound, setClientFound] = useState(false)
  const [clientData, setClientData] = useState(null)
  const [searchingClient, setSearchingClient] = useState(false)
  const [clientName, setClientName] = useState('')

  // Адрес
  const [address, setAddress] = useState('')
  const [geoLocation, setGeoLocation] = useState(null)
  const [savedAddresses, setSavedAddresses] = useState([])
  const [selectedAddressId, setSelectedAddressId] = useState(null)

  // Товары
  const [orderItems, setOrderItems] = useState([])

  // Примечание
  const [note, setNote] = useState('')

  // UI
  const [loading, setLoading] = useState(false)
  const [loadingAddresses, setLoadingAddresses] = useState(false)
  const [error, setError] = useState(null)
  const [showMapPicker, setShowMapPicker] = useState(false)

  // ─── Загрузка данных ────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [productsData, orderData] = await Promise.all([
          api.getProducts(),
          api.getOperatorOrder(orderId),
        ])

        if (cancelled) return

        const productList = Array.isArray(productsData) ? productsData : []
        setProducts(productList)
        setLoadingProducts(false)

        if (orderData) {
          // Заполняем телефон
          const rawPhone = orderData.client_phone || ''
          const phoneDigits = rawPhone.replace(/\D/g, '')
          const phoneBody = phoneDigits.startsWith('998') ? phoneDigits.slice(3) : phoneDigits
          setPhone(phoneBody.slice(0, 9))

          // Заполняем адрес
          setAddress(orderData.delivery_address_text || '')

          // Заполняем координаты
          if (orderData.delivery_latitude && orderData.delivery_longitude) {
            setGeoLocation({
              lat: parseFloat(orderData.delivery_latitude),
              lon: parseFloat(orderData.delivery_longitude),
            })
          }

          // Заполняем имя клиента
          setClientName(orderData.client_name || '')

          // Заполняем примечание
          setNote(orderData.note || '')

          // Заполняем товары
          if (orderData.items && orderData.items.length > 0) {
            setOrderItems(orderData.items.map(item => ({
              product_id: item.product,
              quantity: item.quantity,
            })))
          } else {
            setOrderItems([{ product_id: '', quantity: 1 }])
          }

          // Если есть клиент, ищем его адреса
          if (orderData.client_phone) {
            await loadClientAddresses(orderData.client_phone)
          }
        }

        setLoadingOrder(false)
      } catch (e) {
        if (!cancelled) {
          setError(e.message)
          setLoadingOrder(false)
          setLoadingProducts(false)
        }
      }
    }

    load()
    return () => { cancelled = true }
  }, [orderId])

  // ─── Загрузка адресов клиента ───────────────────────────────────────────────
  const loadClientAddresses = async (phoneNumber) => {
    setLoadingAddresses(true)
    try {
      const data = await api.getClientAddresses(phoneNumber)
      setSavedAddresses(data.addresses || [])
    } catch (e) {
      console.warn('Не удалось загрузить адреса:', e)
      setSavedAddresses([])
    } finally {
      setLoadingAddresses(false)
    }
  }

  const extractPhoneBody = (rawInput) => {
    let digits = rawInput.replace(/\D/g, '')
    if (digits.startsWith('998') && digits.length > 9) {
      digits = digits.slice(3)
    } else if (digits.length === 10 && digits.startsWith('8')) {
      digits = digits.slice(1)
    }
    return digits.slice(0, 9)
  }

  const formatUzPhoneBody = (digits) => {
    const parts = []
    if (digits.length > 0) parts.push(digits.slice(0, 2))
    if (digits.length > 2) parts.push(digits.slice(2, 5))
    if (digits.length > 5) parts.push(digits.slice(5, 7))
    if (digits.length > 7) parts.push(digits.slice(7, 9))
    return parts.join(' ')
  }

  // Валидация кода оператора намеренно убрана — принимаем любые 9 цифр.
  const isValidUzPhoneBody = (digits) => {
    return digits.length === 9
  }

  const handlePhoneChange = (e) => {
    setPhone(extractPhoneBody(e.target.value))
  }

  const validateAndNormalizePhone = () => {
    if (!isValidUzPhoneBody(phone)) return null
    return '+998' + phone
  }

  // ─── Поиск клиента по телефону ──────────────────────────────────────────────
  const handlePhoneBlur = async () => {
    if (phone.length === 0) return

    const normalized = validateAndNormalizePhone()
    if (!normalized) {
      setError('Номер телефона должен содержать 9 цифр')
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
    setLoadingAddresses(true)

    const [searchResult, addressesResult] = await Promise.allSettled([
      api.searchClientByPhone(normalized),
      api.getClientAddresses(normalized),
    ])

    const result = searchResult.status === 'fulfilled' ? searchResult.value : null
    const addressesData = addressesResult.status === 'fulfilled' ? addressesResult.value : null

    if (result && result.id) {
      setClientFound(true)
      setClientData(result)
      setClientName(result.name || '')
      if (addressesData) {
        setSavedAddresses(addressesData.addresses || [])
      }
      setAddress('')
      setGeoLocation(null)
      setSelectedAddressId(null)
    } else {
      setClientFound(false)
      setClientData(null)
      setSavedAddresses([])
      const last4 = normalized.slice(-4)
      setClientName(`Клиент ${last4}`)
      setAddress('')
      setGeoLocation(null)
    }

    setLoadingAddresses(false)
    setPhoneChecked(true)
    setSearchingClient(false)
  }

  // ─── Геолокация и карта ─────────────────────────────────────────────────────
  const handleRequestLocation = () => {
    if (!navigator.geolocation) {
      setError('Геолокация не поддерживается')
      return
    }
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGeoLocation({
          lat: parseFloat(position.coords.latitude.toFixed(6)),
          lon: parseFloat(position.coords.longitude.toFixed(6)),
        })
      },
      (error) => {
        let msg = 'Не удалось получить геолокацию'
        if (error.code === error.PERMISSION_DENIED) msg = 'Доступ запрещён'
        setError(msg)
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  const handleLocationSelect = (lat, lon) => {
    setGeoLocation({ lat, lon })
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

  // ─── Отправка формы ─────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    const normalized = validateAndNormalizePhone()
    if (!normalized) {
      setError('Номер телефона должен содержать 9 цифр')
      return
    }

    if (!address && !geoLocation) {
      setError('Укажите адрес доставки')
      return
    }

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
      const updateData = {
        client_phone: normalized,
        client_name: clientName || `Клиент ${normalized.slice(-4)}`,
        client_address: address || null,
        client_lat: geoLocation?.lat ? parseFloat(geoLocation.lat.toFixed(6)) : null,
        client_lon: geoLocation?.lon ? parseFloat(geoLocation.lon.toFixed(6)) : null,
        items: orderItems.map(item => ({
          product_id: parseInt(item.product_id),
          quantity: parseInt(item.quantity),
        })),
        note: note || '',
      }

      if (clientData?.id) {
        updateData.client_id = clientData.id
      }

      await api.updateOperatorOrder(orderId, updateData)

      WebApp.showAlert('✅ Заказ обновлён', () => {
        navigate('/all-orders')
      })
    } catch (e) {
      setError(e.message || 'Ошибка при обновлении заказа')
    } finally {
      setLoading(false)
    }
  }

  // ─── Рендер ─────────────────────────────────────────────────────────────────
  if (loadingOrder || loadingProducts) {
    return (
      <div style={{ padding: '16px', display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
        <div className="spinner">Загрузка данных заказа...</div>
      </div>
    )
  }

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
          Редактировать заказ
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
              <div style={{ fontSize: '12px', color: 'var(--green)', marginTop: '4px' }}>
                ✓ Клиент найден
              </div>
            )}
            {phoneChecked && !clientFound && (
              <div style={{ fontSize: '12px', color: 'var(--ink3)', marginTop: '4px' }}>
                Новый клиент
              </div>
            )}
          </div>

          {/* Имя */}
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
              placeholder="Имя клиента"
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

          {/* Адрес */}
          <div style={{ marginBottom: '12px' }}>
            <label style={{
              display: 'block',
              fontSize: '13px',
              color: 'var(--ink2)',
              marginBottom: '6px'
            }}>
              Адрес доставки *
            </label>

            {clientFound && (
              <select
                value={selectedAddressId || 'new'}
                onChange={(e) => {
                  const value = e.target.value
                  if (value === 'new') {
                    setSelectedAddressId(null)
                    setAddress('')
                    setGeoLocation(null)
                  } else {
                    const addr = savedAddresses.find(a => a.id === parseInt(value))
                    if (addr) {
                      setSelectedAddressId(addr.id)
                      setAddress(addr.address_text || '')
                      if (addr.latitude && addr.longitude) {
                        setGeoLocation({ lat: parseFloat(addr.latitude), lon: parseFloat(addr.longitude) })
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
                {loadingAddresses ? (
                  <option value="new" disabled>⏳ Загрузка адресов...</option>
                ) : savedAddresses.length === 0 ? (
                  <option value="new">➕ Новый адрес</option>
                ) : (
                  <>
                    <option value="new">➕ Новый адрес</option>
                    {savedAddresses.map((addr, idx) => (
                      <option key={addr.id} value={addr.id}>
                        {idx === 0 ? '🕐 Последний' : `Адрес ${idx + 1}`}: {addr.address_text || 'Только координаты'}
                      </option>
                    ))}
                  </>
                )}
              </select>
            )}

            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                type="text"
                placeholder="Введите адрес доставки"
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value)
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
              >
                <span style={{ fontSize: '16px' }}>📡</span>
                <span>Моя локация</span>
              </button>
              <button
                type="button"
                onClick={() => setShowMapPicker(true)}
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
              >
                <span style={{ fontSize: '16px' }}>🗺️</span>
                <span>На карте</span>
              </button>
            </div>

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
                <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--ink1)' }}>
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

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--ink2)', marginBottom: '6px' }}>
                  Количество
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
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
                  <span style={{ fontSize: '16px', fontWeight: '600', color: 'var(--ink1)', minWidth: '30px', textAlign: 'center' }}>
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
        </div>

        {/* ═══ СЕКЦИЯ 3: Примечание ═══ */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            fontSize: '16px',
            fontWeight: '600',
            color: 'var(--ink1)',
            marginBottom: '12px'
          }}>
            Примечание
          </div>
          <textarea
            placeholder="Примечание к заказу..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
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

        {/* Кнопка сохранения */}
        <div style={{
          position: 'sticky',
          bottom: '0',
          padding: '12px 0 24px',
          background: 'var(--bg2)',
          zIndex: 100,
        }}>
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '14px',
              border: 'none',
              borderRadius: '12px',
              background: loading ? 'var(--ink3)' : 'var(--blue)',
              color: 'white',
              fontSize: '16px',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            }}
          >
            {loading ? 'Сохраняем...' : '💾 Сохранить изменения'}
          </button>
        </div>
      </form>

      {/* Модальное окно с картой */}
      {showMapPicker && (
        <LocationPicker
          initialPosition={geoLocation || null}
          onLocationSelect={handleLocationSelect}
          onClose={() => setShowMapPicker(false)}
        />
      )}
    </div>
  )
}