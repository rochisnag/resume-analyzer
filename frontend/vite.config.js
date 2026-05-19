import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/analyze': apiProxyTarget,
      '/auth': apiProxyTarget,
      '/health': apiProxyTarget,
      '/statistics': apiProxyTarget,
      '/job-roles': apiProxyTarget,
      '/admin': apiProxyTarget,
      '/mail': apiProxyTarget,
    }
  }
})
