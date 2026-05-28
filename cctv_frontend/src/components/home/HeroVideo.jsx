import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

export default function HeroVideo() {
  const sectionRef = useRef(null)
  const videoRef   = useRef(null)
  const [progress, setProgress]   = useState(0)
  const [ready, setReady]         = useState(false)
  const [duration, setDuration]   = useState(0)
  const targetRef  = useRef(0)
  const currentRef = useRef(0)
  const rafRef     = useRef(null)

  // لود ویدیو
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.preload = 'auto'
    v.muted   = true
    v.load()
    const onLoaded = () => {
      setDuration(v.duration)
      setReady(true)
      v.currentTime = 0
    }
    v.addEventListener('loadeddata', onLoaded)
    return () => v.removeEventListener('loadeddata', onLoaded)
  }, [])

  // smooth scrub
  useEffect(() => {
    if (!ready) return
    const lerp = (a, b, t) => a + (b - a) * t
    const animate = () => {
      currentRef.current = lerp(currentRef.current, targetRef.current, 0.07)
      const v = videoRef.current
      if (v && Math.abs(v.currentTime - currentRef.current) > 0.01) {
        v.currentTime = currentRef.current
      }
      rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [ready])

  // scroll → ویدیو
  useEffect(() => {
    const onScroll = () => {
      if (!sectionRef.current || !duration) return
      const rect    = sectionRef.current.getBoundingClientRect()
      const total   = sectionRef.current.offsetHeight - window.innerHeight
      const scrolled = Math.max(0, -rect.top)
      const p = Math.max(0, Math.min(1, scrolled / total))
      setProgress(p)
      targetRef.current = p * duration
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [duration])

  const assembled  = progress >= 0.88
  const textOpacity = Math.max(0, 1 - progress * 0.8 + 0.2)

  const phases = [
    { at: 0,    text: '↓ اسکرول کنید — دوربین مونتاژ می‌شود', sub: 'SCROLL TO ASSEMBLE' },
    { at: 0.2,  text: 'قطعات داخلی',    sub: 'ISP | Sensor | Lens Module' },
    { at: 0.5,  text: 'مونتاژ بدنه',    sub: 'Aluminum Housing | IP67' },
    { at: 0.75, text: 'تنظیم نهایی',    sub: 'Calibration | Quality Check' },
    { at: 0.88, text: 'دوربین آماده است ✓', sub: '5MP | Starlight | Full Color Night Vision' },
  ]
  const currentPhase = [...phases].reverse().find(p => progress >= p.at) || phases[0]

  return (
    <section
      ref={sectionRef}
      style={{ position: 'relative', height: '500vh', background: '#000' }}
    >
      <div style={{
        position: 'sticky', top: 0,
        height: '100vh', width: '100%',
        overflow: 'hidden',
        background: '#050505',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>

        {/* ── grid ── */}
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.015) 1px,transparent 1px),' +
            'linear-gradient(90deg,rgba(255,255,255,0.015) 1px,transparent 1px)',
          backgroundSize: '60px 60px',
          pointerEvents: 'none',
        }}/>

        {/* ── ambient glow ── */}
        <div style={{
          position: 'absolute', inset: 0,
          background: `radial-gradient(ellipse at 50% 50%, rgba(255,140,0,${assembled ? 0.08 : 0.03}) 0%, transparent 65%)`,
          transition: 'all 1s', pointerEvents: 'none',
        }}/>

        {/* ── ویدیو hidden برای scrub ── */}
        <video
          ref={videoRef}
          src="/videos/hero_camera.mp4"
          muted playsInline preload="auto"
          style={{ display: 'none' }}
        />

        {/* ── canvas نمایش ویدیو ── */}
        <CanvasVideo videoRef={videoRef} ready={ready} />

        {/* ── progress bar ── */}
        <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:'rgba(255,255,255,0.04)', zIndex:30 }}>
          <div style={{
            height: '100%', width: `${progress * 100}%`,
            background: 'linear-gradient(90deg, #ff8c00, #ffd700)',
            boxShadow: '0 0 10px rgba(255,165,0,0.8)',
            transition: 'width 0.05s',
          }}/>
        </div>

        {/* ── متن راست ── */}
        <div style={{
          position: 'absolute', top: '50%', right: 80,
          transform: 'translateY(-50%)',
          direction: 'rtl', maxWidth: 380, zIndex: 20,
          opacity: textOpacity,
        }}>

          {/* phase indicators */}
          <div style={{ display:'flex', gap:4, marginBottom:20 }}>
            {phases.map((p,i) => (
              <div key={i} style={{
                height:2, flex:1, borderRadius:1,
                background: progress >= p.at ? '#ffa500' : 'rgba(255,255,255,0.08)',
                boxShadow: progress >= p.at ? '0 0 6px rgba(255,165,0,0.6)' : 'none',
                transition: 'background 0.3s',
              }}/>
            ))}
          </div>

          {/* badge */}
          <div style={{
            display:'inline-flex', alignItems:'center', gap:8,
            background:'rgba(255,165,0,0.08)',
            border:'0.5px solid rgba(255,165,0,0.28)',
            borderRadius:24, padding:'6px 16px', marginBottom:22,
          }}>
            <div style={{
              width:7, height:7, borderRadius:'50%',
              background: assembled ? '#00ff88' : '#ffa500',
              boxShadow: `0 0 10px ${assembled ? '#00ff88' : '#ffa500'}`,
              transition:'all 0.5s', animation:'pulse 2s infinite',
            }}/>
            <span style={{
              fontSize:11, letterSpacing:'1.5px', fontFamily:'Tahoma',
              color: assembled ? 'rgba(0,255,136,0.95)' : 'rgba(255,165,0,0.95)',
              transition:'color 0.5s',
            }}>
              {assembled ? 'دوربین آماده است ✓' : 'در حال مونتاژ...'}
            </span>
          </div>

          <h1 style={{
            fontSize:'clamp(28px,3.2vw,50px)',
            fontWeight:900, color:'#fff', lineHeight:1.15,
            marginBottom:16, fontFamily:'Tahoma, Arial',
          }}>
            قطعات{' '}
            <span style={{ color:'#ffa500', textShadow:'0 0 30px rgba(255,165,0,0.5)' }}>
              دوربین
            </span>
            <br/>مداربسته
          </h1>

          {/* متن دینامیک */}
          <div style={{ minHeight:50, marginBottom:20 }}>
            <div style={{ fontSize:14, color:'#ffa500', fontFamily:'Tahoma', fontWeight:600, marginBottom:5 }}>
              {currentPhase.text}
            </div>
            <div style={{ fontSize:10, color:'rgba(255,255,255,0.3)', fontFamily:'monospace', letterSpacing:'0.8px' }}>
              {currentPhase.sub}
            </div>
          </div>

          {/* progress */}
          {!assembled && (
            <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:24 }}>
              <div style={{ flex:1, height:2, background:'rgba(255,255,255,0.08)', borderRadius:1, overflow:'hidden' }}>
                <div style={{
                  height:'100%', width:`${progress*100}%`,
                  background:'linear-gradient(90deg,#ff8c00,#ffd700)',
                  borderRadius:1, transition:'width 0.05s',
                }}/>
              </div>
              <span style={{ fontSize:11, color:'rgba(255,255,255,0.3)', fontFamily:'monospace', direction:'ltr', minWidth:34 }}>
                {Math.round(progress*100)}%
              </span>
            </div>
          )}

          {/* دکمه‌ها */}
          <div style={{
            display:'flex', gap:12, flexWrap:'wrap',
            opacity: assembled ? 1 : 0.2,
            transform: assembled ? 'translateY(0)' : 'translateY(14px)',
            transition:'all 0.8s cubic-bezier(0.34,1.56,0.64,1)',
            pointerEvents: assembled ? 'auto' : 'none',
          }}>
            <Link to="/products" style={{
              display:'inline-flex', alignItems:'center', gap:8,
              background:'#ffa500', color:'#000',
              textDecoration:'none', borderRadius:12,
              padding:'14px 28px', fontSize:14, fontWeight:700, fontFamily:'Tahoma',
              boxShadow:'0 4px 28px rgba(255,165,0,0.5)',
            }}>
              مشاهده محصولات
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#000" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </Link>
            <Link to="/china-order" style={{
              display:'inline-flex', alignItems:'center',
              background:'rgba(255,255,255,0.06)',
              color:'rgba(255,255,255,0.75)',
              textDecoration:'none',
              border:'0.5px solid rgba(255,255,255,0.15)',
              borderRadius:12, padding:'14px 22px',
              fontSize:14, fontFamily:'Tahoma',
            }}>سفارش از چین</Link>
          </div>
        </div>

        {/* ── stats ── */}
        <div style={{
          position:'absolute', bottom:0, left:0, right:0,
          padding:'14px 80px',
          display:'grid', gridTemplateColumns:'repeat(4,1fr)',
          background:'rgba(0,0,0,0.75)',
          backdropFilter:'blur(20px)', WebkitBackdropFilter:'blur(20px)',
          borderTop:'0.5px solid rgba(255,255,255,0.05)',
          direction:'rtl', zIndex:20,
        }}>
          {[
            { val:'+۲۰۰۰', lbl:'نوع قطعه' },
            { val:'۱۰ sal', lbl:'سابقه فعالیت' },
            { val:'۴۸h',   lbl:'تحویل اکسپرس' },
            { val:'۱۰۰٪',  lbl:'ضمانت اصالت' },
          ].map((s,i) => (
            <div key={i} style={{
              textAlign:'center', padding:'6px 0',
              borderLeft: i>0 ? '0.5px solid rgba(255,255,255,0.05)' : 'none',
            }}>
              <div style={{ fontSize:20, fontWeight:700, color:'#ffa500', fontFamily:'monospace' }}>{s.val}</div>
              <div style={{ fontSize:10, color:'rgba(255,255,255,0.25)', fontFamily:'Tahoma', marginTop:2 }}>{s.lbl}</div>
            </div>
          ))}
        </div>

        {/* scroll hint */}
        {progress < 0.02 && (
          <div style={{
            position:'absolute', bottom:90, left:'50%',
            transform:'translateX(-50%)',
            display:'flex', flexDirection:'column',
            alignItems:'center', gap:8, zIndex:20,
          }}>
            <div style={{ fontSize:9, color:'rgba(255,255,255,0.3)', letterSpacing:'3px', fontFamily:'monospace' }}>
              SCROLL TO ASSEMBLE
            </div>
            <div style={{
              width:22, height:38,
              border:'1px solid rgba(255,165,0,0.25)',
              borderRadius:11,
              display:'flex', justifyContent:'center', paddingTop:5,
            }}>
              <div style={{ width:2, height:7, background:'#ffa500', borderRadius:1, animation:'scrollWheel 1.5s infinite' }}/>
            </div>
          </div>
        )}

        <style>{`
          @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
          @keyframes scrollWheel { 0%{transform:translateY(0);opacity:1} 100%{transform:translateY(12px);opacity:0} }
        `}</style>
      </div>
    </section>
  )
}

// ─── Canvas با حذف پس‌زمینه سفید (pixel manipulation) ────────
function CanvasVideo({ videoRef, ready }) {
  const canvasRef    = useRef(null)
  const offscreenRef = useRef(null)
  const rafRef       = useRef(null)

  useEffect(() => {
    if (!ready) return
    const canvas  = canvasRef.current
    const video   = videoRef.current
    if (!canvas || !video) return

    const draw = () => {
      const W = canvas.offsetWidth
      const H = canvas.offsetHeight
      const dpr = window.devicePixelRatio || 1

      if (canvas.width !== W * dpr || canvas.height !== H * dpr) {
        canvas.width  = W * dpr
        canvas.height = H * dpr
      }

      // ─── offscreen برای pixel manipulation ───────────────────
      if (!offscreenRef.current ||
          offscreenRef.current.width  !== canvas.width ||
          offscreenRef.current.height !== canvas.height) {
        offscreenRef.current = document.createElement('canvas')
        offscreenRef.current.width  = canvas.width
        offscreenRef.current.height = canvas.height
      }

      const off = offscreenRef.current
      const octx = off.getContext('2d')
      const W2 = off.width
      const H2 = off.height

      // رسم ویدیو با cover fit در offscreen
      const vr = video.videoWidth / video.videoHeight
      const cr = W2 / H2
      let sw, sh, sx, sy
      if (vr > cr) { sh = H2; sw = H2 * vr; sx = (W2 - sw)/2; sy = 0 }
      else          { sw = W2; sh = W2 / vr; sx = 0; sy = (H2 - sh)/2 }

      octx.clearRect(0, 0, W2, H2)
      octx.drawImage(video, sx, sy, sw, sh)

      // ─── حذف پس‌زمینه سفید/روشن با pixel manipulation ────────
      const imageData = octx.getImageData(0, 0, W2, H2)
      const data = imageData.data
      const THRESH = 210  // آستانه روشنایی برای حذف
      const FEATHER = 40  // نرمی لبه

      for (let i = 0; i < data.length; i += 4) {
        const r = data[i], g = data[i+1], b = data[i+2]
        // میانگین روشنایی
        const brightness = (r + g + b) / 3
        // اگر روشن باشد → شفاف
        if (brightness > THRESH) {
          data[i+3] = 0
        } else if (brightness > THRESH - FEATHER) {
          // لبه نرم
          data[i+3] = Math.round(255 * (1 - (brightness - (THRESH - FEATHER)) / FEATHER))
        }
      }
      octx.putImageData(imageData, 0, 0)

      // رسم offscreen در canvas اصلی
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, W2, H2)
      ctx.drawImage(off, 0, 0)

      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [ready, videoRef])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        // وسط صفحه — اندازه بزرگ برای معلق بودن
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '90%', height: '90%',
        opacity: ready ? 1 : 0,
        transition: 'opacity 1s',
        zIndex: 5,
        // سایه نارنجی دور دوربین
        filter: 'drop-shadow(0 0 30px rgba(255,140,0,0.2)) drop-shadow(0 0 80px rgba(255,140,0,0.1))',
      }}
    />
  )
}
