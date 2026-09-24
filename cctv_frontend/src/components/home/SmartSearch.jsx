import { useState, useRef, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { createPortal } from 'react-dom'
import api from '../../services/api'
import useAuthStore from '../../store/useAuthStore'
import { useAfterLoad } from '../../hooks/useAfterLoad'

// نام موتورها برای نمایش به ادمین
const ENGINE_NAMES = {
  gemini: 'Gemini', modelscope: 'ModelScope Qwen3', zai: 'z.ai GLM', deepseek: 'DeepSeek', qwen: 'Qwen لوکال',
}

// ─── هوک ارتفاع خودکار تکست‌اریا ──────────────────────────────
function useAutoResizeTextarea(minHeight = 26, maxHeight = 150) {
  const ref = useRef(null)
  const adjust = useCallback((reset) => {
    const el = ref.current
    if (!el) return
    el.style.height = `${minHeight}px`
    if (!reset) el.style.height = `${Math.max(minHeight, Math.min(el.scrollHeight, maxHeight))}px`
  }, [minHeight, maxHeight])
  return [ref, adjust]
}

// ─── سه نقطه «در حال فکر کردن» ────────────────────────────────
function TypingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 4, marginRight: 6, verticalAlign: 'middle' }}>
      {[0, 1, 2].map((i) => (
        <span key={i} className="chat-typing-dot" style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </span>
  )
}

// ─── صورت ربات (مثل ماسکات Kimi ولی با طلایی سایت) ────────────
// حالت‌ها: idle | listening (دارد به سوال گوش می‌دهد) | thinking | happy
function BotFace({ size = 40, state = 'idle' }) {
  return (
    <span className={`bot-face bot-face-${state}`} style={{ width: size, height: size, flexShrink: 0 }}>
      <span className="bot-eye" />
      <span className="bot-eye" />
    </span>
  )
}

// ─── سوالات نمونه برای placeholder تایپ‌شونده ─────────────────
const SAMPLE_QUESTIONS = [
  'برد ۵ مگاپیکسل ip ارزان کدام است؟',
  'لنز دارک لایت چی داری؟',
  'لنز ۲.۸ استارلایت داری؟',
  'کدام بردها را برای پلاک خوانی می توانم استفاده کنم؟',
]

// تایپ حروف‌به‌حروف، مکث، پاک‌کردن و رفتن سراغ سوال بعدی
// فقط وقتی active است (هیرو در دید + تب visible) کار می‌کند و شروع اولیه‌اش به
// فرصت خلوت main-thread موکول می‌شود — وگرنه هر ۵۵ms یک رندر React در پنجره بوت می‌ساخت
function useTypewriter(phrases, active, typeSpeed = 55, deleteSpeed = 22, holdMs = 2100) {
  const [text, setText] = useState('')
  useEffect(() => {
    if (!active) return
    let phrase = 0
    let char = 0
    let deleting = false
    let timer
    const tick = () => {
      const full = phrases[phrase]
      if (!deleting) {
        char += 1
        setText(full.slice(0, char))
        if (char === full.length) {
          deleting = true
          timer = setTimeout(tick, holdMs)
          return
        }
        timer = setTimeout(tick, typeSpeed)
      } else {
        char -= 1
        setText(full.slice(0, char))
        if (char === 0) {
          deleting = false
          phrase = (phrase + 1) % phrases.length
          timer = setTimeout(tick, 450)
          return
        }
        timer = setTimeout(tick, deleteSpeed)
      }
    }
    const ric = window.requestIdleCallback || ((cb) => setTimeout(cb, 900))
    const idleId = ric(() => { timer = setTimeout(tick, 300) }, { timeout: 2200 })
    return () => { clearTimeout(timer); if (window.cancelIdleCallback) cancelIdleCallback(idleId) }
  }, [active])
  return text
}

// ═══════════════════════════════════════════════════════════════
// SmartSearch — باکس پرسش از دستیار هوشمند در هیرو
// ظاهر PromptInput (21st.dev): باکس ساده که با فوکوس باز می‌شود و
// پاسخ زیر سوال نمایش داده می‌شود — منطق دقیقاً همان ChatWidget
// (POST /assistant/chat/ با history) است.
// ═══════════════════════════════════════════════════════════════
export default function SmartSearch() {
  const isAdmin = useAuthStore(s => s.isAdmin)
  const [engineName, setEngineName] = useState('')  // موتور اصلی — فقط برای ادمین
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [started, setStarted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [focused, setFocused] = useState(false)
  const [justAnswered, setJustAnswered] = useState(false)
  const [textareaRef, adjustHeight] = useAutoResizeTextarea(24, 200)
  const bottomRef = useRef(null)

  // حالت ربات: فکرکردن > خوشحالی از جواب > گوش‌دادن به تایپ مشتری > عادی
  const botState = loading ? 'thinking' : justAnswered ? 'happy' : (input.trim() || focused) ? 'listening' : 'idle'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages, loading])

  // موتور اصلی ربات — فقط برای ادمین، یک بار در لود
  useEffect(() => {
    if (!isAdmin()) return
    api.get('/assistant/settings/')
      .then(({ data }) => setEngineName(ENGINE_NAMES[data.provider] || ''))
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setStarted(true)
    setInput('')
    adjustHeight(true)
    setLoading(true)
    try {
      const { data } = await api.post('/assistant/chat/', {
        message: text,
        history: next.slice(-7, -1),
      }, { timeout: 130000 })
      setMessages((m) => [...m, { role: 'assistant', content: data.reply, products: data.products, engine: data.engine, elapsed: data.elapsed }])
      setJustAnswered(true)
      setTimeout(() => setJustAnswered(false), 2600)
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: 'متأسفم، الان نتوانستم پاسخ بدهم. کمی بعد دوباره تلاش کنید.' }])
    } finally {
      setLoading(false)
    }
  }

  // ─── پرواز اسکرول‌محور ربات به سمت چت‌باکس ───
  // حرکت با میزان اسکرول جلو می‌رود (نه با زمان)، با برگرداندن اسکرول ربات هم برمی‌گردد سر جایش
  const frameRef = useRef(null)
  const flyerRef = useRef(null)
  const phaseRef = useRef('idle') // idle | fly | home
  const startRef = useRef(null)
  const posRef = useRef({ x: 0, y: 0 })
  const rafRef = useRef(null)
  const timersRef = useRef([])
  const originRef = useRef({ x: 0, y: 0 })
  const pSmoothRef = useRef(0)
  const reenterRef = useRef(false) // بعد از خروج از خانه تا پایین آمدن پله‌ها اجازه ورود دوباره نیست
  const exitingRef = useRef(false) // وقتی ربات دارد از در بیرون می‌آید، سر جای در می‌ماند
  const catchupUntilRef = useRef(0) // نیم ثانیه بعد از خروج از در، جبران فاصله سریع‌تر و بدون پرش است
  const [origin, setOrigin] = useState(null)
  const [botAway, setBotAway] = useState(false)
  const [showFlyer, setShowFlyer] = useState(false)
  const [entering, setEntering] = useState(false)
  const [exiting, setExiting] = useState(false)
  const [showDoor, setShowDoor] = useState(false)
  const [doorPos, setDoorPos] = useState({ x: 0, y: 0 })
  const [showBubble, setShowBubble] = useState(false)
  const [landing, setLanding] = useState(false)
  const landingAtRef = useRef(0)

  // تایپ‌زن placeholder فقط وقتی هیرو در دید و تب visible است فعال می‌شود
  const [heroActive, setHeroActive] = useState(false)
  useEffect(() => {
    const el = frameRef.current
    if (!el) return
    let seen = false
    const apply = () => setHeroActive(seen && !document.hidden)
    const io = new IntersectionObserver((es) => { seen = es[0].isIntersecting; apply() }, { threshold: 0.05 })
    io.observe(el)
    document.addEventListener('visibilitychange', apply)
    return () => { io.disconnect(); document.removeEventListener('visibilitychange', apply) }
  }, [])
  const afterLoad = useAfterLoad()
  const typedPlaceholder = useTypewriter(SAMPLE_QUESTIONS, heroActive && afterLoad)

  useEffect(() => { exitingRef.current = exiting }, [exiting])

  useEffect(() => {
    const clearTimers = () => { timersRef.current.forEach(clearTimeout); timersRef.current = [] }
    const later = (fn, ms) => timersRef.current.push(setTimeout(fn, ms))

    const tick = () => {
      rafRef.current = null
      const el = frameRef.current
      const fab = document.getElementById('chat-fab')
      if (!el || !fab) return
      const bot = el.querySelector('.bot-face')
      if (!bot) return
      const f = fab.getBoundingClientRect()
      const b = bot.getBoundingClientRect()
      const fx = f.left + f.width / 2
      const fy = f.top + f.height / 2

      if (phaseRef.current === 'idle') {
        // شروع زودتر — وقتی ربات هنوز در تصویر است و به بالای صفحه رسید
        if (b.top < 120) {
          phaseRef.current = 'fly'
          startRef.current = { x: b.left + b.width / 2, y: b.top + b.height / 2, scroll: window.scrollY }
          posRef.current = { x: startRef.current.x, y: startRef.current.y }
          originRef.current = { ...posRef.current }
          pSmoothRef.current = 0
          setOrigin({ ...posRef.current })
          clearTimers()
          setLanding(false)
          setBotAway(true); setShowFlyer(true); setEntering(false); setExiting(false); setShowDoor(false); setShowBubble(false)
        } else {
          return
        }
      }

      const start = startRef.current
      // ربات باید تا قبل از رسیدن اسکرول به سکشن «چرا باید با ما کار کنید» به خانه رسیده باشد
      const anchor = document.getElementById('why-us')
      let total
      if (anchor) {
        const anchorPageY = anchor.getBoundingClientRect().top + window.scrollY
        const targetScroll = Math.max(0, anchorPageY - window.innerHeight)
        total = Math.max(300, targetScroll - start.scroll)
      } else {
        const gap = Math.abs(start.y - fy)
        const remaining = Math.max(400, document.documentElement.scrollHeight - window.innerHeight - start.scroll)
        total = Math.max(gap + 100, remaining * 0.85)
      }
      const p = Math.min(1, Math.max(0, (window.scrollY - start.scroll) / total))
      // کوانتیزه کردن مسیر به ۶ پله — ربات شش هاپ کوچک و نرم طی می‌کند
      const STEPS = 6
      const pq = Math.min(STEPS, Math.max(0, Math.round(p * STEPS))) / STEPS
      // هموارسازی پیشرفت — هر پله با انیمیشن نرم طی می‌شود
      pSmoothRef.current += (pq - pSmoothRef.current) * 0.1
      const ps = pSmoothRef.current
      const e = ps * ps * (3 - 2 * ps) // smoothstep — شروع و پایان نرم
      // نوسان ملایم روی مسیر — حس شناور و غیرمستقیم بودن حرکت
      const swayX = Math.sin(ps * Math.PI * 2) * 16 * (1 - ps)
      const swayY = Math.sin(ps * Math.PI * 3) * 26 * (1 - ps)
      let tx = start.x + (fx - start.x) * e + swayX
      let ty = start.y + (fy - start.y) * e + swayY
      if (exitingRef.current) {
        // ربات کنار در می‌ماند تا انیمیشن خروج تمام شود — وگرنه در پایان انیمیشن پرش دارد
        tx = fx; ty = fy
      }
      const bx = b.left + b.width / 2
      const by = b.top + b.height / 2
      if (ps < 0.2 || phaseRef.current === 'landing') {
        // نزدیک جایگاه (مسیر برگشت): ربات به‌تدریج روی جای واقعی‌اش در کادر می‌نشیند —
        // بدون اینکه اول بالاتر از جایش برود؛ هنگام تحویل کاملاً قفل می‌شود
        const k = phaseRef.current === 'landing' ? 1 : 1 - ps / 0.2
        tx += (bx - tx) * k
        ty += (by - ty) * k
      }
      // تعقیب نرم هدف — حس شناور و آروم بودن؛ کمی پس از خروج از در موقتاً تندتر تا فاصله بدون پرش جبران شود
      const follow = performance.now() < catchupUntilRef.current ? 0.3 : 0.12
      posRef.current.x += (tx - posRef.current.x) * follow
      posRef.current.y += (ty - posRef.current.y) * follow
      const fl = flyerRef.current
      if (fl && phaseRef.current === 'fly') {
        // حرکت با transform — رندر GPU-محور و بدون پله
        const tilt = Math.max(-12, Math.min(12, (ty - posRef.current.y) * 0.35))
        fl.style.transform = `translate(-50%, -50%) translate3d(${posRef.current.x - originRef.current.x}px, ${posRef.current.y - originRef.current.y}px, 0) rotate(${tilt}deg)`
      }
      const near = Math.abs(posRef.current.x - fx) + Math.abs(posRef.current.y - fy)

      // وقتی ربات از پله‌ی آخر پایین آمده، دوباره حق ورود به خانه را دارد
      if (ps < 0.85) reenterRef.current = false

      if (ps >= 0.99 && !reenterRef.current && phaseRef.current === 'fly' && near < 10) {
        // رسید به خانه: درِ نماد چت باز می‌شود و ربات داخل می‌رود
        phaseRef.current = 'home'
        originRef.current = { x: posRef.current.x, y: posRef.current.y }
        setOrigin({ ...posRef.current })
        if (flyerRef.current) flyerRef.current.style.transform = ''
        setDoorPos({ x: fx, y: fy })
        setEntering(true); setShowDoor(true)
        later(() => { setShowFlyer(false); setEntering(false) }, 900)
        later(() => { setShowDoor(false); setShowBubble(true) }, 1150)
        later(() => setShowBubble(false), 6800)
      } else if (p < 0.98 && phaseRef.current === 'home') {
        // اسکرول به بالا: در باز می‌شود، ربات از خانه بیرون می‌آید و برمی‌گردد
        phaseRef.current = 'fly'
        clearTimers()
        // قفل ورود دوباره تا پایین آمدن از پله‌ی آخر — وگرنه در دوباره باز می‌شود
        reenterRef.current = true
        originRef.current = { x: fx, y: fy }
        setOrigin({ x: fx, y: fy })
        if (flyerRef.current) flyerRef.current.style.transform = ''
        setDoorPos({ x: fx, y: fy })
        setEntering(false); setShowBubble(false); setShowDoor(true); setShowFlyer(true); setExiting(true); setLanding(false)
        later(() => { setExiting(false); catchupUntilRef.current = performance.now() + 550 }, 750)
        later(() => setShowDoor(false), 850)
      }

      // نزدیک جایگاه → شروع تحویل نرم: صورت اصلی کم‌رنگ می‌آید، فلایر روی آن محو می‌گردد
      if (b.top > 120 && ps <= 0.02 && phaseRef.current === 'fly') {
        phaseRef.current = 'landing'
        landingAtRef.current = Date.now()
        setLanding(true)
        setBotAway(false)
      }

      if (phaseRef.current === 'landing') {
        // اگر کاربر دوباره پایین رفت، تحویل لغو و ربات به پرواز برمی‌گردد
        if (p > 0.08) {
          phaseRef.current = 'fly'
          setLanding(false)
          setBotAway(true)
        } else {
          const d = Math.abs(posRef.current.x - bx) + Math.abs(posRef.current.y - by)
          if (d < 4 || Date.now() - landingAtRef.current > 450) {
            phaseRef.current = 'idle'
            reenterRef.current = false
            setOrigin(null)
            setLanding(false); setShowFlyer(false); setEntering(false); setExiting(false); setShowDoor(false); setShowBubble(false)
            return
          }
        }
      }

      // حلقه تعقیب نرم در پرواز و تحویل ادامه دارد
      if (phaseRef.current === 'fly' || phaseRef.current === 'landing') rafRef.current = requestAnimationFrame(tick)
    }

    const onScroll = () => {
      if (rafRef.current == null) rafRef.current = requestAnimationFrame(tick)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
      clearTimers()
    }
  }, [])

  return (
    <>
    <div ref={frameRef} className={`liquid-metal-frame${botAway ? ' bot-away' : ''}`} style={{ boxShadow: 'var(--shadow-card-hover), 0 0 60px rgba(251,192,45,0.10)' }}>
    <div className="liquid-metal-inner">
      {/* ناحیه گفتگو — پاسخ زیر سوال، مثل دستیار هوشمند سایت */}
      {started && (
        <div style={{ maxHeight: 340, overflowY: 'auto', padding: '16px 16px 6px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {messages.map((m, i) => (
            <div key={i} style={{ textAlign: m.role === 'user' ? 'right' : 'left' }}>
              <div
                className="inline-block px-3 py-2 rounded-xl text-xs leading-6 whitespace-pre-wrap"
                style={{
                  maxWidth: '88%',
                  background: m.role === 'user' ? 'var(--gradient-gold)' : 'var(--color-bg-secondary)',
                  color: m.role === 'user' ? 'var(--color-brand-contrast)' : 'var(--color-text-primary)',
                  border: m.role === 'user' ? 'none' : '1px solid var(--color-border)',
                  textAlign: 'right',
                }}
              >
                {m.content}
              </div>
              {/* نشان موتور پاسخ — خوانا و ثابت زیر جواب، فقط برای ادمین */}
              {isAdmin() && m.role === 'assistant' && m.engine && (
                <div className="mt-1" style={{ textAlign: 'left' }}>
                  <span className="inline-block text-[11px] font-semibold px-2.5 py-1 rounded-lg"
                    style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-brand)', color: 'var(--color-brand)' }}>
                    {m.engine === 'rules'
                      ? '⚙️ پاسخ آماده'
                      : `${ENGINE_NAMES[m.engine] || m.engine}${m.elapsed != null ? ` — ${Number(m.elapsed).toLocaleString('fa-IR')} ثانیه` : ''}`}
                  </span>
                </div>
              )}
              {m.products?.length > 0 && (
                <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {m.products.slice(0, 4).map((p, j) => (
                    <Link
                      key={j}
                      to={p.url}
                      className="block px-3 py-1.5 rounded-lg text-xs"
                      style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', textDecoration: 'none' }}
                    >
                      {/* نام و قیمت در دو خط جدا — مدل لاتین وسط متن فارسی چیدمان RTL را به‌هم می‌ریزد */}
                      <div>📷 {p.name}</div>
                      <div style={{ marginTop: 2, color: 'var(--color-brand)', fontWeight: 700 }}>
                        {p.price_irt ? `${Number(p.price_irt).toLocaleString('fa-IR')} ریال` : ''}
                        {!p.in_stock && <span style={{ color: '#e74c3c', fontWeight: 400 }}> (ناموجود)</span>}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* باکس ورودی — با فوکوس بزرگ‌تر می‌شود؛ گوی ربات بالا می‌ماند */}
      <div
        className="smart-input-wrap"
        style={{
          display: 'flex', alignItems: 'flex-start', gap: 10,
          padding: '8px 12px',
          borderTop: started ? '1px solid var(--color-border)' : 'none',
          transition: 'box-shadow 0.25s ease',
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); adjustHeight() }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          rows={1}
          placeholder={started ? 'سوال بعدی‌ات را بنویس...' : typedPlaceholder}
          style={{
            flex: 1, alignSelf: 'center', minHeight: focused ? 156 : 24, maxHeight: 200,
            resize: 'none', overflow: 'hidden',
            background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--color-text-primary)', fontSize: 14, lineHeight: 1.9,
            fontFamily: 'inherit',
            transition: 'min-height 0.2s ease',
          }}
        />
        <div style={{ position: 'relative', flexShrink: 0 }}>
          {/* حباب فکر — از سر ربات بیرون می‌زند؛ برای ادمین نام موتور را نشان می‌دهد */}
          {loading && (
            <span className="bot-thought">
              {isAdmin() && engineName ? `${engineName} دارد جواب می‌دهد` : 'در حال فکر کردن'}<TypingDots />
            </span>
          )}
          <button
            type="button"
            onClick={send}
            disabled={!input.trim() || loading}
            aria-label="ارسال"
            style={{
              background: 'transparent', border: 'none', padding: 0, cursor: 'pointer',
              opacity: (!input.trim() || loading) ? 0.85 : 1,
              transition: 'opacity 0.2s, transform 0.15s',
            }}
          >
            <BotFace size={40} state={botState} />
          </button>
        </div>
      </div>
    </div>
    </div>
    {showFlyer && createPortal(
      <div ref={flyerRef} className={`bot-flyer${entering ? ' entering' : ''}${exiting ? ' exiting' : ''}${landing ? ' landing' : ''}`}
        style={{ left: origin ? origin.x : posRef.current.x, top: origin ? origin.y : posRef.current.y }}>
        <span className="bot-face" style={{ width: 36, height: 36 }}>
          <span className="bot-eye" />
          <span className="bot-eye" />
        </span>
      </div>,
      document.body
    )}
    {showDoor && createPortal(
      <div className="bot-door" style={{ left: doorPos.x, top: doorPos.y }}>
        <span className="bot-door-panel" />
      </div>,
      document.body
    )}
    {showBubble && createPortal(
      <div className="bot-home-bubble" style={{ left: doorPos.x + 16, top: doorPos.y }}>
        هر سوالی داشتی من اینجا باهاتم
      </div>,
      document.body
    )}
    </>
  )
}
