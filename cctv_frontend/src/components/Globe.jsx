import { useEffect, useRef } from 'react'

// مسیرهای تجاری چین → تهران (روی کره به‌صورت قوس گریت‌سیرکل با سر متحرک)
const ROUTES = [
  { from: 'Shenzhen', to: 'Tehran' },
  { from: 'Shanghai', to: 'Tehran' },
  { from: 'Guangzhou', to: 'Tehran' },
  { from: 'Hong Kong', to: 'Tehran' },
  { from: 'Beijing', to: 'Tehran' },
]

const HUBS = [
  { city: 'Tehran', v: 90 },
  { city: 'Shanghai', v: 96 }, { city: 'Shenzhen', v: 88 }, { city: 'Beijing', v: 74 },
  { city: 'Guangzhou', v: 66 }, { city: 'Hong Kong', v: 58 },
]

/**
 * Globe — کره زمین سه‌بعدی (three.js + شیدرهای سفارشی، بدون تکسچر)
 * بدون هیچ متن روی تصویر؛ فقط خود کره. رنگ‌ها از توکن‌های --globe-* تم
 * خوانده می‌شوند و با تعویض تم بدون ساخت دوباره به‌روز می‌شوند.
 * ماژول سه‌بعدی با dynamic import لود می‌شود تا روی باندل اصلی اثر نگذارد.
 */
export default function Globe({ size = 300 }) {
  const hostRef = useRef(null)

  useEffect(() => {
    let api = null, cancelled = false
    const obs = new MutationObserver(() => api?.retheme())
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    import('../lib/globe.js').then(({ globe }) => {
      if (cancelled || !hostRef.current) return
      globe(hostRef.current, { routes: ROUTES, markers: HUBS, spin: 0.045 })
        .then((g) => { api = g; if (!cancelled) g.focus('Tehran') })
    })
    return () => { cancelled = true; obs.disconnect(); api?.destroy() }
  }, [])

  return (
    <div
      ref={hostRef}
      aria-hidden="true"
      style={{ position: 'relative', width: '100%', maxWidth: size, aspectRatio: '1/1', margin: '0 auto' }}
    />
  )
}
