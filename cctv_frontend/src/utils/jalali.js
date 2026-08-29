// تبدیل تاریخ میلادی ↔ جلالی — پوشش ساده روی پکیج jalaali-js
import { toJalaali, toGregorian, isLeapJalaaliYear } from 'jalaali-js'

export function gregorianToJalali(gy, gm, gd) {
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  return [jy, jm, jd]
}

export function jalaliToGregorian(jy, jm, jd) {
  const { gy, gm, gd } = toGregorian(jy, jm, jd)
  return [gy, gm, gd]
}

// تعداد روزهای هر ماه جلالی — شش ماه اول ۳۱، تا بهمن ۳۰، اسفند ۲۹ (سال کبیسه ۳۰)
export function jalaliMonthDays(jy, jm) {
  if (jm >= 1 && jm <= 6) return 31
  if (jm >= 7 && jm <= 11) return 30
  if (jm === 12) return isLeapJalaaliYear(jy) ? 30 : 29
  return 0
}

export const JALALI_MONTHS = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

// متن خوانای تاریخ شمسی از ISO میلادی — مثل «۱۵ شهریور ۱۴۰۵»
export function jalaliText(iso) {
  if (!iso) return ''
  const [gy, gm, gd] = iso.split('-').map(Number)
  if (!gy) return ''
  const [jy, jm, jd] = gregorianToJalali(gy, gm, gd)
  return `${jd.toLocaleString('fa-IR')} ${JALALI_MONTHS[jm - 1]} ${jy.toLocaleString('fa-IR')}`
}

// تعطیلات رسمی خورشیدی ثابت (ماه-روز) — تعطیلات قمری (محرم، رمضان، عید فطر/قربان...) پوشش داده نمی‌شوند
const FIXED_HOLIDAYS = new Set([
  '01-01', '01-02', '01-03', '01-04',           // نوروز
  '01-12',                                      // روز جمهوری اسلامی
  '01-13',                                      // سیزده‌بدر
  '03-14',                                      // رحلت امام خمینی
  '03-15',                                      // قیام ۱۵ خرداد
  '11-22',                                      // پیروزی انقلاب
  '12-29',                                      // ملی شدن صنعت نفت
])

// برمی‌گرداند علت تعطیلی یا null — جمعه‌ها + تعطیلات رسمی خورشیدی
export function jalaliHolidayInfo(iso) {
  if (!iso) return null
  const [gy, gm, gd] = iso.split('-').map(Number)
  if (!gy) return null
  const [jy, jm, jd] = gregorianToJalali(gy, gm, gd)
  const key = `${String(jm).padStart(2, '0')}-${String(jd).padStart(2, '0')}`
  if (FIXED_HOLIDAYS.has(key)) return 'تعطیل رسمی'
  if (new Date(gy, gm - 1, gd).getDay() === 5) return 'جمعه'
  return null
}
