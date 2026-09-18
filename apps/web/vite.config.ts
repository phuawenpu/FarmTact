import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', emptyOutDir: true },
  // Development UI and API use different loopback ports. Preserve the API's
  // same-origin mutation boundary at the proxy rather than weakening it in the
  // application server.
  server: { proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, headers: { origin: 'http://127.0.0.1:8000' } } } },
})
