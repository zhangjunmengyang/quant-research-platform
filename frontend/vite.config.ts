import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// API 地址配置
const API_HOST = process.env.VITE_API_HOST || '127.0.0.1'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // 预览服务器配置（生产模式）
  preview: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: `http://${API_HOST}:8000`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://${API_HOST}:8000`,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
