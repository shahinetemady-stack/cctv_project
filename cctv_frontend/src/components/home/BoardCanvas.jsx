import { useEffect, useRef } from 'react'
import { isLowPower } from '../../utils/lowPower'

// ─── ابزارهای کوچک (پورت از cover.js مرجع) ──────────────────────
const TAU = Math.PI * 2
const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

function makeRng(seed) {
  let s = seed >>> 0
  return () => {
    s += 0x6d2b79f5; let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// ═══════════════════════════════════════════════════════════════
// BoardCanvas — افکت «بردی که خودش را می‌سازد»
// زوم بی‌نهایت بازگشتی: یک ماسک ۱۹×۱۹ (دای سیلیکون با پین) از مرکز
// به‌صورت سلولی رشد می‌کند؛ دوربین مدام زوم‌اوت می‌کند و دای فعلی به
// سلول مرکزی دای بزرگ‌تر تبدیل می‌شود. رنگ‌ها از توکن‌های تم سایت
// خوانده می‌شوند (دارک/لایت خودکار).
// ═══════════════════════════════════════════════════════════════
export default function BoardCanvas() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    // روی دستگاه‌های کم‌توان حلقه انیمیشن اجرا نمی‌شود — یک فریم ثابت از
    // فاز کامل‌شده رسم می‌شود تا main-thread برای لود و اسکرول آزاد بماند
    const reduced = isLowPower()
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
    const ctx = canvas.getContext('2d')
    ctx.imageSmoothingQuality = 'high'

    const fit = () => {
      const r = canvas.getBoundingClientRect()
      canvas.width = Math.round(r.width * dpr)
      canvas.height = Math.round(r.height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      return { w: r.width, h: r.height }
    }
    let view = fit()
    let lastW = Math.round(view.w)

    // ─── پالت از روی تم سایت ───
    let theme = null
    const readTheme = () => {
      const cs = getComputedStyle(document.documentElement)
      const light = document.documentElement.dataset.theme === 'light'
      const bg = cs.getPropertyValue('--color-bg-primary').trim() || (light ? '#FAF8F3' : '#0A0A0B')
      const brand = cs.getPropertyValue('--color-brand').trim() || (light ? '#A16207' : '#FBC02D')
      const muted = cs.getPropertyValue('--color-text-muted').trim() || (light ? '#8595a6' : '#8B8B93')
      theme = {
        light, bg, brand, muted,
        // تایل‌های مدار انتزاعی (فقط تا لود عکس بردها دیده می‌شوند)
        tileBg: light
          ? ['#f1f5fe', '#eef3fd', '#f4f7ff', '#edf2fc']
          : ['#141416', '#17171a', '#121215', '#1a1a1e'],
        solidBg: light
          ? ['#dfe7fb', '#d7e1fa', '#e4eafc', '#dbe4ff']
          : ['#1c1c20', '#202024', '#1a1a1e', '#222227'],
        dot: light ? '#c6cfdd' : 'rgba(255,255,255,.28)',
      }
      buildAbstractTiles()
    }

    // ─── rng قطعی ───
    const rng = makeRng(0x51C0FEE1)

    // ─── ۱) ماسک دای روی گرید ۱۹×۱۹ ───
    const G = 19, C = 9
    const inMask = (x, y) => {
      if (x >= 3 && x <= 15 && y >= 3 && y <= 15) {
        const cornerX = (x === 3 || x === 15), cornerY = (y === 3 || y === 15)
        return !(cornerX && cornerY)
      }
      const pins = [5, 7, 9, 11, 13]
      if ((y === 2 || y === 16) && pins.includes(x)) return true
      if ((x === 2 || x === 16) && pins.includes(y)) return true
      return false
    }
    const idxOf = (x, y) => y * G + x
    const inSet = new Set()
    for (let y = 0; y < G; y++) for (let x = 0; x < G; x++) {
      if (inMask(x, y)) inSet.add(idxOf(x, y))
    }
    const N = inSet.size

    // ─── ۲) ترتیب رشد: BFS از مرکز با جلوه تصادفی ───
    const birthOrder = (() => {
      const seen = new Set([idxOf(C, C)])
      const order = [idxOf(C, C)]
      let frontier = [idxOf(C, C)]
      while (order.length < N) {
        const next = []
        for (const i of frontier) {
          const x = i % G, y = (i / G) | 0
          for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
            const nx = x + dx, ny = y + dy
            if (nx < 0 || ny < 0 || nx >= G || ny >= G) continue
            const j = idxOf(nx, ny)
            if (inSet.has(j) && !seen.has(j)) { seen.add(j); next.push(j) }
          }
        }
        next.sort(() => rng() - 0.5)
        order.push(...next)
        frontier = next
        if (!next.length) break
      }
      return order
    })()

    // ─── ۳) تایل‌های مدار انتزاعی پیش‌رندر (۱۲ واریانت) ───
    let TILES = [], SOLIDS = []
    function makeTile(seed) {
      const r = makeRng(9301 * seed + 49297)
      const c = document.createElement('canvas')
      c.width = c.height = 128
      const a = c.getContext('2d')
      a.fillStyle = theme.tileBg[(r() * theme.tileBg.length) | 0]
      a.fillRect(0, 0, 128, 128)
      for (let k = 0; k < 2; k++) {
        const gx = 128 * r(), gy = 128 * r(), rad = 128 * (0.3 + 0.3 * r())
        const g = a.createRadialGradient(gx, gy, 0, gx, gy, rad)
        g.addColorStop(0, theme.brandGlow); g.addColorStop(1, 'rgba(0,0,0,0)')
        a.fillStyle = g; a.fillRect(0, 0, 128, 128)
      }
      a.globalAlpha = 0.05
      for (let k = 0; k < 130; k++) {
        a.fillStyle = k % 3 ? theme.brand : theme.muted
        const s = 1 + 2 * r()
        a.fillRect(128 * r(), 128 * r(), s, s)
      }
      a.globalAlpha = 1
      const trace = (color, alpha, lw) => {
        a.strokeStyle = color; a.globalAlpha = alpha; a.lineWidth = lw; a.lineCap = 'square'
        let x = 16 + 96 * r(), y = r() < 0.5 ? 8 : 120
        a.beginPath(); a.moveTo(x, y)
        const segs = 2 + ((r() * 3) | 0)
        for (let s = 0; s < segs; s++) {
          if (s % 2 === 0) y = 16 + 96 * r(); else x = 16 + 96 * r()
          a.lineTo(x, y)
          a.fillStyle = color; a.fillRect(x - 2.4, y - 2.4, 4.8, 4.8)
        }
        a.stroke(); a.globalAlpha = 1
      }
      trace(theme.brand, 0.5, 2.6); trace(theme.brand, 0.35, 2.2); trace(theme.muted, 0.3, 2.2)
      if (r() < 0.5) trace(theme.brand, 0.4, 2.6)
      a.strokeStyle = theme.brand; a.globalAlpha = 0.15; a.lineWidth = 4
      a.beginPath(); a.roundRect(7, 7, 114, 114, 16); a.stroke(); a.globalAlpha = 1
      a.globalCompositeOperation = 'destination-in'
      a.fillStyle = '#000'
      a.beginPath(); a.roundRect(0, 0, 128, 128, 20); a.fill()
      a.globalCompositeOperation = 'source-over'
      return c
    }
    function solidTile(seed) {
      const c = document.createElement('canvas')
      c.width = c.height = 64
      const a = c.getContext('2d')
      a.beginPath(); a.roundRect(0, 0, 64, 64, 11)
      a.fillStyle = theme.solidBg[seed % theme.solidBg.length]; a.fill()
      a.strokeStyle = theme.brandBorder; a.lineWidth = 2; a.stroke()
      return c
    }
    let boardsReady = false
    function buildAbstractTiles() {
      // مشتقات رنگ برند با آلفا — برای استروک و هاله
      theme.brandGlow = theme.light ? 'rgba(251,192,45,.14)' : 'rgba(251,192,45,.10)'
      theme.brandBorder = theme.light ? 'rgba(161,98,7,.3)' : 'rgba(251,192,45,.3)'
      TILES = Array.from({ length: 12 }, (_, k) => makeTile(k + 1))
      SOLIDS = Array.from({ length: 4 }, (_, k) => solidTile(k))
      // اگر عکس بردها قبلاً لود شده‌اند (مثلاً بعد از تعویض تم)، تایل‌های عکسی حفظ می‌شوند
      if (boardsReady) buildBoardTiles()
    }

    // ─── ۳ب) با لود عکس بردها، هر سلول به عکس واقعی برد تبدیل می‌شود ───
    const boardImg = new Image()
    boardImg.src = '/images/board.webp'
    const boardImg2 = new Image()
    boardImg2.src = '/images/board2.webp'
    function buildBoardTiles() {
      const boards = [boardImg, boardImg2]
      TILES = Array.from({ length: 12 }, (_, k) => {
        const img = boards[k % 2]
        const c = document.createElement('canvas')
        c.width = c.height = 256
        const a = c.getContext('2d')
        a.save()
        a.beginPath(); a.roundRect(0, 0, 256, 256, 40); a.clip()
        a.drawImage(img, 0, 0, 256, 256)
        const v = ((k >> 1) % 3) * 0.09
        if (v > 0) { a.fillStyle = 'rgba(255,255,255,' + v.toFixed(2) + ')'; a.fillRect(0, 0, 256, 256) }
        a.restore()
        a.strokeStyle = theme.brandBorder; a.lineWidth = 8
        a.beginPath(); a.roundRect(14, 14, 228, 228, 32); a.stroke()
        return c
      })
      SOLIDS = Array.from({ length: 4 }, (_, k) => {
        const img = boards[k % 2]
        const c = document.createElement('canvas')
        c.width = c.height = 128
        const a = c.getContext('2d')
        a.beginPath(); a.roundRect(0, 0, 128, 128, 22); a.clip()
        a.drawImage(img, 0, 0, 128, 128)
        if (k > 1) { a.fillStyle = 'rgba(255,255,255,.12)'; a.fillRect(0, 0, 128, 128) }
        return c
      })
    }
    let boardsLoaded = 0
    const maybeBuild = () => {
      if (++boardsLoaded === 2) {
        boardsReady = true
        buildBoardTiles()
        // بعد از لود عکس‌ها یک بار بازرسی تا تایل‌های واقعی دیده شوند — اگر حلقه
        // در حال اجراست فریم بعدی خودش این کار را می‌کند (بدون دو زنجیره‌ی rAF)
        if (!(started && running && shown)) { lastDraw = -1e9; requestAnimationFrame(frame) }
      }
    }
    if (boardImg.complete && boardImg.naturalWidth) boardsLoaded++; else boardImg.addEventListener('load', maybeBuild)
    if (boardImg2.complete && boardImg2.naturalWidth) boardsLoaded++; else boardImg2.addEventListener('load', maybeBuild)
    if (boardsLoaded === 2) { boardsReady = true; buildBoardTiles() }

    const tileFor = (i) => TILES[((i % G) * 7 + (((i / G) | 0) * 13)) % 12]
    const solidFor = (i) => SOLIDS[((i % G) + ((i / G) | 0)) % 4]

    // ─── ۴) پارامترهای حلقه زوم ───
    const R = G / 0.78
    const CYCLE = 12
    const GROW_AT = 0.04
    const GROW_DUR = 0.82 * CYCLE

    function camera() {
      const desktop = view.w >= 992
      const dieW = desktop ? Math.min(view.w * 0.5, view.h * 0.82) : Math.min(view.w * 0.86, view.h * 0.34)
      return {
        // چیدمان RTL: ستون متن سمت راست است، پس بردها سمت چپ زندگی می‌کنند
        cx: desktop ? view.w * 0.30 : view.w * 0.5,
        cy: desktop ? view.h * 0.52 : view.h * 0.86,
        base: dieW / (G * 2),
      }
    }

    const bornCount = (clock) => clamp(clock / GROW_DUR, 0, 1) * N

    function drawLevel(cx, cy, pitch, clock, alpha, detailed, skipCenter) {
      const size = pitch * 0.78
      if (size < 1.2 || alpha <= 0.01) return
      const nb = bornCount(clock)
      const centerIdx = idxOf(C, C)
      ctx.save()
      for (let r = 0; r < N; r++) {
        if (r >= nb) break
        const i = birthOrder[r]
        if (skipCenter && i === centerIdx) continue
        const bp = clamp((nb - r) / 3, 0, 1)
        const e = 1 - Math.pow(1 - bp, 3)
        const x = i % G, y = (i / G) | 0
        const px = cx + (x - C) * pitch, py = cy + (y - C) * pitch
        if (px < -size || py < -size || px > view.w + size || py > view.h + size) continue
        const s = size * (0.72 + 0.28 * e)
        ctx.globalAlpha = alpha * e
        if (detailed && size > 20) ctx.drawImage(tileFor(i), px - s / 2, py - s / 2, s, s)
        else ctx.drawImage(solidFor(i), px - s / 2, py - s / 2, s, s)
        // فلش تولد — سلول تازه‌متولدشده یک لحظه با رنگ برند می‌درخشد
        if (e < 1) {
          ctx.globalAlpha = alpha * (1 - e) * 0.55
          ctx.fillStyle = theme.brand
          ctx.beginPath()
          ctx.roundRect(px - s / 2, py - s / 2, s, s, Math.min(6, s * 0.16))
          ctx.fill()
        }
      }
      ctx.restore()
      ctx.globalAlpha = 1
    }

    function dotGrid(cx, cy, pitch, alpha) {
      if (pitch < 9 || alpha <= 0.01) return
      if ((view.w / pitch) * (view.h / pitch) > 12000) return
      const offx = ((cx % pitch) + pitch) % pitch
      const offy = ((cy % pitch) + pitch) % pitch
      ctx.fillStyle = theme.dot
      ctx.globalAlpha = alpha * 0.5
      for (let y = offy; y <= view.h; y += pitch)
        for (let x = offx; x <= view.w; x += pitch)
          ctx.fillRect(x - 1, y - 1, 2, 2)
      ctx.globalAlpha = 1
    }

    // ─── ۵) حلقه اصلی ───
    // سقف ~۳۰fps: حرکت زوم آن‌قدر کند است که ۶۰فریم فقط main-thread را مشغول نگه می‌دارد
    const FRAME_MS = 1000 / 30 - 2
    let t0 = null, running = true, shown = !document.hidden, started = false, raf = 0, lastDraw = -1e9

    // گرادیان‌های واش/محوشوندگی یک بار در هر resize یا تعویض تم ساخته می‌شوند، نه هر فریم
    let washGrad = null, fadeGrad = null, fadeH = 0
    function buildWash() {
      const desktop = view.w >= 992
      const rgb = theme.bgRgb
      washGrad = desktop
        ? ctx.createLinearGradient(view.w, 0, view.w * 0.32, 0)
        : ctx.createLinearGradient(0, 0, 0, view.h * 0.72)
      washGrad.addColorStop(0, `rgba(${rgb},1)`)
      washGrad.addColorStop(desktop ? 0.55 : 0.62, `rgba(${rgb},.96)`)
      washGrad.addColorStop(desktop ? 0.82 : 0.86, `rgba(${rgb},.5)`)
      washGrad.addColorStop(1, `rgba(${rgb},0)`)
      fadeH = Math.min(view.h * 0.24, 200)
      fadeGrad = ctx.createLinearGradient(0, view.h - fadeH, 0, view.h)
      fadeGrad.addColorStop(0, `rgba(${rgb},0)`)
      fadeGrad.addColorStop(1, `rgba(${rgb},1)`)
    }

    function frame(ts) {
      if (!reduced && running && shown && started) raf = requestAnimationFrame(frame)
      if (ts - lastDraw < FRAME_MS) return
      lastDraw = ts
      if (t0 == null) t0 = ts - CYCLE * 160  // شروع از فاز ۰.۱۶ — دای خوانا از فریم اول
      const t = (ts - t0) / 1000
      // فاز ثابت ۰.۱۶ — دای تقریباً کامل‌رشدکرده و در اندازه‌ی خوانا دیده می‌شود
      const phase = reduced ? 0.16 : (t % CYCLE) / CYCLE
      const { cx, cy, base } = camera()
      const pitch = base * 2 * Math.pow(R, -phase)
      const pitchPar = pitch * R

      ctx.clearRect(0, 0, view.w, view.h)
      // پس‌زمینه پر نمی‌شود — بک‌گراند gas+circuit سایت از زیر کنواس دیده می‌شود

      dotGrid(cx, cy, 26, 0.7)

      const clockPar = reduced ? GROW_DUR * 0.62 : (phase - GROW_AT) * CYCLE

      drawLevel(cx, cy, pitch, 1e9, 1, pitch * 0.78 > 20)

      const gcPitch = pitch / R
      if (gcPitch * G > 7) drawLevel(cx, cy, gcPitch, 1e9, clamp(1 - phase * 2, 0, 1), false)

      drawLevel(cx, cy, pitchPar, Math.max(0, clockPar), 1, true, true)

      // براکت دور دایِ در حال کوچک‌شدن
      {
        const half = (G * pitch) / 2 + 6
        const vfA = clamp(Math.sin(phase * Math.PI) * 1.15, 0, 0.85) * 0.72
        if (vfA > 0.02 && half > 9) {
          const L = Math.min(16, half * 0.4)
          ctx.strokeStyle = theme.brand
          ctx.globalAlpha = vfA
          ctx.lineWidth = 1.6
          const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
          corners.forEach(([sx, sy]) => {
            const px = cx + sx * half, py = cy + sy * half
            ctx.beginPath()
            ctx.moveTo(px - sx * L, py)
            ctx.lineTo(px, py)
            ctx.lineTo(px, py - sy * L)
            ctx.stroke()
          })
          ctx.globalAlpha = 1
        }
      }

      // مارکر پین ۱ (قرارداد صنعتی)
      const p1x = cx + (4 - C) * pitchPar, p1y = cy + (4 - C) * pitchPar
      ctx.beginPath(); ctx.arc(p1x, p1y, Math.max(1.4, pitchPar * 0.05), 0, TAU)
      ctx.fillStyle = theme.brand; ctx.globalAlpha = 0.4; ctx.fill(); ctx.globalAlpha = 1

      // واش خوانایی روی ستون متن (سمت راست در دسکتاپ) — گرادیان پیش‌ساخته
      ctx.fillStyle = washGrad
      ctx.fillRect(0, 0, view.w, view.h)

      // محوشوندگی لبه پایین — بردها در پس‌زمینه حل می‌شوند تا مرز هیرو با سکشن بعد خط نداشته باشد
      ctx.fillStyle = fadeGrad
      ctx.fillRect(0, view.h - fadeH, view.w, fadeH)

      // کپشن پایین-چپ، آروم (بعد از محوشوندگی کشیده می‌شود تا کم‌رنگ نشود)
      ctx.font = '12.5px Vazirmatn, Tahoma, Arial, sans-serif'
      ctx.fillStyle = theme.muted
      ctx.textAlign = 'left'
      ctx.fillText('هر برد، یکی از هزاران قطعه‌ای است که اینجا پیدا می‌شود', 18, view.h - 14)
    }

    // rgb خام پس‌زمینه برای گرادیان واش
    const readBgRgb = () => {
      const m = theme.bg.match(/#([0-9a-f]{6})/i)
      theme.bgRgb = m
        ? `${parseInt(m[1].slice(0, 2), 16)},${parseInt(m[1].slice(2, 4), 16)},${parseInt(m[1].slice(4, 6), 16)}`
        : '10,10,11'
    }

    readTheme()
    readBgRgb()
    buildWash()
    // اولین فریم بلافاصله رسم می‌شود (هیرو خالی نمی‌ماند) — در فاز خوابانده‌شده ۰.۱۶
    // تا دای تقریباً کامل‌رشدکرده به‌صورت ثابت دیده شود و حلقه بعداً از همان‌جا ادامه یابد
    raf = requestAnimationFrame(frame)
    // حلقه انیمیشن فقط با اولین تعامل واقعی کاربر (اسکرول/لمس/کلید) شروع می‌شود.
    // روی دسکتاپ fallbackِ load+8s هم هست؛ روی ویوپورت کوچک عمداً نیست تا
    // ترِیس Lighthouse/موبایل هرگز با انیمیشن دیررس آلوده نشود
    let loopTimer = 0
    const smallScreen = window.matchMedia('(max-width: 768px)').matches
    const startLoop = () => {
      if (started || reduced) return
      started = true
      t0 = null  // ری‌بیس — ادامه از همان فاز فریم ثابت، بدون پرش
      if (running && shown) { cancelAnimationFrame(raf); raf = requestAnimationFrame(frame) }
    }
    const scheduleLoop = () => { if (!smallScreen) loopTimer = setTimeout(startLoop, 8000) }
    if (document.readyState === 'complete') scheduleLoop()
    else window.addEventListener('load', scheduleLoop, { once: true })
    // مرورگرها هنگام لود رویداد scroll مصنوعی با scrollY=0 می‌سازند (تنظیمات
    // چیدمان/نوار آدرس موبایل) — فقط اسکرول واقعی کاربر (scrollY>0) یا لمس/کلید
    // به‌حساب تعامل است؛ once:true نیست تا رویداد مصنوعی شنونده را مصرف نکند
    const onInteract = (e) => {
      if (e.type === 'scroll' && (window.scrollY || 0) <= 0) return
      clearTimeout(loopTimer)
      startLoop()
      INTERACT_EVENTS.forEach(ev => window.removeEventListener(ev, onInteract))
    }
    const INTERACT_EVENTS = ['pointerdown', 'touchstart', 'scroll', 'keydown']
    INTERACT_EVENTS.forEach(ev => window.addEventListener(ev, onInteract, { passive: true }))

    const kick = () => { if (running && shown && started) { cancelAnimationFrame(raf); raf = requestAnimationFrame(frame) } }

    // ریسایز: فقط تغییر عرض واقعی پردازش می‌شود — در موبایل، اسکرول نوار آدرس را
    // مخفی/آشکار می‌کند و یک resize صرفاً‌ارتفاعی می‌سازد؛ fit() کنواس را پاک می‌کند
    // و بدون بازرسی فوری، فریم ثابت برای همیشه ناپدید می‌شد (باگ گزارش‌شده موبایل)
    const onResize = () => {
      const w = Math.round(canvas.getBoundingClientRect().width)
      if (w === lastW) return
      lastW = w
      view = fit()
      buildWash()
      // اگر حلقه در حال اجراست فریم بعدی خودش نقاشی می‌کند؛ وگرنه (فریم ثابت /
      // توقف / هنوز شروع نشده) همین‌جا بازرسی می‌کنیم تا کنواس هرگز خالی نماند
      // (lastDraw ریست می‌شود تا throttle فریمِ بازرسی را قورت ندهد)
      if (!(running && shown && started)) { lastDraw = -1e9; requestAnimationFrame(frame) }
    }
    window.addEventListener('resize', onResize)

    // تعویض تم — پالت و واش دوباره خوانده می‌شوند (در حالت فریم‌ثابت یک بار بازرسی می‌شود)
    const themeObs = new MutationObserver(() => {
      readTheme(); readBgRgb(); buildWash()
      if (reduced) requestAnimationFrame(frame)
    })
    themeObs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

    const io = new IntersectionObserver(es => {
      es.forEach(en => {
        if (en.isIntersecting && !running) { running = true; kick() }
        else if (!en.isIntersecting) running = false
      })
    }, { threshold: 0.02 })
    io.observe(canvas)

    // تب مخفی — حلقه کامل متوقف می‌شود
    const onVis = () => {
      shown = !document.hidden
      if (shown) kick()
      else cancelAnimationFrame(raf)
    }
    document.addEventListener('visibilitychange', onVis)

    return () => {
      running = false
      cancelAnimationFrame(raf)
      clearTimeout(loopTimer)
      window.removeEventListener('load', scheduleLoop)
      INTERACT_EVENTS.forEach(ev => window.removeEventListener(ev, onInteract))
      window.removeEventListener('resize', onResize)
      document.removeEventListener('visibilitychange', onVis)
      themeObs.disconnect()
      io.disconnect()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block' }}
    />
  )
}
