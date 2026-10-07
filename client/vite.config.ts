import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Same-origin /api keeps the session cookie first-party during development.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
