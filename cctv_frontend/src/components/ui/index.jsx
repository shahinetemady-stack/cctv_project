import { useState } from 'react'
import { formatDate } from '../../utils/date'

// ─── PasswordInput (فیلد رمز با دکمه چشم نمایش/پنهان) ─────────────────────────
export function PasswordInput({ className = '', style, ...props }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        className={className}
        style={{ paddingLeft: '2.75rem', ...style }}
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        {...props}
      />
      <button
        type="button"
        onClick={() => setShow(s => !s)}
        aria-label={show ? 'پنهان کردن رمز عبور' : 'نمایش رمز عبور'}
        title={show ? 'پنهان کردن رمز عبور' : 'نمایش رمز عبور'}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-steel hover:text-white transition-colors"
      >
        {show ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>
    </div>
  )
}

// ─── Spinner ──────────────────────────────────────────────────────────────────
export function Spinner({ size = 'md', className = '' }) {
  const s = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[size]
  return (
    <div className={`${s} ${className} relative`}>
      <div className="absolute inset-0 rounded-full border-2 border-brand/20" />
      <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-brand animate-spin" />
    </div>
  )
}

// ─── PageLoader ───────────────────────────────────────────────────────────────
export function PageLoader() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
      <Spinner size="lg" />
      <p className="text-gray-steel text-sm animate-pulse">در حال بارگذاری...</p>
    </div>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
export function EmptyState({ icon = '📭', title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
      <div className="text-5xl">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">{title}</h3>
      {description && <p className="text-sm text-gray-steel max-w-xs">{description}</p>}
      {action}
    </div>
  )
}

// ─── UserStamp — نمایش ثبت‌کننده و آخرین ویرایش‌کننده سند ─────────────────────
export function UserStamp({ createdBy, updatedBy, createdAt, updatedAt, inline = false }) {
  if (!createdBy && !updatedBy) return <span className="text-gray-steel">—</span>
  return (
    <div className={inline ? 'inline-flex gap-2' : 'space-y-0.5'} style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
      {createdBy && (
        <div title={createdAt || ''}>
          📝 {createdBy}
          {!inline && createdAt && (
            <div className="text-[10px] text-gray-steel">{formatDate(createdAt, { withTime: true })}</div>
          )}
        </div>
      )}
      {updatedBy && updatedBy !== createdBy && <div title={updatedAt || ''}>✏️ {updatedBy}</div>}
    </div>
  )
}

// ─── ErrorMessage ─────────────────────────────────────────────────────────────
export function ErrorMessage({ message = 'خطایی رخ داد', retry }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <div className="w-12 h-12 rounded-full bg-alert-red/10 flex items-center justify-center">
        <svg className="w-6 h-6 text-alert-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        </svg>
      </div>
      <p className="text-sm text-alert-red">{message}</p>
      {retry && (
        <button onClick={retry} className="btn-secondary text-xs">
          تلاش مجدد
        </button>
      )}
    </div>
  )
}

