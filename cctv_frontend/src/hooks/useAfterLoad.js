import { useEffect, useState } from 'react'

// true بعد از load کامل صفحه یا حداکثر ۴ ثانیه بعد از mount (هر کدام زودتر) —
// برای به‌تاخیر انداختن کار غیربحرانی (فچ دیتای زیر اسکرول، انیمیشن‌های زنده)
// تا بیرون از پنجره‌ی بوت اولیه (FCP→TTI) بماند
export function useAfterLoad(maxDelayMs = 4000) {
  const [ready, setReady] = useState(() => document.readyState === 'complete')
  useEffect(() => {
    if (ready) return
    const on = () => { clearTimeout(t); setReady(true) }
    const t = setTimeout(() => setReady(true), maxDelayMs)
    window.addEventListener('load', on, { once: true })
    return () => { clearTimeout(t); window.removeEventListener('load', on) }
  }, [ready, maxDelayMs])
  return ready
}
