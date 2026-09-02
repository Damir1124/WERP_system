import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/miniapp/client/',
  build: {
    outDir: '../../static/miniapp/client',
    emptyOutDir: true,
  },
  server: {
    port: 5174,
  }
})
