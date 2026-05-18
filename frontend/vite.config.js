import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/statistics': 'http://localhost:8000',
      '/job-roles': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/mail': 'http://localhost:8000',
    }
  }
})
