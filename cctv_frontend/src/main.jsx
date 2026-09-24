import React, { lazy, Suspense, useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HelmetProvider } from 'react-helmet-async'
import App from './App'
import useThemeStore, { applyTheme } from './store/useThemeStore'
import './index.css'

// Toaster (sonner) برای لود اولیه بحرانی نیست — چانک جدا و mount بعد از idle
const Toaster = lazy(() => import('sonner').then(m => ({ default: m.Toaster })))
function LazyToaster() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const ric = window.requestIdleCallback || ((cb) => setTimeout(cb, 1500))
    const id = ric(() => setReady(true), { timeout: 3000 })
    return () => { if (window.cancelIdleCallback) cancelIdleCallback(id) }
  }, [])
  if (!ready) return null
  return (
    <Suspense fallback={null}>
      <Toaster theme="dark" position="bottom-center" toastOptions={{ style: { fontFamily: 'inherit' } }} />
    </Suspense>
  )
}

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

const boot = () => {
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HelmetProvider>
        <BrowserRouter>
          <App />
          <LazyToaster />
        </BrowserRouter>
      </HelmetProvider>
    </QueryClientProvider>
  </React.StrictMode>
)
requestAnimationFrame(() => requestAnimationFrame(() => {
  document.getElementById('static-home')?.remove()
}))
}

// اسپلش استاتیک هیرو (index.html) — بلوک fixed تمام‌صفحه است. CSS اصلی async لود
// می‌شود؛ اگر React قبل از رسیدن آن مونت شود، محتوای بدون‌استایل زیر اسپلش قرار
// می‌گیرد و اعمال stylesheet کل سند را جابه‌جا می‌کند — Chrome این جابه‌جایی را حتی
// زیر پوشش اسپلش هم CLS حساب می‌کند (در PSI موبایل CLS≈1.2). پس مونت تا آماده‌شدن
// CSS عقب می‌افتد: محتوا مستقیم با استایل نهایی ساخته می‌شود (insertion ≠ shift)
// و اسپلش بعد از دو فریم حذف می‌شود. سقف ۴ ثانیه تا هیچ‌وقت گیر نکند.
const cssLink = document.querySelector('link[as="style"]')
if (!cssLink || cssLink.rel === 'stylesheet') {
  boot()
} else {
  cssLink.addEventListener('load', boot, { once: true })
  setTimeout(boot, 3000)  // سقف اطمینان — تعامل‌پذیری صفحه هرگز بیش از ۳ ثانیه عقب نمی‌افتد
}

// ─── Service Worker (PWA) — فقط در production ────────────────
if ('serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      // ?v=11 → URL متفاوت از sw.js قدیمی؛ تضمین می‌کند حتی با کش CDN/مرورگر هم
      // نسخه تازه fetch شود (بررسی آپدیت SW از کش HTTP مرورگر تبعیت می‌کند)
      navigator.serviceWorker.register('/sw.js?v=11').then(
        (reg) => {
          console.log('SW registered:', reg.scope)
          // اگر نسخه تازه در راه بود، اجبار به فعال‌سازی فوری (بدون بستن تب‌ها)
          reg.update()
          if (reg.waiting) reg.waiting.postMessage('SKIP_WAITING')
        },
        (err) => console.warn('SW registration failed:', err)
      )
      navigator.serviceWorker.addEventListener('message', (e) => {
        if (e.data === 'SW_ACTIVATED') window.location.reload()
      })
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
