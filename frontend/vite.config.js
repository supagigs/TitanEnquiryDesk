import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/assets/titan_desk/frontend/',
  build: { outDir: '../titan_desk/public/frontend', emptyOutDir: true, target: 'es2020' },
  server: { port: 8080, proxy: { '^/(app|api|assets|files|login)': 'http://127.0.0.1:8000' } },
})
