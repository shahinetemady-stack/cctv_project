import { useEffect, useRef } from 'react'

/**
 * SiteBackground — پس‌زمینه ثابت سایت (SENTINEL)
 * گرادیان نیمه‌شب/سیان + گرید ظریف + glow دنبال‌کننده موس
 * رنگ‌ها از توکن‌های تم خوانده می‌شوند (دارک/لایت سازگار)
 * فقط CSS — بدون three.js/canvas
 */
export default function SiteBackground() {
  const glowRef = useRef(null)

  useEffect(() => {
    let raf = 0
    const el = glowRef.current
    if (!el) return

    const onMove = (e) => {
      const x = (e.clientX / window.innerWidth) * 100
      const y = (e.clientY / window.innerHeight) * 100
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        el.style.background = `radial-gradient(600px circle at ${x}% ${y}%, var(--bg-glow), transparent 60%)`
      })
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: -10,
        pointerEvents: 'none',
        background: 'var(--site-bg)',
      }}
    >
      {/* گرید سیان بسیار ظریف */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(var(--bg-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--bg-grid-line) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 100% 80% at 50% 0%, black 30%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(ellipse 100% 80% at 50% 0%, black 30%, transparent 100%)',
        }}
      />
      {/* glow دنبال‌کننده موس */}
      <div ref={glowRef} style={{ position: 'absolute', inset: 0 }} />
    </div>
  )
}
