// ─── Media URL helper ────────────────────────────────────────────────────────
// بک‌اند URLهای تصویر را به صورت relative (مثل /media/...) برمی‌گرداند.
// این helper آن‌ها را به URL کامل تبدیل می‌کند تا در <img src> درست load شوند.
// در محیط production می‌توان VITE_MEDIA_BASE را تنظیم کرد.

const MEDIA_BASE =
  import.meta.env.VITE_MEDIA_BASE ||
  'http://localhost:8000'

/**
 * تبدیل URL تصویر relative به absolute
 * @param {string|null|undefined} url
 * @returns {string|null}
 */
export function mediaUrl(url) {
  if (!url) return null
  if (typeof url !== 'string') return null
  // اگر قبلاً absolute است (http/https) همان برگردان
  if (/^https?:\/\//i.test(url)) return url
  // اگر با // شروع می‌شود (protocol-relative)
  if (url.startsWith('//')) return `https:${url}`
  // در غیر این صورت prepend کن
  const base = MEDIA_BASE.replace(/\/+$/, '')
  const path = url.startsWith('/') ? url : `/${url}`
  return `${base}${path}`
}
