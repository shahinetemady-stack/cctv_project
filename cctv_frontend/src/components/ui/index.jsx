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

// ─── Modal ────────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative card w-full max-w-md max-h-[90vh] overflow-y-auto animate-slide-up">
        <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-white/5">
          <h2 className="font-bold text-lg">{title}</h2>
          <button onClick={onClose} className="btn-ghost p-1 rounded-lg">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

// ─── Toast ────────────────────────────────────────────────────────────────────
let _setToasts
export function ToastContainer() {
  const [toasts, setToasts] = [[], () => {}]
  _setToasts = setToasts
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-4 left-4 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div key={t.id}
          className={`px-4 py-3 rounded-xl shadow-lg text-sm font-medium animate-slide-up
            ${t.type === 'success' ? 'bg-alert-green text-white' : ''}
            ${t.type === 'error' ? 'bg-alert-red text-white' : ''}
            ${t.type === 'info' ? 'bg-brand text-white' : ''}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}

// سیستم toast ساده — از React state خارج
let toastId = 0
export const toast = {
  success: (msg) => _showToast(msg, 'success'),
  error:   (msg) => _showToast(msg, 'error'),
  info:    (msg) => _showToast(msg, 'info'),
}
function _showToast(message, type) {
  if (!_setToasts) { console.log(`[${type}] ${message}`); return }
  const id = ++toastId
  _setToasts(prev => [...prev, { id, message, type }])
  setTimeout(() => _setToasts(prev => prev.filter(t => t.id !== id)), 3000)
}
