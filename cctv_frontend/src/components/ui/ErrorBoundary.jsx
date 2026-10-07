import { Component } from 'react'

/**
 * ErrorBoundary — جلوگیری از سفید شدن کل سایت هنگام خطای یک کامپوننت
 * (مثل خطای لود chunk یا crash یک کامپوننت سنگین)
 */

// خطای لود چانک: بعد از هر دیپلوی، فایل‌های هش‌دار قدیمی از سرور حذف می‌شوند و
// تبِ بازِ کاربر با index.html قبلی دنبال چانک‌های حذف‌شده می‌گردد — رفرش یک‌باره
// (با بازهٔ امن ۶۰ ثانیه‌ای تا حلقهٔ رفرش پیش نیاید) مشکل را بی‌صدا حل می‌کند.
function isChunkLoadError(error) {
  const msg = String(error?.message || error || '')
  return msg.includes('dynamically imported module')
    || msg.includes('Importing a module script failed')
    || msg.includes('error loading dynamically imported module')
}

function reloadOnce() {
  try {
    const last = Number(sessionStorage.getItem('chunk_reload_at') || 0)
    if (Date.now() - last < 60_000) return
    sessionStorage.setItem('chunk_reload_at', String(Date.now()))
  } catch { /* sessionStorage در دسترس نیست */ }
  window.location.reload()
}

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: String(error?.message || '') }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info)
    if (isChunkLoadError(error)) reloadOnce()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined) return this.props.fallback
      return (
        <div className="container-site py-20 text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="font-bold text-lg mb-2" style={{ color: 'var(--color-text-primary)' }}>
            خطایی رخ داد
          </h2>
          <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
            مشکلی در نمایش این بخش پیش آمد.
          </p>
          {this.state.message && (
            <p className="text-[11px] mb-6 opacity-60" dir="ltr" style={{ color: 'var(--color-text-secondary)' }}>
              {this.state.message}
            </p>
          )}
          <button className="btn-gold" onClick={() => window.location.reload()}>
            تلاش مجدد
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
