import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HelmetProvider } from 'react-helmet-async'
import { Toaster } from 'sonner'
import App from './App'
import useThemeStore, { applyTheme } from './store/useThemeStore'
import './index.css'

// اعمال تم ذخیره‌شده قبل از رندر — پارامتر ?theme=light|dark برای تست/پیش‌نمایش
const urlTheme = new URLSearchParams(location.search).get('theme')
if (urlTheme === 'light' || urlTheme === 'dark') useThemeStore.getState().setTheme(urlTheme)
applyTheme(useThemeStore.getState().theme)

// غیرفعال کردن تغییر مقدار input[type=number] با اسکرول موس (در کل سایت)
document.addEventListener('wheel', (e) => {
  if (e.target instanceof HTMLInputElement && e.target.type === 'number') e.target.blur()
}, { passive: true })

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,   // 5 دقیقه
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HelmetProvider>
        <BrowserRouter>
          <App />
          <Toaster theme="dark" position="bottom-center" toastOptions={{ style: { fontFamily: 'inherit' } }} />
        </BrowserRouter>
      </HelmetProvider>
    </QueryClientProvider>
  </React.StrictMode>
)

// ─── Service Worker (PWA) — فقط در production ────────────────
if ('serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').then(
        (reg) => console.log('SW registered:', reg.scope),
        (err) => console.warn('SW registration failed:', err)
      )
    })
  } else {
    // حالت توسعه: SW و کش‌های قدیمی را پاک کن تا همیشه نسخه تازه دیده شود
    navigator.serviceWorker.getRegistrations().then((regs) => {
      regs.forEach((r) => r.unregister())
    })
    if ('caches' in window) {
      caches.keys().then((keys) => keys.forEach((k) => caches.delete(k)))
    }
  }
}
