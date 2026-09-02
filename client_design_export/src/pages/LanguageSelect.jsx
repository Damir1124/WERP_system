import { LANGUAGES, t } from '../i18n.js'
import { ICONS, FLAG_ICONS } from '../icons/water-icons.jsx'

/**
 * Экран выбора языка (как в боте: 🇷🇺 / 🇺🇿 / 🇬🇧).
 * @param {Object} props
 * @param {Function} props.onSelect - Callback с выбранным языком (ru/uz/en)
 */
export default function LanguageSelect({ onSelect }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3 text-blue-600"><ICONS.logo size={48} /></div>
          <h1 className="text-2xl font-bold text-gray-900">{t('app_title', 'ru')}</h1>
          <p className="text-gray-500 mt-1">{t('app_subtitle', 'ru')}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {t('choose_language', 'ru')}
          </h2>

          <div className="space-y-3">
            {Object.entries(LANGUAGES).map(([code, label]) => {
              const Flag = FLAG_ICONS[code]
              return (
                <button
                  key={code}
                  onClick={() => onSelect(code)}
                  className="w-full py-3.5 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                >
                  {Flag && <Flag size={18} />}
                  {label}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}