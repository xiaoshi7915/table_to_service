import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',  // 允许外部访问
    port: 3003,
    proxy: {
      '/api': {
        target: 'http://localhost:8300',
        changeOrigin: true
      }
    }
  }
})


