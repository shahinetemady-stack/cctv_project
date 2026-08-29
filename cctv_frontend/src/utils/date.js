// ─── فرمت تاریخ شمسی (Jalali) برای نمایش در کل سایت ───────────────
// مبتنی بر Intl با locale «fa-IR» — بدون وابستگی خارجی
// خروجی پیش‌فرض: ۱۴۰۵/۰۴/۲۸

/**
 * تبدیل مقدار تاریخ (رشته ISO، Date، timestamp) به متن شمسی
 * @param {string|Date|number|null|undefined} value
 * @param {{ short?: boolean, withTime?: boolean }} opts
 *   short: فقط ماه/روز — ۰۴/۲۸
 *   withTime: همراه ساعت — ۱۴۰۵/۰۴/۲۸ ۱۴:۳۰
 * @returns {string} متن شمسی یا «—» برای مقدار خالی
 */
export function formatDate(value, { short = false, withTime = false } = {}) {
  if (!value) return '—'
  const d = value instanceof Date ? value : new Date(value)
  if (isNaN(d.getTime())) return String(value)

  if (short) {
    return d.toLocaleDateString('fa-IR', { month: '2-digit', day: '2-digit' })
  }
  if (withTime) {
    return d.toLocaleString('fa-IR', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  }
  return d.toLocaleDateString('fa-IR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
