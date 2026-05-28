import { useEffect, useRef } from 'react'

// ─── بک‌گراند کهکشانی با Canvas ──────────────────────────────
export default function GalaxyBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId
    let time = 0

    // ─── ستاره‌ها ──────────────────────────────────────────────
    const STARS = Array.from({ length: 200 }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: Math.random() * 1.5 + 0.2,
      speed: Math.random() * 0.0002 + 0.0001,
      twinkle: Math.random() * Math.PI * 2,
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      color: Math.random() > 0.8
        ? `hsl(${200 + Math.random()*60}, 80%, 80%)`
        : `hsl(${30 + Math.random()*20}, 60%, 90%)`,
    }))

    // ─── ذرات غبار کهکشان ─────────────────────────────────────
    const DUST = Array.from({ length: 80 }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: Math.random() * 60 + 20,
      opacity: Math.random() * 0.06 + 0.01,
      hue: Math.random() > 0.5 ? 220 : 280,
      speed: Math.random() * 0.00005,
    }))

    // ─── شهاب‌ها ───────────────────────────────────────────────
    const METEORS = []
    function spawnMeteor() {
      if (Math.random() > 0.003) return
      METEORS.push({
        x: Math.random(),
        y: Math.random() * 0.5,
        len: Math.random() * 0.12 + 0.05,
        speed: Math.random() * 0.003 + 0.002,
        opacity: 1,
        angle: Math.PI / 4 + (Math.random() - 0.5) * 0.3,
      })
    }

    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    function draw() {
      const W = canvas.width
      const H = canvas.height
      time++

      // ─── پس‌زمینه فضا ─────────────────────────────────────
      const bg = ctx.createRadialGradient(W*0.5, H*0.4, 0, W*0.5, H*0.5, W*0.8)
      bg.addColorStop(0,   '#0a0318')
      bg.addColorStop(0.3, '#050212')
      bg.addColorStop(0.7, '#020108')
      bg.addColorStop(1,   '#000005')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, W, H)

      // ─── غبار کهکشان ──────────────────────────────────────
      DUST.forEach(d => {
        d.x += d.speed
        if (d.x > 1.2) d.x = -0.2
        const gx = ctx.createRadialGradient(
          d.x*W, d.y*H, 0,
          d.x*W, d.y*H, d.r
        )
        gx.addColorStop(0, `hsla(${d.hue}, 70%, 50%, ${d.opacity})`)
        gx.addColorStop(1, `hsla(${d.hue}, 70%, 50%, 0)`)
        ctx.fillStyle = gx
        ctx.beginPath()
        ctx.ellipse(d.x*W, d.y*H, d.r*2, d.r, Math.PI/6, 0, Math.PI*2)
        ctx.fill()
      })

      // ─── نبولای مرکزی ──────────────────────────────────────
      const neb = ctx.createRadialGradient(W*0.45, H*0.45, 0, W*0.45, H*0.45, W*0.35)
      neb.addColorStop(0,   'rgba(80,20,120,0.08)')
      neb.addColorStop(0.4, 'rgba(30,10,80,0.05)')
      neb.addColorStop(1,   'transparent')
      ctx.fillStyle = neb
      ctx.fillRect(0, 0, W, H)

      const neb2 = ctx.createRadialGradient(W*0.6, H*0.6, 0, W*0.6, H*0.6, W*0.25)
      neb2.addColorStop(0,   'rgba(0,40,100,0.07)')
      neb2.addColorStop(1,   'transparent')
      ctx.fillStyle = neb2
      ctx.fillRect(0, 0, W, H)

      // ─── ستاره‌ها ──────────────────────────────────────────
      STARS.forEach(s => {
        s.twinkle += s.twinkleSpeed
        s.y -= s.speed
        if (s.y < 0) { s.y = 1; s.x = Math.random() }

        const tw  = Math.sin(s.twinkle)
        const alpha = 0.4 + tw * 0.5
        const r   = s.r * (0.8 + tw * 0.3)

        // هاله ستاره
        if (s.r > 1) {
          const glow = ctx.createRadialGradient(s.x*W, s.y*H, 0, s.x*W, s.y*H, r*4)
          glow.addColorStop(0, s.color.replace(')', `, ${alpha*0.3})`).replace('hsl', 'hsla'))
          glow.addColorStop(1, 'transparent')
          ctx.fillStyle = glow
          ctx.beginPath()
          ctx.arc(s.x*W, s.y*H, r*4, 0, Math.PI*2)
          ctx.fill()
        }

        ctx.fillStyle = s.color
        ctx.globalAlpha = alpha
        ctx.beginPath()
        ctx.arc(s.x*W, s.y*H, r, 0, Math.PI*2)
        ctx.fill()
        ctx.globalAlpha = 1
      })

      // ─── شهاب‌ها ───────────────────────────────────────────
      spawnMeteor()
      for (let i = METEORS.length - 1; i >= 0; i--) {
        const m = METEORS[i]
        m.x += Math.cos(m.angle) * m.speed
        m.y += Math.sin(m.angle) * m.speed
        m.opacity -= 0.015

        if (m.opacity <= 0 || m.x > 1.2 || m.y > 1.2) {
          METEORS.splice(i, 1)
          continue
        }

        const ex = m.x - Math.cos(m.angle) * m.len
        const ey = m.y - Math.sin(m.angle) * m.len
        const grad = ctx.createLinearGradient(m.x*W, m.y*H, ex*W, ey*H)
        grad.addColorStop(0, `rgba(255,255,255,${m.opacity})`)
        grad.addColorStop(0.3, `rgba(200,220,255,${m.opacity*0.5})`)
        grad.addColorStop(1, 'transparent')

        ctx.strokeStyle = grad
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.moveTo(m.x*W, m.y*H)
        ctx.lineTo(ex*W, ey*H)
        ctx.stroke()
      }

      animId = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100vw', height: '100vh',
        zIndex: -1,
        pointerEvents: 'none',
      }}
    />
  )
}
