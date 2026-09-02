import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/miniapp/owner/',
  build: {
    outDir: '../../static/miniapp/owner',
    emptyOutDir: true,
  },
})