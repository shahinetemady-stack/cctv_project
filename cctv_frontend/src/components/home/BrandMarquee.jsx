// ─── نوار مارکی برندها — تایپوگرافی غول‌پیکر شبیه نمونه‌ی کیمی ──────
// حرکت باند کاملاً با اسکرول عمودی صفحه جابه‌جا می‌شود (scroll-driven) — مثل نمونه
import { useEffect, useRef } from 'react'

const BRANDS = [
  { name: 'YTOT',      cap: 'LENS & SENSOR' },
  { name: 'HS',        cap: 'BOARD' },
  { name: 'RUISION',   cap: 'BOARD' },
  { name: 'ANJVISION', cap: 'BOARD' },
  { name: 'XM',        cap: 'MODULE' },
  { name: 'CW',        cap: 'IRCUT' },
]

export default function BrandMarquee() {
  const trackRef = useRef(null)

  useEffect(() => {
    const track = trackRef.current
    if (!track) return
    let raf = null
    const update = () => {
      raf = null
      const half = track.scrollWidth / 2
      if (half > 0) {
        // چسبیده به اسکرول: هر پیکسل اسکرول عمودی، ~۱ پیکسل جابه‌جایی افقی —
        // ماجولو روی نصف عرض مسیر حلقه می‌بندد تا ناپیوستگی نباشد
        const offset = (window.scrollY * 1.5) % half
        track.style.transform = `translate3d(${-offset}px, 0, 0)`
      }
    }
    const onScroll = () => { if (raf == null) raf = requestAnimationFrame(update) }
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    update()
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <div className="brand-marquee-band" dir="ltr">
      <div className="bm-label">برندهایی که با آنها همکاری داریم</div>
      <div className="marquee-viewport">
        <div className="marquee-track" ref={trackRef}>
          {[...BRANDS, ...BRANDS].map((b, i) => (
            <span key={i} className="bm-item">
              <span className="bm-word">{b.name}</span>
              <span className="bm-cap">( {b.cap} )</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
