import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

// ─── تنظیمات قطعات — از API لود می‌شود ──────────────────────
const DEFAULT_PARTS = [
  {
    id: 'body',
    img: '/images/cam_body.png',
    label: 'بدنه آلومینیوم',
    spec: 'IP67 | ضدآب | ضدضربه',
    color: '#e0e0e0',
    assembled: { x: 0, y: 0, rotate: 0, scale: 1, w: 320, h: 180 },
    exploded:  { x: 0, y: 0, rotate: 0, scale: 1.05, w: 320, h: 180 },
    initial:   { x: -500, y: 200, rotate: -15, scale: 0.7, w: 320, h: 180 },
    zIndex: 2, phase: 0,
  },
  {
    id: 'pcb',
    img: '/images/cam_pcb.jpg',
    label: 'برد اصلی PCB',
    spec: 'HiSilicon Hi3516 | 4 لایه',
    color: '#FF8C00',
    assembled: { x: -30, y: -10, rotate: 0, scale: 0.55, w: 160, h: 160 },
    exploded:  { x: -280, y: -160, rotate: -12, scale: 0.65, w: 160, h: 160 },
    initial:   { x: 600, y: -300, rotate: 30, scale: 0.3, w: 160, h: 160 },
    zIndex: 4, phase: 0.15,
  },
  {
    id: 'lens',
    img: '/images/cam_lens.jpg',
    label: 'لنز اصلی',
    spec: '3.6mm | F1.6 | M12',
    color: '#aaa',
    assembled: { x: 80, y: 0, rotate: 0, scale: 0.5, w: 120, h: 120 },
    exploded:  { x: 280, y: -150, rotate: 15, scale: 0.65, w: 120, h: 120 },
    initial:   { x: -400, y: -350, rotate: -20, scale: 0.3, w: 120, h: 120 },
    zIndex: 5, phase: 0.3,
  },
  {
    id: 'lens2',
    img: '/images/cam_lens2.jpg',
    label: 'هولدر لنز',
    spec: 'M12 Mount | آلومینیوم',
    color: '#888',
    assembled: { x: 70, y: 5, rotate: 0, scale: 0.45, w: 130, h: 100 },
    exploded:  { x: 300, y: 100, rotate: 20, scale: 0.6, w: 130, h: 100 },
    initial:   { x: 500, y: 300, rotate: 25, scale: 0.3, w: 130, h: 100 },
    zIndex: 3, phase: 0.4,
  },
  {
    id: 'parts',
    img: '/images/cam_parts.jpg',
    label: 'ماژول LED + PCB',
    spec: 'Warm Light | 3000K | IP65',
    color: '#FFB347',
    assembled: { x: -20, y: 0, rotate: 0, scale: 0.5, w: 200, h: 160 },
    exploded:  { x: -260, y: 160, rotate: 10, scale: 0.65, w: 200, h: 160 },
    initial:   { x: 0, y: 500, rotate: 5, scale: 0.3, w: 200, h: 160 },
    zIndex: 3, phase: 0.55,
  },
]

function lerp(a, b, t) { return a + (b - a) * t }
function easeInOut(t) { return t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2)/2 }
function easeOut(t) { return 1 - Math.pow(1-t, 3) }

function interpolateState(initial, exploded, assembled, scrollP) {
  if (scrollP <= 0.5) {
    const t = easeOut(scrollP * 2)
    return {
      x: lerp(initial.x, exploded.x, t),
      y: lerp(initial.y, exploded.y, t),
      rotate: lerp(initial.rotate, exploded.rotate, t),
      scale: lerp(initial.scale, exploded.scale, t),
      w: lerp(initial.w, exploded.w, t),
      h: lerp(initial.h, exploded.h, t),
      opacity: t,
    }
  } else {
    const t = easeInOut((scrollP - 0.5) * 2)
    return {
      x: lerp(exploded.x, assembled.x, t),
      y: lerp(exploded.y, assembled.y, t),
      rotate: lerp(exploded.rotate, assembled.rotate, t),
      scale: lerp(exploded.scale, assembled.scale, t),
      w: lerp(exploded.w, assembled.w, t),
      h: lerp(exploded.h, assembled.h, t),
      opacity: 1,
    }
  }
}

// ─── Smart Image — PNG شفاف یا JPG ──────────────────────────
function PartImage({ src, alt, color, isActive }) {
  const isPng = src.toLowerCase().endsWith('.png')
  const [imgSrc, setImgSrc] = useState(src)

  return (
    <img
      src={imgSrc}
      alt={alt}
      onError={() => {
        // اگر jpg نشد png را امتحان کن و برعکس
        if (imgSrc.endsWith('.jpg')) setImgSrc(imgSrc.replace('.jpg', '.png'))
        else if (imgSrc.endsWith('.png')) setImgSrc(imgSrc.replace('.png', '.jpg'))
      }}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'contain',
        display: 'block',
        background: 'transparent',
        // PNG شفاف نیازی به border و borderRadius ندارد
        borderRadius: isPng ? 0 : 8,
        border: isPng ? 'none' : isActive ? `1px solid ${color}50` : '1px solid rgba(255,255,255,0.04)',
      }}
    />
  )
}

export default function HeroSection() {
  const sectionRef = useRef(null)
  const [scroll, setScroll] = useState(0)
  const [parts, setParts] = useState(DEFAULT_PARTS)

  // لود تنظیمات قالب از localStorage (که ادمین تنظیم می‌کند)
  useEffect(() => {
    try {
      const saved = localStorage.getItem('hero_parts_config')
      if (saved) {
        const config = JSON.parse(saved)
        setParts(prev => prev.map(p => {
          const override = config.find(c => c.id === p.id)
          return override ? { ...p, img: override.img, label: override.label, spec: override.spec } : p
        }))
      }
    } catch {}
  }, [])

  useEffect(() => {
    const onScroll = () => {
      if (!sectionRef.current) return
      const rect = sectionRef.current.getBoundingClientRect()
      const total = sectionRef.current.offsetHeight - window.innerHeight
      const scrolled = Math.max(0, -rect.top)
      setScroll(Math.min(1, scrolled / total))
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const assembled = scroll >= 0.88
  const exploding = scroll > 0.05 && scroll < 0.55

  const phases = [
    { at: 0,    text: 'اسکرول کنید — دوربین مونتاژ می‌شود', sub: '↓ SCROLL TO ASSEMBLE' },
    { at: 0.12, text: 'برد اصلی PCB',        sub: 'HiSilicon Hi3516 | 5MP ISP' },
    { at: 0.28, text: 'لنز و هولدر',          sub: '3.6mm F1.6 | IR Cut Filter' },
    { at: 0.48, text: 'ماژول LED Warm Light', sub: '3000K | 30m Range | IP65' },
    { at: 0.65, text: 'در حال مونتاژ...',     sub: 'بدنه IP67 | آلومینیوم' },
    { at: 0.88, text: 'دوربین آماده است! ✓',  sub: '5MP Starlight | Full Color Night Vision' },
  ]
  const currentPhase = [...phases].reverse().find(p => scroll >= p.at) || phases[0]
  const activePart = scroll < 0.55
    ? parts.filter(p => scroll >= p.phase).slice(-1)[0]
    : null

  return (
    <section
      ref={sectionRef}
      style={{ position: 'relative', height: '600vh', background: '#000' }}
    >
      <div style={{
        position: 'sticky', top: 0,
        height: '100vh', width: '100%',
        overflow: 'hidden',
        background: '#050505',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {/* grid */}
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)',
          backgroundSize: '70px 70px',
        }}/>

        {/* ambient glow */}
        <div style={{
          position: 'absolute', inset: 0,
          background: `radial-gradient(ellipse at 40% 50%, rgba(255,165,0,${assembled ? 0.06 : 0.025}) 0%, transparent 60%)`,
          transition: 'all 1s', pointerEvents: 'none',
        }}/>

        {/* scan lines */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.01) 3px, rgba(0,0,0,0.01) 4px)',
          pointerEvents: 'none',
        }}/>

        {/* progress bar */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'rgba(255,255,255,0.04)' }}>
          <div style={{
            height: '100%', width: `${scroll * 100}%`,
            background: 'linear-gradient(90deg, #ffa500, #ffcc44)',
            boxShadow: '0 0 10px rgba(255,165,0,0.7)',
            transition: 'width 0.05s',
          }}/>
        </div>

        {/* connector lines */}
        {exploding && (
          <svg style={{
            position: 'absolute', inset: 0,
            width: '100%', height: '100%',
            pointerEvents: 'none',
            opacity: Math.min(1, (scroll - 0.1) / 0.2) * 0.18,
          }}>
            {parts.filter(p => scroll >= p.phase && p.id !== 'body').map(part => {
              const ps = Math.max(0, Math.min(1, (scroll - part.phase) / (1 - part.phase)))
              const state = interpolateState(part.initial, part.exploded, part.assembled, ps)
              const w = typeof window !== 'undefined' ? window.innerWidth : 1200
              const h = typeof window !== 'undefined' ? window.innerHeight : 800
              return (
                <line key={part.id}
                  x1={w/2} y1={h/2}
                  x2={w/2 + state.x} y2={h/2 + state.y}
                  stroke={part.color} strokeWidth="0.8" strokeDasharray="5,7"
                />
              )
            })}
          </svg>
        )}

        {/* ── قطعات ── */}
        {parts.map((part) => {
          const partScroll = Math.max(0, Math.min(1, (scroll - part.phase) / (1 - part.phase)))
          const state = interpolateState(part.initial, part.exploded, part.assembled, partScroll)
          const isActive = activePart?.id === part.id
          const isPng = part.img.toLowerCase().endsWith('.png')

          return (
            <div key={part.id} style={{
              position: 'absolute',
              top: '50%', left: '50%',
              width: state.w, height: state.h,
              transform: `translate(calc(-50% + ${state.x}px), calc(-50% + ${state.y}px)) rotate(${state.rotate}deg) scale(${state.scale})`,
              opacity: state.opacity,
              zIndex: part.zIndex,
              background: 'transparent',
              filter: isActive
                ? `drop-shadow(0 0 24px ${part.color}) drop-shadow(0 0 8px ${part.color}80)`
                : assembled
                ? `drop-shadow(0 12px 30px rgba(0,0,0,0.6))`
                : `drop-shadow(0 4px 12px rgba(0,0,0,0.4))`,
              willChange: 'transform, opacity',
            }}>
              <PartImage src={part.img} alt={part.label} color={part.color} isActive={isActive} />

              {/* label */}
              {exploding && scroll >= part.phase + 0.05 && (
                <div style={{
                  position: 'absolute', bottom: -38,
                  left: '50%', transform: 'translateX(-50%)',
                  textAlign: 'center', whiteSpace: 'nowrap',
                  opacity: Math.min(1, (scroll - part.phase - 0.05) / 0.1),
                  pointerEvents: 'none',
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: part.color, fontFamily: 'Tahoma', direction: 'rtl', textShadow: `0 0 10px ${part.color}50` }}>
                    {part.label}
                  </div>
                  <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', marginTop: 1 }}>
                    {part.spec}
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {/* LED glow */}
        {assembled && (
          <div style={{
            position: 'absolute', top: '50%', left: '45%',
            transform: 'translate(-50%, -50%)',
            width: 300, height: 200, borderRadius: '50%',
            background: 'radial-gradient(ellipse, rgba(255,200,80,0.14) 0%, transparent 70%)',
            animation: 'ledPulse 2s ease-in-out infinite',
            pointerEvents: 'none',
          }}/>
        )}

        {/* ring */}
        <svg style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none', opacity: 0.2,
          width: 500, height: 500,
        }} viewBox="-250 -250 500 500">
          <circle cx="0" cy="0" r="230" fill="none" stroke="rgba(255,165,0,0.1)" strokeWidth="0.5"/>
          <circle cx="0" cy="0" r="230" fill="none"
            stroke="rgba(255,165,0,0.6)" strokeWidth="1"
            strokeDasharray={`${scroll * 1445} 1445`}
            strokeLinecap="round" transform="rotate(-90)"/>
        </svg>

        {/* ── متن راست ── */}
        <div style={{
          position: 'absolute', top: '50%', right: 80,
          transform: 'translateY(-50%)',
          direction: 'rtl', maxWidth: 360, zIndex: 10,
        }}>
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            {phases.map((p, i) => (
              <div key={i} style={{
                height: 2, flex: 1, borderRadius: 1,
                background: scroll >= p.at ? '#ffa500' : 'rgba(255,255,255,0.1)',
                boxShadow: scroll >= p.at ? '0 0 4px rgba(255,165,0,0.5)' : 'none',
                transition: 'background 0.4s',
              }}/>
            ))}
          </div>

          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            background: 'rgba(255,165,0,0.08)',
            border: '0.5px solid rgba(255,165,0,0.25)',
            borderRadius: 24, padding: '5px 14px', marginBottom: 20,
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: assembled ? '#00ff88' : '#ffa500',
              boxShadow: `0 0 8px ${assembled ? '#00ff88' : '#ffa500'}`,
              transition: 'all 0.5s', animation: 'pulse 2s infinite',
            }}/>
            <span style={{
              fontSize: 11, letterSpacing: '1.5px', fontFamily: 'Tahoma',
              color: assembled ? 'rgba(0,255,136,0.9)' : 'rgba(255,165,0,0.9)',
              transition: 'color 0.5s',
            }}>
              {assembled ? 'مونتاژ کامل شد ✓' : 'در حال مونتاژ...'}
            </span>
          </div>

          <h1 style={{
            fontSize: 'clamp(30px, 3.5vw, 50px)',
            fontWeight: 800, color: '#fff', lineHeight: 1.15,
            marginBottom: 16, fontFamily: 'Tahoma, Arial',
          }}>
            قطعات{' '}
            <span style={{ color: '#ffa500', textShadow: '0 0 30px rgba(255,165,0,0.4)' }}>دوربین</span>
            <br/>مداربسته
          </h1>

          <div style={{ minHeight: 48, marginBottom: 20 }}>
            <div style={{ fontSize: 15, color: '#ffa500', fontFamily: 'Tahoma', fontWeight: 600, marginBottom: 5 }}>
              {currentPhase.text}
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace', letterSpacing: '0.5px' }}>
              {currentPhase.sub}
            </div>
          </div>

          {!assembled && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
              <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.08)', borderRadius: 1 }}>
                <div style={{ height: '100%', width: `${scroll * 100}%`, background: '#ffa500', borderRadius: 1, transition: 'width 0.05s' }}/>
              </div>
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', direction: 'ltr', minWidth: 34 }}>
                {Math.round(scroll * 100)}%
              </span>
            </div>
          )}

          <div style={{
            display: 'flex', gap: 12, flexWrap: 'wrap',
            opacity: assembled ? 1 : 0.25,
            transform: assembled ? 'translateY(0)' : 'translateY(12px)',
            transition: 'all 0.7s cubic-bezier(0.34,1.56,0.64,1)',
            pointerEvents: assembled ? 'auto' : 'none',
          }}>
            <Link to="/products" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: '#ffa500', color: '#000',
              textDecoration: 'none', borderRadius: 10,
              padding: '13px 28px', fontSize: 14, fontWeight: 700, fontFamily: 'Tahoma',
              boxShadow: assembled ? '0 4px 24px rgba(255,165,0,0.4)' : 'none',
            }}>
              مشاهده محصولات
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#000" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </Link>
            <Link to="/china-order" style={{
              display: 'inline-flex', alignItems: 'center',
              background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.7)',
              textDecoration: 'none', border: '0.5px solid rgba(255,255,255,0.12)',
              borderRadius: 10, padding: '13px 20px', fontSize: 14, fontFamily: 'Tahoma',
            }}>
              سفارش از چین
            </Link>
          </div>
        </div>

        {/* stats */}
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          padding: '14px 80px',
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
          borderTop: '0.5px solid rgba(255,255,255,0.05)',
          direction: 'rtl', zIndex: 10,
        }}>
          {[
            { val: '+۲۰۰۰', lbl: 'نوع قطعه' },
            { val: '۱۰ sal', lbl: 'سابقه فعالیت' },
            { val: '۴۸h', lbl: 'تحویل اکسپرس' },
            { val: '۱۰۰٪', lbl: 'ضمانت اصالت' },
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

        {scroll < 0.02 && (
          <div style={{
            position: 'absolute', bottom: 90, left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', gap: 8, zIndex: 10,
          }}>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '3px', fontFamily: 'monospace' }}>
              SCROLL TO ASSEMBLE
            </div>
            <div style={{
              width: 22, height: 38, border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: 11, display: 'flex', justifyContent: 'center', paddingTop: 5,
            }}>
              <div style={{ width: 2, height: 7, background: '#ffa500', borderRadius: 1, animation: 'scrollWheel 1.5s infinite' }}/>
            </div>
          </div>
        )}

        <style>{`
          @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
          @keyframes scrollWheel { 0%{transform:translateY(0);opacity:1} 100%{transform:translateY(12px);opacity:0} }
          @keyframes ledPulse { 0%,100%{opacity:0.6;transform:translate(-50%,-50%) scale(1)} 50%{opacity:1;transform:translate(-50%,-50%) scale(1.1)} }
        `}</style>
      </div>
    </section>
  )
}
