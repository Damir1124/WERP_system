import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/miniapp/launcher/',
  build: {
    outDir: '../../static/miniapp/launcher',
    emptyOutDir: true,
  },
})