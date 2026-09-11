import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Версия сборки — уникальна для каждого npm run build.
// Вшивается в URL целевых Mini App (см. App.jsx: __BUILD_VER__),
// чтобы при каждом деплое Telegram/WebView сбрасывал кэш и открывал актуальное.
const buildVersion = String(Date.now())

export default defineConfig({
  plugins: [react()],
  // Глобальная константа для всего кода launcher (Vite подставляет её на этапе сборки).
  define: {
    __BUILD_VER__: JSON.stringify(buildVersion),
  },
  build: {
    outDir: '../../static/miniapp/launcher',
    emptyOutDir: true,
  },
})