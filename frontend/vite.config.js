import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',  // 允许外部访问
    port: 3003,
    hmr: {
      // 通过nginx代理时，HMR应该使用当前页面的协议和主机
      // 当通过HTTPS访问时，HMR会自动使用WSS协议并通过nginx代理
      // 设置host为当前域名，让HMR通过nginx代理而不是直接连接3003端口
      host: 'wenshu.chenxiaoshivivid.top',
      // 不指定clientPort，让Vite根据当前页面的协议自动选择（HTTP使用3003，HTTPS使用443）
      // 当通过HTTPS访问时，HMR会通过nginx代理，不会直接连接3003端口
    },
    // 允许的域名列表（用于通过nginx反向代理访问）
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'wenshu.chenxiaoshivivid.top',
      '121.36.205.70'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8300',
        changeOrigin: true
      }
    }
  },
  build: {
    // 代码分割配置
    rollupOptions: {
      output: {
        // 手动分包策略
        manualChunks: {
          // 将Vue相关库单独打包
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // 将Element Plus单独打包
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          // 将ECharts单独打包（图表库较大）
          'echarts': ['echarts'],
          // 将axios单独打包
          'axios': ['axios']
        },
        // 优化chunk命名
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    },
    // 启用压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,  // 生产环境移除console
        drop_debugger: true
      }
    },
    // 启用CSS代码分割
    cssCodeSplit: true,
    // 设置chunk大小警告限制
    chunkSizeWarningLimit: 1000
  },
  // 优化依赖预构建
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'element-plus', 'axios']
  }
})


