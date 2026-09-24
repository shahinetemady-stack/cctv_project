import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { transformSync } from 'esbuild'

// Critical CSS محتوای پر‌رندر استاتیک (هیرو/مارکی/معرفی) — این‌لاین در head تا
// اولین نقاشی منتظر stylesheet اصلی نماند؛ stylesheet کامل async لود می‌شود
function inlineCriticalCss() {
  const critical = transformSync(readFileSync('src/critical.css', 'utf8'), {
    loader: 'css',
    minify: true,
  }).code
  return {
    name: 'inline-critical-css',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        html = html.replace(
          /<link rel="stylesheet"([^>]*)>/g,
          '<link rel="preload" as="style"$1 onload="this.onload=null;this.rel=\'stylesheet\'"><noscript><link rel="stylesheet"$1></noscript>'
        )
        return html.replace('</head>', `<style data-critical>${critical}</style></head>`)
      },
    },
  }
}

export default defineConfig({
  plugins: [react(), inlineCriticalCss()],
  build: {
    rollupOptions: {
      output: {
        // جدا کردن وندورها از باندل اصلی — کاهش JS اولیه و کش بهتر
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-libs': ['@tanstack/react-query', 'axios', 'zustand'],
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // همان پراکسی برای `vite preview` — تا تست Lighthouse محلی روی بیلد نهایی ممکن شود
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
