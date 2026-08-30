import { useState } from 'react'
import { clientApi } from '../api.js'
import { effectiveTgId } from '../tg.js'
import { t } from '../i18n.js'
import { ICONS } from '../icons/water-icons.jsx'
import PhoneInput, { validateAndNormalizePhone } from '../components/PhoneInput.jsx'

export default function Register({ onRegistered, onLogin, lang = 'ru' }) {
  const [form, setForm] = useState({ name: '', phone: '', address: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [phoneError, setPhoneError] = useState(null)

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handlePhoneChange = (phoneBody) => {
    setForm((prev) => ({ ...prev, phone: phoneBody }))
    if (phoneError) setPhoneError(null)
  }

  const handlePhoneBlur = () => {
    if (form.phone.length === 0) {
      setPhoneError(null)
      return
    }
    if (!validateAndNormalizePhone(form.phone)) {
      setPhoneError(t('phone_invalid', lang))
    } else {
      setPhoneError(null)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.phone.trim()) {
      setError(t('name_phone_required', lang))
      return
    }
    const normalized = validateAndNormalizePhone(form.phone)
    if (!normalized) {
      setPhoneError(t('phone_invalid', lang))
      return
    }
    setLoading(true)
    setError(null)
    try {
      // Вход/регистрация по телефону (tg_id опционален — бэкенд создаст или найдёт клиента)
      const result = await clientApi.loginByPhone({ name: form.name, phone: normalized, address: form.address })
      const profile = { id: result.client_id, name: result.name, phone: normalized, registered: true }
      if (onRegistered) onRegistered(profile)
      if (onLogin) onLogin(profile)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3 text-blue-600"><ICONS.logo size={48} /></div>
          <h1 className="text-2xl font-bold text-gray-900">{t('app_title', lang)}</h1>
          <p className="text-gray-500 mt-1">{t('app_subtitle', lang)}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">{t('register_title', lang)}</h2>
          <p className="text-sm text-gray-500 mb-4">
            {t('register_hint', lang)}
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('your_name', lang)}
              </label>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder={t('name_placeholder', lang)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('phone', lang)} *
              </label>
              <PhoneInput
                phone={form.phone}
                onChange={handlePhoneChange}
                onBlur={handlePhoneBlur}
                error={phoneError}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('delivery_address', lang)}
              </label>
              <input
                type="text"
                name="address"
                value={form.address}
                onChange={handleChange}
                placeholder={t('address_placeholder', lang)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? t('registering', lang) : t('register_btn', lang)}
            </button>
          </form>

          {effectiveTgId && (
            <p className="mt-3 text-xs text-center text-gray-400">
              Telegram ID: {effectiveTgId}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
