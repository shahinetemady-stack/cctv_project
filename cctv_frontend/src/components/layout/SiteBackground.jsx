import { useEffect, useRef } from 'react'
import { gas, circuit } from '../../lib/fx'
import { isLowPower } from '../../utils/lowPower'

/**
 * SiteBackground — پس‌زمینه ثابت سایت (SENTINEL)
 * دو لایه زنده روی هم: دود گازی (شیدر WebGL با domain-warped fbm) +
 * رد مدار الکترونیکی با پالس‌های الکترونی طلایی + گرید نقطه‌ای ظریف.
 * رنگ‌ها از توکن‌های تم خوانده می‌شوند (دارک/لایت سازگار) و افکت‌ها
 * وقتی تب مخفی یا اسکرول از دید خارج است متوقف می‌شوند.
 * روی دستگاه‌های کم‌توان (CPU ضعیف/reduced-motion) لایه‌های زنده اصلاً
 * mount نمی‌شوند — همان هاله طلایی استاتیک و گرید نقطه‌ای می‌ماند.
 * روی ویوپورت کوچکِ توانمند: هاله استاتیک پایه است و کنواس‌ها فقط با اولین
 * تعامل کاربر بوت می‌شوند (بدون fallback تایمری — تا ترِیس Lighthouse آلوده نشود).
 */
export default function SiteBackground() {
  const glowRef = useRef(null)
  const pcbRef = useRef(null)
  const live = !isLowPower()
  const smallScreen = window.matchMedia('(max-width: 768px)').matches

  useEffect(() => {
    if (!live) return
    let gasFx, pcbFx, cancelled = false, timer = 0
    // شروع فقط با اولین تعامل واقعی کاربر — روی دسکتاپ fallbackِ load+8s هم هست.
    // ورود لایه‌ها با محو نرم opacity است (composite-only، بدون جابه‌جایی چیدمان).
    // چرخش پیکسلی بی‌پایان در پنجره‌ی لود، Speed Index را خراب می‌کرد
    const boot = () => {
      if (cancelled) return
      // روی صفحه کوچک شیدر گاز با رزولوشن پایین‌تر می‌دهد — نرمی بخشیدن به GPU موبایل
      gasFx = gas(glowRef.current, { amp: 0.5, scale: 2.3, res: smallScreen ? 0.25 : 0.3, fps: 20 })
      pcbFx = circuit(pcbRef.current, { alpha: 0.8, fps: 15 })
      if (glowRef.current) glowRef.current.style.opacity = '1'
      if (pcbRef.current) pcbRef.current.style.opacity = '0.9'
    }
    const schedule = () => { if (!smallScreen) timer = setTimeout(boot, 8000) }
    if (document.readyState === 'complete') schedule()
    else window.addEventListener('load', schedule, { once: true })
    // رویداد scroll مصنوعی هنگام لود (scrollY=0) تعامل واقعی نیست — نباید بوت را
    // زودتر از حرکت واقعی کاربر فعال کند (once:true نیست تا مصرفش نکند)
    const onInteract = (e) => {
      if (e.type === 'scroll' && (window.scrollY || 0) <= 0) return
      clearTimeout(timer)
      boot()
      INTERACT_EVENTS.forEach(ev => window.removeEventListener(ev, onInteract))
    }
    const INTERACT_EVENTS = ['pointerdown', 'touchstart', 'scroll', 'keydown']
    INTERACT_EVENTS.forEach(ev => window.addEventListener(ev, onInteract, { passive: true }))
    return () => {
      cancelled = true
      clearTimeout(timer)
      window.removeEventListener('load', schedule)
      INTERACT_EVENTS.forEach(ev => window.removeEventListener(ev, onInteract))
      gasFx?.destroy(); pcbFx?.destroy()
    }
  }, [live, smallScreen])

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: -10,
        pointerEvents: 'none',
        background: 'var(--color-bg-primary)',
      }}
    >
      {/* هاله طلایی استاتیک — پایه‌ی همیشگی برای دستگاه کم‌توان و پایه‌ی پیش از تعامل روی ویوپورت کوچک */}
      {(!live || smallScreen) && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(ellipse 70% 45% at 50% 0%, rgb(var(--color-brand-rgb) / 0.09), transparent 70%)',
          }}
        />
      )}
      {live && (
        <>
          {/* لایه دود گازی — شیدر WebGL (با تعامل کاربر و محو نرم وارد می‌شود) */}
          <div ref={glowRef} style={{ position: 'absolute', inset: 0, opacity: 0, transition: 'opacity 0.9s ease' }} />
          {/* لایه رد مدار الکترونیکی با پالس‌های الکترونی */}
          <div ref={pcbRef} style={{ position: 'absolute', inset: 0, opacity: 0, transition: 'opacity 0.9s ease' }} />
        </>
      )}
      {/* گرید نقطه‌ای بسیار ظریف روی همه لایه‌ها */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: 'radial-gradient(rgb(var(--color-text-primary-rgb) / 0.09) 1px, transparent 1px)',
          backgroundSize: '26px 26px',
          maskImage: 'radial-gradient(ellipse 90% 70% at 50% 30%, #000 30%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(ellipse 90% 70% at 50% 30%, #000 30%, transparent 100%)',
        }}
      />
    </div>
  )
}
