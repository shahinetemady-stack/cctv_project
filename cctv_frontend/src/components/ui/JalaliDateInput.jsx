// ورودی تاریخ شمسی — تایپ مستقیم (مثل ۱۴۰۴/۰۵/۲۴ یا 14040524) + سه سلکت روز/ماه/سال
// مقدار به صورت ISO میلادی (YYYY-MM-DD) پاس می‌شود
import { useState, useEffect } from 'react'
import { gregorianToJalali, jalaliToGregorian, jalaliMonthDays, JALALI_MONTHS } from '../../utils/jalali'
import { todayTehranParts } from '../../utils/date'

// سال جلالی جاری — پیش‌فرض برای وقتی کاربر هنوز سالی انتخاب نکرده (به وقت ایران)
const CURRENT_JY = gregorianToJalali(...todayTehranParts())[0]

const toEn = (s) => String(s || '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))

// پارس متن شمسی → ISO میلادی؛ نامعتبر → null
function parseJalaliText(t) {
  const en = toEn(t).trim().replace(/[-.]/g, '/')
  let y, m, d
  if (/^\d{8}$/.test(en)) {
    y = +en.slice(0, 4); m = +en.slice(4, 6); d = +en.slice(6, 8)
  } else {
    const parts = en.split('/')
    if (parts.length !== 3) return null
    ;[y, m, d] = parts.map(Number)
  }
  if (!(y >= 1300 && y <= 1500 && m >= 1 && m <= 12)) return null
  // روز باید در بازه واقعی همان ماه باشد (اسفند ۲۹/۳۰، بهمن و قبلش ۳۰، ...)
  if (!(d >= 1 && d <= jalaliMonthDays(y, m))) return null
  const [gy, gm, gd] = jalaliToGregorian(y, m, d)
  return `${gy}-${String(gm).padStart(2, '0')}-${String(gd).padStart(2, '0')}`
}

export default function JalaliDateInput({ value, onChange, className = 'input text-sm' }) {
  const [jy, setJy] = useState('')
  const [jm, setJm] = useState('')
  const [jd, setJd] = useState('')
  const [text, setText] = useState('')
  const [badText, setBadText] = useState(false)

  // سینک از مقدار بیرونی (ISO میلادی) به state داخلی شمسی
  useEffect(() => {
    if (!value) { setJy(''); setJm(''); setJd(''); setText(''); setBadText(false); return }
    const [gy, gm, gd] = value.split('-').map(Number)
    if (!gy) return
    const [y, m, d] = gregorianToJalali(gy, gm, gd)
    setJy(String(y)); setJm(String(m)); setJd(String(d))
    // متن تایپ‌شده را فقط وقتی بازنویسی کن که تاریخ دیگری را نشان می‌دهد (وسط تایپ دست نمی‌خورد)
    if (parseJalaliText(text) !== value) {
      setText(`${y}/${String(m).padStart(2, '0')}/${String(d).padStart(2, '0')}`)
      setBadText(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  // وقتی هر سه انتخاب شدند، میلادی بیرون بده
  useEffect(() => {
    if (!jy || !jm || !jd) return
    const [gy, gm, gd] = jalaliToGregorian(Number(jy), Number(jm), Number(jd))
    const iso = `${gy}-${String(gm).padStart(2, '0')}-${String(gd).padStart(2, '0')}`
    if (iso !== value) onChange(iso)
  }, [jy, jm, jd])

  function onTextChange(e) {
    // جداکننده‌ها خودکار گذاشته می‌شوند — کاربر فقط عدد تایپ می‌کند (۱۴۰۵۰۶۱۰ → ۱۴۰۵/۰۶/۱۰)
    const digits = toEn(e.target.value).replace(/\D/g, '').slice(0, 8)
    let v = digits
    if (digits.length > 6) v = `${digits.slice(0, 4)}/${digits.slice(4, 6)}/${digits.slice(6)}`
    else if (digits.length > 4) v = `${digits.slice(0, 4)}/${digits.slice(4)}`
    setText(v)
    if (!digits) { setBadText(false); if (value) onChange(''); return }
    const iso = parseJalaliText(v)
    if (iso) {
      setBadText(false)
      if (iso !== value) onChange(iso)
    } else {
      // فقط وقتی ورودی به اندازه کافی کامل شده خطا نشان بده
      setBadText(digits.length >= 7)
    }
  }

  // روزهای قابل انتخاب به ماه (و برای اسفند، به سال) بستگی دارد
  const maxDay = jm ? jalaliMonthDays(Number(jy) || CURRENT_JY, Number(jm)) : 31
  const days = Array.from({ length: maxDay }, (_, i) => i + 1)
  const years = Array.from({ length: 12 }, (_, i) => 1400 + i)

  // اگر با تعویض ماه/سال، روز انتخاب‌شده از سقف ماه گذشت، روز ریست می‌شود
  useEffect(() => {
    if (jd && jm && Number(jd) > maxDay) setJd('')
  }, [jm, jy])

  return (
    <div className="space-y-2" dir="rtl">
      <input
        type="text"
        inputMode="numeric"
        dir="ltr"
        value={text}
        onChange={onTextChange}
        placeholder="۱۴۰۴/۰۵/۲۴"
        className={`${className} text-center tracking-wider ${badText ? 'border-red-500/60' : ''}`}
      />
      <div className="grid grid-cols-3 gap-2">
        <select value={jd} onChange={e => setJd(e.target.value)} className={className}>
          <option value="">روز</option>
          {days.map(d => <option key={d} value={d}>{d.toLocaleString('fa-IR')}</option>)}
        </select>
        <select value={jm} onChange={e => setJm(e.target.value)} className={className}>
          <option value="">ماه</option>
          {JALALI_MONTHS.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
        </select>
        <select value={jy} onChange={e => setJy(e.target.value)} className={className}>
          <option value="">سال</option>
          {years.map(y => <option key={y} value={y}>{y.toLocaleString('fa-IR')}</option>)}
        </select>
      </div>
    </div>
  )
}
