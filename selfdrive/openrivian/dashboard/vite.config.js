import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/offer': {
        target: 'http://192.168.0.233:8081',
        changeOrigin: true
      },
      '/routes': {
        target: 'http://192.168.0.233:8081',
        changeOrigin: true
      }
    }
  }
})
