import { useState, useEffect } from 'react'
import { clientApi } from '../api.js'
import { t } from '../i18n.js'
import { ICONS } from '../icons/water-icons.jsx'
import LocationPicker from '../components/LocationPicker.jsx'

/**
 * Страница управления адресами клиента.
 * Список сохранённых адресов + добавление нового (текст / геолокация / метка) + удаление.
 *
 * @param {Object} props
 * @param {Object} props.clientData - Данные клиента {id, phone, name, ...}
 * @param {string} props.lang - Текущий язык (ru/uz/en)
 */
export default function MyAddresses({ clientData, lang = 'ru' }) {
  const [addresses, setAddresses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  // Форма добавления
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ label: '', address_text: '', latitude: null, longitude: null })
  const [showMap, setShowMap] = useState(false)
  const [saving, setSaving] = useState(false)

  const loadAddresses = async () => {
    // Если у клиента нет телефона (вход по tg_id) — не зависаем на загрузке,
    // показываем пустой список адресов.
    if (!clientData?.phone) {
      setAddresses([])
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await clientApi.getAddresses(clientData.phone)
      setAddresses(Array.isArray(data.addresses) ? data.addresses : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAddresses()
  }, [clientData?.phone])

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleLocationSelect = (lat, lon) => {
    setForm((prev) => ({ ...prev, latitude: lat, longitude: lon }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.address_text.trim() && (form.latitude == null || form.longitude == null)) {
      setError(t('address_required', lang))
      return
    }
    setSaving(true)
    setError(null)
    try {
      await clientApi.saveAddress({
        client_id: clientData.id,
        label: form.label,
        address_text: form.address_text,
        latitude: form.latitude,
        longitude: form.longitude,
      })
      setMessage(t('address_saved', lang))
      setForm({ label: '', address_text: '', latitude: null, longitude: null })
      setShowForm(false)
      await loadAddresses()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (addressId) => {
    if (!window.confirm(t('confirm_delete_address', lang))) return
    try {
      await clientApi.deleteAddress(addressId)
      setMessage(t('address_deleted', lang))
      await loadAddresses()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-900">{t('my_addresses', lang)}</h2>
        <button
          onClick={() => { setShowForm((v) => !v); setMessage(null) }}
          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
        >
          {showForm ? t('cancel', lang) : (<><ICONS.add size={14} /> {t('add_address', lang)}</>)}
        </button>
      </div>

      {message && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 font-medium">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Форма добавления */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4 space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('address_label', lang)}
            </label>
            <input
              type="text"
              name="label"
              value={form.label}
              onChange={handleChange}
              placeholder={t('address_label_placeholder', lang)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('delivery_address', lang)}
            </label>
            <input
              type="text"
              name="address_text"
              value={form.address_text}
              onChange={handleChange}
              placeholder={t('address_placeholder', lang)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm"
            />
          </div>

          <button
            type="button"
            onClick={() => setShowMap(true)}
            className="w-full py-2.5 border border-blue-300 text-blue-700 font-medium rounded-lg"
          >
            {t('use_geolocation', lang)}
          </button>

          {(form.latitude != null || form.longitude != null) && (
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <ICONS.location size={12} /> {form.latitude?.toFixed?.(6) ?? form.latitude}, {form.longitude?.toFixed?.(6) ?? form.longitude}
            </p>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl disabled:opacity-50"
          >
            {saving ? '...' : (<span className="flex items-center justify-center gap-1.5"><ICONS.save size={16} /> {t('save_address', lang)}</span>)}
          </button>
        </form>
      )}

      {/* Список адресов */}
      {loading ? (
        <div className="flex justify-center items-center h-40">
          <div className="text-center">
            <div className="text-3xl mb-2"><ICONS.location size={32} /></div>
            <p className="text-gray-500">{t('loading', lang)}</p>
          </div>
        </div>
      ) : addresses.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-5xl mb-3"><ICONS.empty size={48} /></div>
          <p className="text-gray-500 font-medium">{t('no_addresses', lang)}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {addresses.map((addr) => (
            <div key={addr.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
              <div className="flex items-start justify-between">
                <div>
                  {addr.label && (
                    <span className="inline-block px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium mb-1">
                      {addr.label}
                    </span>
                  )}
                  <p className="font-medium text-gray-900">
                    {addr.address_text || `Локация - ${addr.latitude}, ${addr.longitude}`}
                  </p>
                  {(addr.latitude != null || addr.longitude != null) && (
                    <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                      <ICONS.location size={12} /> {addr.latitude}, {addr.longitude}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(addr.id)}
                  className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
                >
                  <ICONS.delete size={14} /> {t('delete_address', lang)}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showMap && (
        <LocationPicker
          initialPosition={
            form.latitude != null && form.longitude != null
              ? { lat: form.latitude, lon: form.longitude }
              : null
          }
          onLocationSelect={handleLocationSelect}
          onClose={() => setShowMap(false)}
          lang={lang}
        />
      )}
    </div>
  )
}