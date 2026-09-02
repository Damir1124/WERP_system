import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/miniapp/operator/',
  build: {
    outDir: '../../static/miniapp/operator',
    emptyOutDir: true,
  },
})