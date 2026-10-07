// ─── فرمت تاریخ شمسی (Jalali) برای نمایش در کل سایت ───────────────
// مبتنی بر Intl با locale «fa-IR» — بدون وابستگی خارجی
// خروجی پیش‌فرض: ۱۴۰۵/۰۴/۲۸
// مبنای تاریخ/ساعت همیشه زمان رسمی ایران است (نه ساعت دستگاه کاربر)

export const TEHRAN_TZ = 'Asia/Tehran'

/**
 * تاریخ امروز به وقت ایران به فرمت YYYY-MM-DD (میلادی) — برای پیش‌فرض فرم‌ها
 */
export function todayTehran() {
  return new Date().toLocaleDateString('en-CA', { timeZone: TEHRAN_TZ })
}

/** [سال، ماه، روز] میلادیِ امروز به وقت ایران — برای تبدیل به شمسی */
export function todayTehranParts() {
  return todayTehran().split('-').map(Number)
}

/** تاریخ n روز قبل به وقت ایران، به فرمت YYYY-MM-DD */
export function daysAgoTehran(n) {
  const [y, m, d] = todayTehranParts()
  return new Date(Date.UTC(y, m - 1, d - n)).toISOString().split('T')[0]
}

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
    return d.toLocaleDateString('fa-IR', { timeZone: TEHRAN_TZ, month: '2-digit', day: '2-digit' })
  }
  if (withTime) {
    return d.toLocaleString('fa-IR', {
      timeZone: TEHRAN_TZ,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  }
  return d.toLocaleDateString('fa-IR', { timeZone: TEHRAN_TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
}
