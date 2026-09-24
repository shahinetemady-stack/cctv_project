// ─── Media URL helper ────────────────────────────────────────────────────────
// بک‌اند URLهای تصویر را به صورت relative (مثل /media/...) یا absolute برمی‌گرداند.
// این helper آن‌ها را به URL امن (same-origin / https) تبدیل می‌کند تا
// mixed content قفل سبز مرورگر را نشکند.
// پیش‌فرض same-origin است: در dev پروکسی Vite مسیر /media را به بک‌اند می‌رساند
// و در production هم‌دامنه سرو می‌شود. در صورت نیاز VITE_MEDIA_BASE را تنظیم کنید.

const MEDIA_BASE =
  import.meta.env.VITE_MEDIA_BASE ||
  ''

/**
 * تبدیل URL تصویر relative به absolute
 * @param {string|null|undefined} url
 * @returns {string|null}
 */
export function mediaUrl(url) {
  if (!url) return null
  if (typeof url !== 'string') return null
  // اگر absolute است: فقط دامنه production را به https ارتقا بده تا mixed content
  // پیش نیاید — localhost/127.0.0.1 (dev server بدون SSL) دست‌نخورده می‌ماند
  if (/^https?:\/\//i.test(url)) {
    return url.replace(/^http:\/\/(www\.)?doorbinkar\.com(?=[/:]|$)/i, 'https://doorbinkar.com')
  }
  // اگر با // شروع می‌شود (protocol-relative)
  if (url.startsWith('//')) return `https:${url}`
  // در غیر این صورت prepend کن
  const base = MEDIA_BASE.replace(/\/+$/, '')
  const path = url.startsWith('/') ? url : `/${url}`
  return `${base}${path}`
}
