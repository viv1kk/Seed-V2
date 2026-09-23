import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // The dashboard chunk is ECharts, tree-shaken to the three marks the
    // descriptors use, and it is loaded only when a dashboard opens. It is
    // served from this machine, never over a network (NFR-D2), so its
    // size has no effect worth a warning.
    chunkSizeWarningLimit: 700,
  },
  server: {
    proxy: {
      // Same origin in the browser, so the event stream needs no CORS
      // configuration and no absolute URLs in the client.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
