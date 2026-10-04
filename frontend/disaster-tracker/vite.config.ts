import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000',
      '/static': process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000',
    },
  },
})
