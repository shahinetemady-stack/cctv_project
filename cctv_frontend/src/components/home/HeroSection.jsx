import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

// ─── قطعات ────────────────────────────────────────────────────────
// phase: در چه درصدی از اسکرول این قطعه شروع به ظاهر شدن می‌کند
// initial  = موقعیت خارج از صفحه (شروع)
// exploded = موقعیت معلق در هوا
// assembled= موقعیت مرکز (مونتاژ شده)
const PARTS = [
  {
    id: 'pcb', label: 'برد اصلی PCB', spec: 'HiSilicon Hi3516 | 5MP ISP',
    img: '/images/cam_pcb.jpg', color: '#6495ed',
    enterAt: 0.03, // شروع ورود
    initial:  { x:  220, y: -200, r: -20, s: 0,   w: 170, h: 110 },
    exploded: { x:  190, y: -140, r:  -8, s: 1,   w: 170, h: 110 },
    assembled:{ x:    0, y:    0, r:   0, s: 0.85, w: 170, h: 110 },
  },
  {
    id: 'lens', label: 'لنز اصلی', spec: '3.6mm | F1.6 | IR Cut',
    img: '/images/cam_lens.jpg', color: '#ffa500',
    enterAt: 0.12,
    initial:  { x: -220, y: -180, r:  25, s: 0,   w: 120, h: 120 },
    exploded: { x: -180, y: -120, r:  10, s: 1,   w: 120, h: 120 },
    assembled:{ x:    0, y:    0, r:   0, s: 1,   w: 120, h: 120 },
  },
  {
    id: 'lens2', label: 'هولدر لنز', spec: 'M12 Mount | آلومینیوم',
    img: '/images/cam_lens2.jpg', color: '#aaaaff',
    enterAt: 0.22,
    initial:  { x:  210, y:  180, r:  18, s: 0,   w: 110, h:  85 },
    exploded: { x:  175, y:  145, r:   7, s: 1,   w: 110, h:  85 },
    assembled:{ x:    0, y:    0, r:   0, s: 0.9, w: 110, h:  85 },
  },
  {
    id: 'parts', label: 'ماژول LED', spec: '3000K | 30m | IP65',
    img: '/images/cam_parts.jpg', color: '#ffdd44',
    enterAt: 0.32,
    initial:  { x: -200, y:  175, r: -18, s: 0,   w: 140, h:  85 },
    exploded: { x: -170, y:  150, r:  -6, s: 1,   w: 140, h:  85 },
    assembled:{ x:    0, y:    0, r:   0, s: 0.9, w: 140, h:  85 },
  },
  {
    id: 'body', label: 'بدنه دوربین', spec: 'Aluminum | IP67',
    img: '/images/cam_body.png', color: '#88ccff',
    enterAt: 0.42,
    initial:  { x:    0, y:  220, r:   0, s: 0,   w: 210, h: 140 },
    exploded: { x:    0, y:  185, r:   0, s: 1,   w: 210, h: 140 },
    assembled:{ x:    0, y:    0, r:   0, s: 1,   w: 210, h: 140 },
  },
]

// اسکرول کلی:
// 0.00 → 0.50 : قطعات یکی‌یکی وارد می‌شوند و معلق می‌مانند
// 0.50 → 0.75 : همه قطعات به مرکز می‌آیند (مونتاژ)
// 0.75 → 0.85 : قطعات محو می‌شوند
// 0.85 → 1.00 : دوربین نهایی ظاهر می‌شود

function lerp(a, b, t) { return a + (b - a) * t }
function easeOut(t)    { return 1 - Math.pow(1-t, 3) }
function easeInOut(t)  { return t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2)/2 }
function easeIn(t)     { return t * t * t }
function clamp(v,a,b)  { return Math.max(a, Math.min(b, v)) }

function getPartState(part, scroll) {
  const ENTER_DUR   = 0.10  // مدت ورود هر قطعه
  const ASSEMBLE_S  = 0.52  // شروع مونتاژ
  const ASSEMBLE_E  = 0.76  // پایان مونتاژ
  const FADE_E      = 0.86  // پایان محو شدن

  // قبل از ورود — مخفی
  if (scroll < part.enterAt) {
    return { x: part.initial.x, y: part.initial.y, r: part.initial.r, s: 0, w: part.initial.w, h: part.initial.h, opacity: 0 }
  }

  // مرحله ورود: initial → exploded
  if (scroll < part.enterAt + ENTER_DUR) {
    const t = easeOut(clamp((scroll - part.enterAt) / ENTER_DUR, 0, 1))
    return {
      x: lerp(part.initial.x, part.exploded.x, t),
      y: lerp(part.initial.y, part.exploded.y, t),
      r: lerp(part.initial.r, part.exploded.r, t),
      s: lerp(0, part.exploded.s, t),
      w: part.exploded.w, h: part.exploded.h,
      opacity: t,
    }
  }

  // مرحله معلق: ثابت در exploded (با کمی wobble در render)
  if (scroll < ASSEMBLE_S) {
    return { ...part.exploded, r: part.exploded.r, opacity: 1 }
  }

  // مرحله مونتاژ: exploded → assembled
  if (scroll < ASSEMBLE_E) {
    const t = easeInOut(clamp((scroll - ASSEMBLE_S) / (ASSEMBLE_E - ASSEMBLE_S), 0, 1))
    return {
      x: lerp(part.exploded.x, part.assembled.x, t),
      y: lerp(part.exploded.y, part.assembled.y, t),
      r: lerp(part.exploded.r, 0, t),
      s: lerp(part.exploded.s, part.assembled.s, t),
      w: lerp(part.exploded.w, part.assembled.w, t),
      h: lerp(part.exploded.h, part.assembled.h, t),
      opacity: 1,
    }
  }

  // مرحله محو شدن
  if (scroll < FADE_E) {
    const t = easeIn(clamp((scroll - ASSEMBLE_E) / (FADE_E - ASSEMBLE_E), 0, 1))
    return { ...part.assembled, opacity: 1 - t }
  }

  return { ...part.assembled, opacity: 0 }
}

export default function HeroSection() {
  const sectionRef = useRef(null)
  const [scroll, setScroll] = useState(0)
  const [parts, setParts]   = useState(PARTS)
  const rafRef = useRef(null)
  const timeRef = useRef(0)

  // لود تنظیمات ادمین
  useEffect(() => {
    try {
      const saved = localStorage.getItem('hero_parts_config')
      if (saved) {
        const config = JSON.parse(saved)
        setParts(prev => prev.map(p => {
          const ov = config.find(c => c.id === p.id)
          return ov ? { ...p, img: ov.img || p.img, label: ov.label || p.label, spec: ov.spec || p.spec } : p
        }))
      }
    } catch {}
  }, [])

  // scroll handler — دقیق و سریع
  useEffect(() => {
    const onScroll = () => {
      if (!sectionRef.current) return
      const rect    = sectionRef.current.getBoundingClientRect()
      const total   = sectionRef.current.offsetHeight - window.innerHeight
      if (total <= 0) return
      const scrolled = Math.max(0, -rect.top)
      setScroll(Math.min(1, scrolled / total))
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // RAF برای wobble animation قطعات معلق
  const [wobble, setWobble] = useState(0)
  useEffect(() => {
    let id
    const tick = () => {
      timeRef.current += 0.016
      setWobble(timeRef.current)
      id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [])

  const assembled     = scroll >= 0.86
  const assembling    = scroll >= 0.52 && scroll < 0.76
  const revealProg    = clamp((scroll - 0.82) / 0.12, 0, 1)
  const finalOpacity  = easeInOut(revealProg)

  const phases = [
    { at: 0,    text: '↓ اسکرول کنید — دوربین مونتاژ می‌شود', sub: 'SCROLL TO ASSEMBLE' },
    { at: 0.03, text: 'برد اصلی PCB',        sub: 'HiSilicon Hi3516 | 5MP ISP' },
    { at: 0.12, text: 'لنز و اپتیک',          sub: '3.6mm F1.6 | IR Cut Filter' },
    { at: 0.22, text: 'هولدر لنز',            sub: 'M12 Mount | آلومینیوم' },
    { at: 0.32, text: 'ماژول LED Warm Light', sub: '3000K | 30m | IP65' },
    { at: 0.42, text: 'بدنه آلومینیومی',      sub: 'IP67 | ضدزنگ' },
    { at: 0.52, text: 'در حال مونتاژ...',     sub: 'assembling...' },
    { at: 0.86, text: 'دوربین آماده است ✓',   sub: '5MP | Starlight | Full Color Night Vision' },
  ]
  const currentPhase = [...phases].reverse().find(p => scroll >= p.at) || phases[0]

  return (
    <section
      ref={sectionRef}
      style={{ position: 'relative', height: '600vh', background: 'transparent' }}
    >
      <div style={{
        position: 'sticky', top: 0,
        height: '100vh', width: '100%',
        overflow: 'hidden',
        background: 'transparent',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>

        {/* خطوط grid ظریف */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px),' +
            'linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px)',
          backgroundSize: '70px 70px',
        }}/>

        {/* halo نور مرکزی */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          transition: 'all 1.5s ease',
          background: assembling
            ? 'radial-gradient(ellipse at 50% 50%, rgba(255,140,0,0.12) 0%, rgba(100,149,237,0.05) 30%, transparent 65%)'
            : assembled
            ? 'radial-gradient(ellipse at 50% 50%, rgba(255,165,0,0.15) 0%, transparent 55%)'
            : 'radial-gradient(ellipse at 50% 50%, rgba(100,149,237,0.05) 0%, transparent 60%)',
        }}/>

        {/* progress bar بالای صفحه */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'rgba(255,255,255,0.04)', zIndex: 30 }}>
          <div style={{
            height: '100%', width: `${scroll * 100}%`,
            background: 'linear-gradient(90deg,#ff8c00,#ffd700)',
            boxShadow: '0 0 8px rgba(255,165,0,0.8)',
            transition: 'width 0.05s',
          }}/>
        </div>

        {/* ═══ PARTS CONTAINER ═══ */}
        <div style={{
          position: 'absolute',
          left: '50%', top: '50%',
          width: 0, height: 0,
          zIndex: 10,
        }}>
          {parts.map(part => {
            const st = getPartState(part, scroll)
            if (st.opacity < 0.01) return null

            // wobble فقط در حالت معلق
            const inExploded = scroll >= part.enterAt + 0.10 && scroll < 0.52
            const wobbleY = inExploded ? Math.sin(wobble * 1.2 + part.enterAt * 8) * 5 : 0
            const wobbleR = inExploded ? Math.sin(wobble * 0.8 + part.enterAt * 5) * 1.5 : 0

            const isActive = scroll >= part.enterAt && scroll < part.enterAt + 0.12

            // halo رنگی پشت قطعه
            const haloSize = Math.max(st.w, st.h) * 1.8
            const haloOpacity = isActive ? 0.35 : inExploded ? 0.15 : 0

            return (
              <div
                key={part.id}
                style={{
                  position: 'absolute',
                  left: 0, top: 0,
                  width:  st.w,
                  height: st.h,
                  transform: `translate(calc(${st.x}px - 50%), calc(${st.y + wobbleY}px - 50%)) rotate(${st.r + wobbleR}deg) scale(${st.s})`,
                  opacity: st.opacity,
                  pointerEvents: 'none',
                  willChange: 'transform, opacity',
                }}
              >
                {/* halo نور پشت قطعه */}
                <div style={{
                  position: 'absolute',
                  left: '50%', top: '50%',
                  width: haloSize, height: haloSize,
                  transform: 'translate(-50%, -50%)',
                  borderRadius: '50%',
                  background: `radial-gradient(ellipse, ${part.color}55 0%, ${part.color}22 40%, transparent 70%)`,
                  opacity: haloOpacity,
                  transition: 'opacity 0.5s',
                  pointerEvents: 'none',
                  zIndex: -1,
                }}/>

                {/* عکس قطعه */}
                <img
                  src={part.img}
                  alt={part.label}
                  style={{
                    width: '100%', height: '100%',
                    objectFit: 'contain',
                    display: 'block',
                    filter: isActive
                      ? `drop-shadow(0 0 18px ${part.color}cc) drop-shadow(0 0 6px ${part.color}88)`
                      : inExploded
                      ? `drop-shadow(0 0 8px ${part.color}66)`
                      : 'none',
                  }}
                  onError={e => {
                    e.target.style.display = 'none'
                    const fb = e.target.nextSibling
                    if (fb) fb.style.display = 'flex'
                  }}
                />

                {/* fallback اگر عکس لود نشد */}
                <div style={{
                  display: 'none',
                  position: 'absolute', inset: 0,
                  background: 'rgba(5,2,20,0.85)',
                  border: `1px solid ${part.color}55`,
                  borderRadius: 10,
                  alignItems: 'center', justifyContent: 'center',
                  flexDirection: 'column', gap: 6,
                }}>
                  <div style={{ fontSize: 10, color: part.color, fontFamily: 'monospace', textAlign: 'center', padding: '0 8px' }}>
                    {part.label}
                  </div>
                  <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                    {part.spec}
                  </div>
                </div>

                {/* label زیر قطعه فعال */}
                {isActive && (
                  <div style={{
                    position: 'absolute', bottom: -26, left: '50%',
                    transform: 'translateX(-50%)',
                    whiteSpace: 'nowrap', fontSize: 9,
                    color: part.color, fontFamily: 'monospace',
                    letterSpacing: '0.8px', opacity: 0.9,
                    textShadow: `0 0 8px ${part.color}`,
                  }}>
                    {part.label}
                  </div>
                )}

                {/* خط اتصال به مرکز — فقط در حالت معلق */}
                {inExploded && (
                  <div style={{
                    position: 'absolute',
                    left: '50%', top: '50%',
                    width: Math.sqrt(st.x*st.x + st.y*st.y),
                    height: 1,
                    background: `linear-gradient(90deg, transparent, ${part.color}33)`,
                    transformOrigin: '0 50%',
                    transform: `rotate(${Math.atan2(-st.y, -st.x) * 180 / Math.PI}deg)`,
                    opacity: 0.4,
                    pointerEvents: 'none',
                  }}/>
                )}
              </div>
            )
          })}

          {/* ═══ دوربین نهایی ═══ */}
          {scroll > 0.80 && (
            <div style={{
              position: 'absolute',
              left: 0, top: 0,
              transform: `translate(-50%, -50%) scale(${0.7 + finalOpacity * 0.3})`,
              opacity: finalOpacity,
              pointerEvents: 'none',
              filter: `drop-shadow(0 0 40px rgba(255,165,0,${finalOpacity * 0.6})) drop-shadow(0 0 80px rgba(255,165,0,${finalOpacity * 0.3}))`,
            }}>
              <img
                src="/images/cam_body.png"
                alt="دوربین مداربسته"
                style={{ width: 290, height: 'auto', objectFit: 'contain', display: 'block' }}
                onError={e => {
                  e.target.style.display = 'none'
                  const fb = e.target.nextSibling
                  if (fb) fb.style.display = 'flex'
                }}
              />
              <div style={{
                display: 'none',
                width: 240, height: 160,
                background: 'rgba(255,165,0,0.06)',
                border: '1px solid rgba(255,165,0,0.4)',
                borderRadius: 18,
                alignItems: 'center', justifyContent: 'center',
                flexDirection: 'column', gap: 10,
              }}>
                <div style={{ fontSize: 48 }}>📷</div>
                <div style={{ fontSize: 13, color: '#ffa500', fontFamily: 'Tahoma' }}>دوربین آماده</div>
              </div>
            </div>
          )}
        </div>

        {/* ═══ متن سمت راست ═══ */}
        <div style={{
          position: 'absolute', top: '50%', right: 80,
          transform: 'translateY(-50%)',
          direction: 'rtl', maxWidth: 380, zIndex: 20,
          opacity: Math.max(0, 1 - scroll * 2 + 0.35),
        }}>
          {/* phase indicators */}
          <div style={{ display: 'flex', gap: 3, marginBottom: 20 }}>
            {phases.map((p, i) => (
              <div key={i} style={{
                height: 2, flex: 1, borderRadius: 1,
                background: scroll >= p.at ? '#ffa500' : 'rgba(255,255,255,0.08)',
                boxShadow: scroll >= p.at ? '0 0 6px rgba(255,165,0,0.6)' : 'none',
                transition: 'background 0.3s',
              }}/>
            ))}
          </div>

          {/* badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: 'rgba(255,165,0,0.08)',
            border: '0.5px solid rgba(255,165,0,0.3)',
            borderRadius: 24, padding: '6px 16px', marginBottom: 22,
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: assembled ? '#00ff88' : '#ffa500',
              boxShadow: `0 0 10px ${assembled ? '#00ff88' : '#ffa500'}`,
              transition: 'all 0.5s', animation: 'heroPulse 2s infinite',
            }}/>
            <span style={{
              fontSize: 11, letterSpacing: '1.5px', fontFamily: 'Tahoma',
              color: assembled ? 'rgba(0,255,136,0.95)' : 'rgba(255,165,0,0.95)',
              transition: 'color 0.5s',
            }}>
              {assembled ? 'دوربین آماده است ✓' : 'در حال مونتاژ...'}
            </span>
          </div>

          <h1 style={{
            fontSize: 'clamp(26px,3.2vw,50px)',
            fontWeight: 900, color: '#fff', lineHeight: 1.15,
            marginBottom: 16, fontFamily: 'Tahoma, Arial',
          }}>
            قطعات{' '}
            <span style={{ color: '#ffa500', textShadow: '0 0 30px rgba(255,165,0,0.5)' }}>دوربین</span>
            <br/>مداربسته
          </h1>

          <div style={{ minHeight: 50, marginBottom: 20 }}>
            <div style={{ fontSize: 14, color: '#ffa500', fontFamily: 'Tahoma', fontWeight: 600, marginBottom: 5 }}>
              {currentPhase.text}
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', letterSpacing: '0.8px' }}>
              {currentPhase.sub}
            </div>
          </div>

          {!assembled && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
              <div style={{ flex: 1, height: 2, background: 'rgba(255,255,255,0.08)', borderRadius: 1, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${scroll * 100}%`,
                  background: 'linear-gradient(90deg,#ff8c00,#ffd700)',
                  transition: 'width 0.05s',
                }}/>
              </div>
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', direction: 'ltr', minWidth: 34 }}>
                {Math.round(scroll * 100)}%
              </span>
            </div>
          )}

          <div style={{
            display: 'flex', gap: 12, flexWrap: 'wrap',
            opacity: assembled ? 1 : 0.12,
            transform: assembled ? 'translateY(0)' : 'translateY(12px)',
            transition: 'all 0.8s cubic-bezier(0.34,1.56,0.64,1)',
            pointerEvents: assembled ? 'auto' : 'none',
          }}>
            <Link to="/products" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: '#ffa500', color: '#000',
              textDecoration: 'none', borderRadius: 12,
              padding: '14px 28px', fontSize: 14, fontWeight: 700, fontFamily: 'Tahoma',
              boxShadow: '0 4px 28px rgba(255,165,0,0.5)',
            }}>
              مشاهده محصولات
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#000" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </Link>
            <Link to="/china-order" style={{
              display: 'inline-flex', alignItems: 'center',
              background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.75)',
              textDecoration: 'none', border: '0.5px solid rgba(255,255,255,0.15)',
              borderRadius: 12, padding: '14px 22px', fontSize: 14, fontFamily: 'Tahoma',
            }}>سفارش از چین</Link>
          </div>
        </div>

        {/* ═══ stats bar پایین ═══ */}
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          padding: '14px 80px',
          display: 'grid', gridTemplateColumns: 'repeat(4,1fr)',
          background: 'rgba(0,0,0,0.72)',
          backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
          borderTop: '0.5px solid rgba(255,255,255,0.05)',
          direction: 'rtl', zIndex: 20,
        }}>
          {[
            { val: '+۱۰۰۰', lbl: 'نوع قطعه' },
            { val: '۳۰ سال', lbl: 'سابقه فعالیت' },
            { val: '۴۸h',   lbl: 'تحویل اکسپرس' },
            { val: '۳۰ روز', lbl: 'ضمانت اصالت' },
          ].map((s, i) => (
            <div key={i} style={{
              textAlign: 'center', padding: '6px 0',
              borderLeft: i > 0 ? '0.5px solid rgba(255,255,255,0.05)' : 'none',
            }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#ffa500', fontFamily: 'monospace' }}>{s.val}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', fontFamily: 'Tahoma', marginTop: 2 }}>{s.lbl}</div>
            </div>
          ))}
        </div>

        {/* scroll hint */}
        {scroll < 0.02 && (
          <div style={{
            position: 'absolute', bottom: 90, left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', gap: 8, zIndex: 20,
          }}>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '3px', fontFamily: 'monospace' }}>
              SCROLL TO ASSEMBLE
            </div>
            <div style={{
              width: 22, height: 38,
              border: '1px solid rgba(255,165,0,0.25)',
              borderRadius: 11,
              display: 'flex', justifyContent: 'center', paddingTop: 5,
            }}>
              <div style={{ width: 2, height: 7, background: '#ffa500', borderRadius: 1, animation: 'heroScrollWheel 1.5s infinite' }}/>
            </div>
          </div>
        )}

        <style>{`
          @keyframes heroPulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
          @keyframes heroScrollWheel { 0%{transform:translateY(0);opacity:1} 100%{transform:translateY(12px);opacity:0} }
        `}</style>
      </div>
    </section>
  )
}
