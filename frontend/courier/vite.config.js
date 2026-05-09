import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // base — путь где будет лежать собранное приложение
  // если раздаёт Django по /static/miniapp/courier/ то:
  base: '/static/miniapp/courier/',
  build: {
    outDir: '../../static/miniapp/courier',  // сборка прямо в Django static
    emptyOutDir: true,
  }
})