// تأیید رفتار کنواس هیرو + پس‌زمینه سایت در موبایل:
// ۱) فریم ثابت از لود هست و بدون تعامل هیچ انیمیشنی شروع نمی‌شود
// ۲) کنواسهای پس‌زمینه (gas+circuit) قبل از تعامل وجود ندارند
// ۳) با اولین اسکرول/لمس، لوپ هیرو و پس‌زمینه شروع می‌شوند و هیچ‌وقت خالی نمی‌مانند
// ۴) ریسایز ارتفاعی (نوار آدرس) و عرضی هیچ‌وقت کنواس را خالی نمی‌کند
// ۵) در حالت reduced-motion هیچ کنواس زمینه‌ای حتی بعد از تعامل هم ساخته نمی‌شود
const { chromium } = require('/home/shahin/.npm/_npx/e41f203b7505f1fb/node_modules/playwright')

const URL = process.env.TARGET || 'https://localhost:4175'

function canvasStats() {
  const c = document.querySelector('.hero-board canvas')
  if (!c) return { exists: false }
  const ctx = c.getContext('2d')
  const d = ctx.getImageData(0, 0, c.width, c.height).data
  let painted = 0
  for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 8) painted++
  return { exists: true, painted }
}
const canvasCount = () => document.querySelectorAll('canvas').length

;(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--ignore-certificate-errors'] })

  // ─── سناریوی ۱: موبایل توانمند ───
  {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true, hasTouch: true, deviceScaleFactor: 2, ignoreHTTPSErrors: true,
    })
    const page = await ctx.newPage()
    page.on('pageerror', e => console.log('PAGE ERROR:', e.message))
    await page.goto(URL, { waitUntil: 'load', timeout: 30000 })
    await page.waitForTimeout(1200)

    const s1 = await page.evaluate(canvasStats)
    await page.waitForTimeout(600)
    const s2 = await page.evaluate(canvasStats)
    const n1 = await page.evaluate(canvasCount)
    console.log('capable mobile | initial:', JSON.stringify(s1), 'canvases:', n1)
    if (!s1.exists || s1.painted < 1000) { console.log('FAIL: initial frame blank'); process.exit(1) }
    if (s1.painted !== s2.painted) { console.log('FAIL: hero animated without interaction', s1.painted, s2.painted); process.exit(1) }
    if (n1 !== 1) { console.log('FAIL: background canvases exist before interaction:', n1); process.exit(1) }
    console.log('  ✓ static frame present, no animation, no bg canvases before interaction')

    // اسکرول لمسی → لوپ هیرو + کنواسهای پس‌زمینه شروع شوند
    await page.evaluate(() => window.scrollTo({ top: 80 }))
    await page.waitForTimeout(1000)
    const a1 = await page.evaluate(canvasStats)
    await page.waitForTimeout(500)
    const a2 = await page.evaluate(canvasStats)
    const n2 = await page.evaluate(canvasCount)
    console.log('after scroll:', JSON.stringify(a1), '→', JSON.stringify(a2), 'canvases:', n2)
    if (a1.painted < 1000 || a2.painted < 1000) { console.log('FAIL: blank after scroll'); process.exit(1) }
    if (a1.painted === a2.painted) { console.log('FAIL: hero loop did not start on interaction'); process.exit(1) }
    if (n2 !== 3) { console.log('FAIL: background canvases missing after interaction:', n2); process.exit(1) }
    console.log('  ✓ hero loop + background canvases started on interaction')

    // اسکرول پلکانی + ریسایزها — هرگز خالی نشود
    for (const [w, h, label] of [[390, 740, 'URL-bar hide'], [390, 844, 'URL-bar back'], [500, 844, 'width change'], [390, 844, 'width back']]) {
      await page.setViewportSize({ width: w, height: h })
      await page.waitForTimeout(400)
      const s = await page.evaluate(canvasStats)
      if (s.painted < 1000) { console.log('FAIL: blank at', label, JSON.stringify(s)); process.exit(1) }
      console.log('  ✓ not blank after', label, `(${s.painted}px)`)
    }
    await page.evaluate(() => window.scrollTo({ top: 0 }))
    await ctx.close()
  }

  // ─── سناریوی ۲: reduced-motion (کم‌توان) ───
  {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true, hasTouch: true, reducedMotion: 'reduce', ignoreHTTPSErrors: true,
    })
    const page = await ctx.newPage()
    await page.goto(URL, { waitUntil: 'load', timeout: 30000 })
    await page.waitForTimeout(1200)
    const r1 = await page.evaluate(canvasStats)
    await page.evaluate(() => window.scrollTo({ top: 120 }))
    await page.waitForTimeout(800)
    const r2 = await page.evaluate(canvasStats)
    const n = await page.evaluate(canvasCount)
    console.log('reduced-motion | initial:', JSON.stringify(r1), 'after scroll:', JSON.stringify(r2), 'canvases:', n)
    if (!r1.exists || r1.painted < 1000) { console.log('FAIL: reduced initial frame blank'); process.exit(1) }
    if (r1.painted !== r2.painted) { console.log('FAIL: reduced mode animated'); process.exit(1) }
    if (n !== 1) { console.log('FAIL: reduced mode created background canvases:', n); process.exit(1) }
    console.log('  ✓ reduced-motion: static frame persists, no bg canvases even after interaction')
    await ctx.close()
  }

  await browser.close()
  console.log('ALL CHECKS PASSED')
})().catch(e => { console.error('ERROR', e.message); process.exit(1) })
