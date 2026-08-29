import { Component } from 'react'

/**
 * ErrorBoundary — جلوگیری از سفید شدن کل سایت هنگام خطای یک کامپوننت
 * (مثل خطای لود chunk یا crash یک کامپوننت سنگین)
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info)
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
          <p className="text-sm mb-6" style={{ color: 'var(--color-text-secondary)' }}>
            مشکلی در نمایش این بخش پیش آمد.
          </p>
          <button className="btn-gold" onClick={() => window.location.reload()}>
            تلاش مجدد
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
