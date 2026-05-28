import { useEffect, useRef, useState, useCallback } from 'react'

// ─── قطعات دوربین با عکس‌های واقعی ───────────────────────────
const PARTS = [
  {
    id: 'body',
    label: 'بدنه دوربین',
    spec: 'آلومینیوم | IP67 | ضدآب',
    img: '/images/cam_body.jpg',
    // موقعیت نهایی مونتاژ (مرکز)
    assembledX: 0, assembledY: 0,
    // موقعیت انفجار
    explodeX: 0, explodeY: 0,
    width: 280, height: 160,
    zIndex: 5,
    color: '#e0e0e0',
    rotate: 0,
  },
  {
    id: 'pcb',
    label: 'برد اصلی PCB',
    spec: 'HiSilicon Hi3516 | 4 لایه',
    img: '/images/cam_pcb.jpg',
    assembledX: -20, assembledY: 0,
    explodeX: -200, explodeY: -120,
    width: 100, height: 100,
    zIndex: 3,
    color: '#FF8C00',
    rotate: -5,
  },
  {
    id: 'lens',
    label: 'لنز',
    spec: '3.6mm | F1.6 | IR Cut',
    img: '/images/cam_lens.jpg',
    assembledX: 60, assembledY: 0,
    explodeX: 200, explodeY: -100,
    width: 80, height: 80,
    zIndex: 6,
    color: '#aaa',
    rotate: 0,
  },
  {
    id: 'lens2',
    label: 'هولدر لنز',
    spec: 'M12 Mount | آلومینیوم',
    img: '/images/cam_lens2.jpg',
    assembledX: 60, assembledY: 0,
    explodeX: 220, explodeY: 80,
    width: 90, height: 70,
    zIndex: 4,
    color: '#888',
    rotate: 10,
  },
  {
    id: 'parts',
    label: 'ماژول LED',
    spec: 'Warm Light | ۳۰۰۰K | IP65',
    img: '/images/cam_parts.jpg',
    assembledX: 0, assembledY: 0,
    explodeX: -180, explodeY: 120,
    width: 110, height: 90,
    zIndex: 2,
    color: '#FFB347',
    rotate: 5,
  },
]

// ─── دوربین مونتاژ شده SVG ───────────────────────────────────
function AssembledCamera({ ledOn, glowIntensity }) {
  return (
    <svg viewBox="0 0 400 240" width="400" height="240" style={{ overflow: 'visible' }}>
      <defs>
        {/* glow filter برای LED */}
        <filter id="ledGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={glowIntensity * 8} result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        <filter id="warmGlow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="20" result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#f0f0f0"/>
          <stop offset="50%" stopColor="#e0e0e0"/>
          <stop offset="100%" stopColor="#c8c8c8"/>
        </linearGradient>
        <linearGradient id="mountGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#666"/>
          <stop offset="100%" stopColor="#888"/>
        </linearGradient>
        <radialGradient id="lensGrad" cx="40%" cy="35%">
          <stop offset="0%" stopColor="#334"/>
          <stop offset="40%" stopColor="#112"/>
          <stop offset="80%" stopColor="#001"/>
          <stop offset="100%" stopColor="#000"/>
        </radialGradient>
        <radialGradient id="lensReflect" cx="35%" cy="30%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.6)"/>
          <stop offset="100%" stopColor="rgba(255,255,255,0)"/>
        </radialGradient>
      </defs>

      {/* سایه زیر دوربین */}
      <ellipse cx="185" cy="225" rx="140" ry="12" fill="rgba(0,0,0,0.3)" opacity="0.6"/>

      {/* براکت نصب بالا */}
      <rect x="160" y="8" width="50" height="18" rx="4" fill="url(#mountGrad)"/>
      <rect x="155" y="12" width="60" height="10" rx="3" fill="#555"/>
      <circle cx="168" cy="17" r="4" fill="#333"/>
      <circle cx="202" cy="17" r="4" fill="#333"/>
      <circle cx="168" cy="17" r="2" fill="#666"/>
      <circle cx="202" cy="17" r="2" fill="#666"/>

      {/* بدنه اصلی دوربین */}
      <rect x="30" y="52" width="290" height="148" rx="16" fill="url(#bodyGrad)"/>
      {/* خطوط طراحی بدنه */}
      <rect x="30" y="84" width="290" height="2" fill="rgba(0,0,0,0.06)"/>
      <rect x="30" y="166" width="290" height="2" fill="rgba(0,0,0,0.06)"/>
      {/* اتصال براکت */}
      <rect x="150" y="26" width="70" height="28" rx="3" fill="#d0d0d0"/>
      <rect x="155" y="30" width="60" height="18" rx="2" fill="#c0c0c0"/>

      {/* قسمت جلو — پنل LED */}
      <rect x="30" y="52" width="88" height="148" rx="16" fill="#e8e8e8"/>
      <rect x="30" y="52" width="88" height="148" rx="0" fill="#e0e0e0" style={{clipPath:'inset(0 0 0 16px)'}}/>

      {/* LED های گرم (چپ) */}
      <rect x="38" y="72" width="62" height="22" rx="5"
        fill={ledOn ? '#FFF5E0' : '#ddd'}
        filter={ledOn ? 'url(#ledGlow)' : 'none'}
        opacity={ledOn ? 1 : 0.8}
      />
      {[0,1,2].map(i => (
        <ellipse key={i} cx={50 + i*18} cy={83} rx="6" ry="7"
          fill={ledOn ? `rgba(255,${180-i*10},${50+i*20},${0.9+i*0.03})` : '#bbb'}
          filter={ledOn ? 'url(#ledGlow)' : 'none'}
        />
      ))}

      {/* LED های گرم (پایین) */}
      <rect x="38" y="158" width="62" height="22" rx="5"
        fill={ledOn ? '#FFF5E0' : '#ddd'}
        filter={ledOn ? 'url(#ledGlow)' : 'none'}
        opacity={ledOn ? 1 : 0.8}
      />
      {[0,1,2].map(i => (
        <ellipse key={i} cx={50 + i*18} cy={169} rx="6" ry="7"
          fill={ledOn ? `rgba(255,${180-i*10},${50+i*20},${0.9})` : '#bbb'}
          filter={ledOn ? 'url(#ledGlow)' : 'none'}
        />
      ))}

      {/* نور پخش شده LED روی صحنه */}
      {ledOn && (
        <>
          <ellipse cx="10" cy="126" rx="60" ry="80"
            fill={`rgba(255,200,80,${glowIntensity * 0.18})`}
            filter="url(#warmGlow)"
          />
          <rect x="-80" y="46" width="120" height="160" rx="8"
            fill={`rgba(255,220,100,${glowIntensity * 0.08})`}
          />
        </>
      )}

      {/* حلقه لنز */}
      <circle cx="240" cy="126" r="62" fill="#b8b8b8"/>
      <circle cx="240" cy="126" r="58" fill="#aaa"/>
      <circle cx="240" cy="126" r="52" fill="#222"/>

      {/* شیشه لنز */}
      <circle cx="240" cy="126" r="48" fill="url(#lensGrad)"/>

      {/* حلقه‌های لنز */}
      <circle cx="240" cy="126" r="48" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
      <circle cx="240" cy="126" r="38" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
      <circle cx="240" cy="126" r="26" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1"/>

      {/* انعکاس لنز */}
      <ellipse cx="226" cy="110" rx="14" ry="10" fill="url(#lensReflect)" opacity="0.7"/>
      <circle cx="256" cy="140" r="4" fill="rgba(255,255,255,0.08)"/>

      {/* هسته لنز */}
      <circle cx="240" cy="126" r="16" fill="#000d1a" opacity="0.9"/>
      <circle cx="240" cy="126" r="8" fill="#000510"/>
      <circle cx="236" cy="122" r="3" fill="rgba(100,149,237,0.3)"/>

      {/* حلقه بیرونی لنز */}
      <circle cx="240" cy="126" r="62" fill="none" stroke="#c0c0c0" strokeWidth="1"/>
      <circle cx="240" cy="126" r="60" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="0.5"/>

      {/* تزئینات بدنه */}
      <rect x="108" y="68" width="4" height="116" rx="2" fill="rgba(0,0,0,0.08)"/>
      <rect x="316" y="68" width="4" height="116" rx="2" fill="rgba(0,0,0,0.08)"/>

      {/* نوشته مدل */}
      <text x="175" y="205" textAnchor="middle" fontSize="8"
        fill="rgba(0,0,0,0.2)" fontFamily="monospace" letterSpacing="1">
        5MP • STARLIGHT • IP67
      </text>

      {/* پیچ‌های گوشه */}
      {[[38,60],[312,60],[38,188],[312,188]].map(([x,y],i) => (
        <g key={i}>
          <circle cx={x} cy={y} r="5" fill="#c0c0c0" stroke="#aaa" strokeWidth="0.5"/>
          <line x1={x-3} y1={y} x2={x+3} y2={y} stroke="#999" strokeWidth="1"/>
          <line x1={x} y1={y-3} x2={x} y2={y+3} stroke="#999" strokeWidth="1"/>
        </g>
      ))}
    </svg>
  )
}

// ─── Hero Section اصلی ───────────────────────────────────────
export default function HeroSection() {
  const sectionRef = useRef(null)
  const [progress, setProgress] = useState(0) // 0 = assembled, 1 = fully exploded
  const [ledOn, setLedOn] = useState(false)
  const [glowIntensity, setGlowIntensity] = useState(0)
  const [assembledFull, setAssembledFull] = useState(false)
  const rafRef = useRef(null)

  // LED flicker effect
  useEffect(() => {
    if (!ledOn) { setGlowIntensity(0); return }
    let frame
    const flicker = () => {
      setGlowIntensity(0.85 + Math.random() * 0.15)
      frame = setTimeout(flicker, 80 + Math.random() * 120)
    }
    flicker()
    return () => clearTimeout(frame)
  }, [ledOn])

  // scroll handler
  useEffect(() => {
    const onScroll = () => {
      if (!sectionRef.current) return
      const rect = sectionRef.current.getBoundingClientRect()
      const sectionH = sectionRef.current.offsetHeight
      const viewH = window.innerHeight

      // progress: 0 اول → انفجار → مونتاژ → LED روشن
      const scrolled = -rect.top
      const phase1End = viewH * 0.8    // انفجار کامل
      const phase2End = viewH * 1.6    // شروع مونتاژ
      const phase3End = viewH * 2.2    // مونتاژ کامل

      let p = 0
      if (scrolled < 0) p = 0
      else if (scrolled < phase1End) p = scrolled / phase1End
      else if (scrolled < phase2End) p = 1
      else if (scrolled < phase3End) {
        p = 1 - (scrolled - phase2End) / (phase3End - phase2End)
      } else {
        p = 0
        setAssembledFull(true)
        setLedOn(true)
      }

      if (scrolled < phase3End) {
        setAssembledFull(false)
        setLedOn(false)
      }

      setProgress(Math.max(0, Math.min(1, p)))
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // محاسبه transform هر قطعه
  const getPartTransform = useCallback((part) => {
    const ease = progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2

    const x = part.explodeX * ease
    const y = part.explodeY * ease
    const rotate = part.rotate * ease
    const scale = 1 + ease * 0.08

    return {
      transform: `translate(${x}px, ${y}px) rotate(${rotate}deg) scale(${scale})`,
      opacity: progress < 0.05 ? 1 : 0.85 + ease * 0.15,
      filter: ease > 0.5 ? `drop-shadow(0 4px 20px ${part.color}40)` : 'none',
      transition: progress === 0 ? 'transform 1s cubic-bezier(0.34,1.56,0.64,1), opacity 0.5s' : 'none',
      zIndex: part.zIndex,
    }
  }, [progress])

  const showExploded = progress > 0.05
  const labelOpacity = Math.min(1, Math.max(0, (progress - 0.2) / 0.4))

  return (
    <section
      ref={sectionRef}
      style={{
        position: 'relative',
        height: '300vh',
        background: '#000',
      }}
    >
      {/* sticky viewport */}
      <div style={{
        position: 'sticky',
        top: 0,
        height: '100vh',
        width: '100%',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        background: '#030303',
      }}>

        {/* background */}
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.016) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.016) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}/>

        {/* LED warm ambient light */}
        {ledOn && (
          <div style={{
            position: 'absolute',
            left: '20%',
            top: '50%',
            transform: 'translate(-50%,-50%)',
            width: 600, height: 400,
            borderRadius: '50%',
            background: `radial-gradient(ellipse, rgba(255,200,80,${glowIntensity * 0.12}) 0%, transparent 70%)`,
            pointerEvents: 'none',
            transition: 'opacity 0.1s',
          }}/>
        )}

        {/* scan lines */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.012) 3px, rgba(0,0,0,0.012) 4px)',
          pointerEvents: 'none',
        }}/>

        {/* ── main content ── */}
        <div style={{
          width: '100%', maxWidth: 1280,
          margin: '0 auto',
          padding: '0 60px',
          display: 'flex',
          alignItems: 'center',
          gap: 60,
          position: 'relative',
        }}>

          {/* ── چپ: دوربین منفجر / مونتاژ ── */}
          <div style={{
            flex: 1,
            position: 'relative',
            height: 420,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>

            {/* connector lines */}
            {showExploded && PARTS.map(part => {
              if (part.id === 'body') return null
              const ease = Math.min(1, (progress - 0.05) / 0.5)
              return (
                <svg key={`conn-${part.id}`} style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  pointerEvents: 'none',
                  opacity: ease * 0.25,
                }}>
                  <line
                    x1="50%" y1="50%"
                    x2={`calc(50% + ${part.explodeX * ease}px)`}
                    y2={`calc(50% + ${part.explodeY * ease}px)`}
                    stroke={part.color}
                    strokeWidth="0.8"
                    strokeDasharray="4,6"
                  />
                </svg>
              )
            })}

            {/* دوربین مونتاژ شده */}
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              {/* قطعات منفجر */}
              {PARTS.map((part) => (
                <div key={part.id} style={{
                  position: 'absolute',
                  ...getPartTransform(part),
                  willChange: 'transform',
                }}>
                  <div style={{ position: 'relative' }}>
                    <img
                      src={part.img}
                      alt={part.label}
                      style={{
                        width: part.width,
                        height: part.height,
                        objectFit: 'cover',
                        borderRadius: 10,
                        border: showExploded && progress > 0.3
                          ? `1px solid ${part.color}40`
                          : '1px solid transparent',
                        transition: 'border-color 0.3s',
                        display: 'block',
                      }}
                    />
                    {/* label */}
                    <div style={{
                      position: 'absolute',
                      bottom: -34,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      opacity: labelOpacity,
                      textAlign: 'center',
                      whiteSpace: 'nowrap',
                      pointerEvents: 'none',
                      transition: 'opacity 0.3s',
                    }}>
                      <div style={{
                        fontSize: 11, fontWeight: 600,
                        color: part.color,
                        fontFamily: 'Tahoma, Arial',
                        direction: 'rtl',
                        textShadow: '0 0 10px rgba(0,0,0,0.8)',
                      }}>{part.label}</div>
                      <div style={{
                        fontSize: 9,
                        color: 'rgba(255,255,255,0.3)',
                        fontFamily: 'monospace',
                        marginTop: 1,
                      }}>{part.spec}</div>
                    </div>
                  </div>
                </div>
              ))}

              {/* دوربین SVG مونتاژ شده — زیر قطعات */}
              <div style={{
                opacity: assembledFull ? 1 : Math.max(0, 1 - progress * 3),
                transition: assembledFull ? 'opacity 1s' : 'opacity 0.3s',
                position: 'relative',
                zIndex: 10,
              }}>
                <AssembledCamera ledOn={ledOn} glowIntensity={glowIntensity} />
              </div>
            </div>

            {/* ring progress */}
            <svg style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              opacity: 0.25,
            }}>
              <circle
                cx="50%" cy="50%"
                r="180"
                fill="none"
                stroke="rgba(255,165,0,0.12)"
                strokeWidth="1"
              />
              <circle
                cx="50%" cy="50%"
                r="180"
                fill="none"
                stroke="rgba(255,165,0,0.6)"
                strokeWidth="1"
                strokeDasharray={`${progress * 1131} 1131`}
                strokeLinecap="round"
                transform="rotate(-90, 50%, 50%)"
              />
            </svg>
          </div>

          {/* ── راست: متن ── */}
          <div style={{
            width: 380,
            flexShrink: 0,
            direction: 'rtl',
          }}>
            {/* badge */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 7,
              background: 'rgba(255,165,0,0.07)',
              border: '0.5px solid rgba(255,165,0,0.22)',
              borderRadius: 20,
              padding: '5px 14px',
              marginBottom: 24,
            }}>
              <div style={{
                width: 7, height: 7,
                borderRadius: '50%',
                background: ledOn ? '#FFB347' : '#ffa500',
                boxShadow: ledOn ? '0 0 8px #FFB347' : 'none',
                animation: 'pulse 2s infinite',
              }}/>
              <span style={{
                fontSize: 11,
                color: 'rgba(255,165,0,0.85)',
                letterSpacing: '1.5px',
                fontFamily: 'Tahoma',
              }}>واردکننده مستقیم از چین</span>
            </div>

            <h1 style={{
              fontSize: 46,
              fontWeight: 800,
              color: '#fff',
              lineHeight: 1.2,
              marginBottom: 18,
              fontFamily: 'Tahoma, Arial',
            }}>
              قطعات{' '}
              <span style={{ color: '#ffa500' }}>دوربین</span>
              <br/>مداربسته
            </h1>

            {/* متن دینامیک */}
            <p style={{
              fontSize: 14,
              color: 'rgba(255,255,255,0.38)',
              lineHeight: 1.9,
              marginBottom: 28,
              fontFamily: 'Tahoma',
              minHeight: 54,
              transition: 'all 0.4s',
            }}>
              {assembledFull || progress < 0.05
                ? 'تامین مستقیم از کارخانه — بهترین قیمت بازار — ضمانت اصالت کالا'
                : progress < 0.5
                ? 'اسکرول کنید و ساختار داخلی دوربین را کشف کنید...'
                : 'قطعات در حال مونتاژ — از سنسور تا لنز و LED...'}
            </p>

            {/* part badges */}
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 7,
              marginBottom: 30,
            }}>
              {PARTS.map((part, i) => {
                const active = progress > i * 0.16 || assembledFull
                return (
                  <div key={part.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    background: active ? `${part.color}12` : 'rgba(255,255,255,0.03)',
                    border: `0.5px solid ${active ? part.color + '35' : 'rgba(255,255,255,0.07)'}`,
                    borderRadius: 6,
                    padding: '4px 10px',
                    transition: 'all 0.4s',
                  }}>
                    <div style={{
                      width: 5, height: 5,
                      borderRadius: '50%',
                      background: active ? part.color : 'rgba(255,255,255,0.18)',
                      transition: 'background 0.4s',
                    }}/>
                    <span style={{
                      fontSize: 10,
                      color: active ? part.color : 'rgba(255,255,255,0.2)',
                      fontFamily: 'Tahoma',
                      direction: 'rtl',
                      transition: 'color 0.4s',
                    }}>{part.label}</span>
                  </div>
                )
              })}
            </div>

            {/* LED indicator */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              marginBottom: 28,
              opacity: assembledFull ? 1 : 0.3,
              transition: 'opacity 0.8s',
            }}>
              <div style={{
                width: 10, height: 10,
                borderRadius: '50%',
                background: ledOn ? '#FFB347' : '#333',
                boxShadow: ledOn ? '0 0 12px #FFB347, 0 0 24px rgba(255,180,70,0.4)' : 'none',
                transition: 'all 0.2s',
              }}/>
              <span style={{
                fontSize: 11,
                color: ledOn ? '#FFB347' : 'rgba(255,255,255,0.25)',
                fontFamily: 'Tahoma',
                transition: 'color 0.3s',
              }}>
                {ledOn ? 'Warm LED روشن است' : 'منتظر مونتاژ کامل...'}
              </span>
            </div>

            {/* CTAs */}
            <div style={{ display: 'flex', gap: 12 }}>
              <a href="/products" style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                background: '#ffa500',
                color: '#000',
                textDecoration: 'none',
                borderRadius: 10,
                padding: '13px 26px',
                fontSize: 14,
                fontWeight: 700,
                fontFamily: 'Tahoma',
                boxShadow: ledOn ? '0 0 20px rgba(255,165,0,0.3)' : 'none',
                transition: 'box-shadow 0.3s',
              }}>
                مشاهده محصولات
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke="#000" strokeWidth="2.5" strokeLinecap="round"/>
                </svg>
              </a>
              <a href="/china-order" style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                background: 'transparent',
                color: 'rgba(255,255,255,0.45)',
                textDecoration: 'none',
                border: '0.5px solid rgba(255,255,255,0.1)',
                borderRadius: 10,
                padding: '13px 22px',
                fontSize: 14,
                fontFamily: 'Tahoma',
              }}>سفارش از چین</a>
            </div>

            {/* scroll hint */}
            {progress < 0.04 && (
              <div style={{
                marginTop: 36,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                color: 'rgba(255,255,255,0.18)',
                fontSize: 11,
                fontFamily: 'Tahoma',
              }}>
                <div style={{
                  width: 22, height: 36,
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: 11,
                  display: 'flex',
                  justifyContent: 'center',
                  paddingTop: 5,
                }}>
                  <div style={{
                    width: 2, height: 7,
                    background: '#ffa500',
                    borderRadius: 1,
                    animation: 'scrollWheel 1.5s infinite',
                  }}/>
                </div>
                اسکرول کنید — دوربین منفجر می‌شود
              </div>
            )}
          </div>
        </div>

        {/* ── نوار پایین stats ── */}
        <div style={{
          position: 'absolute',
          bottom: 0, left: 0, right: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
          borderTop: '0.5px solid rgba(255,255,255,0.05)',
          padding: '12px 60px',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          direction: 'rtl',
        }}>
          {[
            { val: '+۲۰۰۰', lbl: 'نوع قطعه', icon: '📦' },
            { val: '۱۰ sal', lbl: 'سابقه فعالیت', icon: '🏆' },
            { val: '۴۸h', lbl: 'تحویل اکسپرس', icon: '🚀' },
            { val: '۱۰۰٪', lbl: 'ضمانت اصالت', icon: '✅' },
          ].map((s, i) => (
            <div key={i} style={{
              textAlign: 'center',
              borderLeft: i < 3 ? '0.5px solid rgba(255,255,255,0.05)' : 'none',
              padding: '4px 0',
            }}>
              <div style={{
                fontSize: 19,
                fontWeight: 700,
                color: '#ffa500',
                fontFamily: 'monospace',
                letterSpacing: '1px',
              }}>{s.val}</div>
              <div style={{
                fontSize: 10,
                color: 'rgba(255,255,255,0.22)',
                fontFamily: 'Tahoma',
                marginTop: 1,
              }}>{s.lbl}</div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%,100%{opacity:1;transform:scale(1)}
          50%{opacity:0.4;transform:scale(0.85)}
        }
        @keyframes scrollWheel {
          0%{transform:translateY(0);opacity:1}
          100%{transform:translateY(12px);opacity:0}
        }
      `}</style>
    </section>
  )
}
