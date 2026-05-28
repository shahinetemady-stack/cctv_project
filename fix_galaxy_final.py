"""
fix_galaxy_final.py — اجرا در پوشه cctv_project:
python fix_galaxy_final.py
"""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))

FE = None
for name in ['cctv_frontend', 'frontend', 'cctv-frontend']:
    p = os.path.join(BASE, name)
    if os.path.isdir(p):
        FE = p
        break

if not FE:
    print("X پوشه frontend پیدا نشد. پوشه های موجود:")
    for item in os.listdir(BASE):
        print(f"   {item}")
    exit(1)

SRC = os.path.join(FE, 'src')
print(f"OK Frontend: {FE}\n")

# ════ 1. index.css ════════════════════════════════════════════════
css_path = os.path.join(SRC, 'index.css')
if not os.path.exists(css_path):
    css_path = os.path.join(SRC, 'App.css')

if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        css = f.read()
    for marker in ['/* --- Galaxy', '/* ===', '/* GALAXY', '/* --- Glass', '/* Glass', '/* galaxy']:
        if marker.lower() in css.lower():
            idx = css.lower().find(marker.lower())
            css = css[:idx].rstrip()
    css += '''

/* GALAXY BACKGROUND + FLOATING GLASS WINDOWS - Final */

body, #root, #root > div, .min-h-screen, .min-h-full {
  background: transparent !important;
  background-color: transparent !important;
  color: rgba(255,255,255,0.87) !important;
}
section, main > section, div > section {
  background: transparent !important;
  background-color: transparent !important;
}
.card {
  background: rgba(8,4,28,0.62) !important;
  backdrop-filter: blur(28px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(28px) saturate(180%) !important;
  border: 1px solid rgba(255,255,255,0.09) !important;
  box-shadow: 0 10px 40px rgba(0,0,0,0.55), 0 1px 0 rgba(255,255,255,0.07) inset !important;
  transition: border-color 0.3s, box-shadow 0.3s, transform 0.25s !important;
  position: relative;
  z-index: 1;
}
.card:hover {
  border-color: rgba(255,165,0,0.22) !important;
  box-shadow: 0 20px 60px rgba(0,0,0,0.65), 0 0 35px rgba(255,165,0,0.06), 0 1px 0 rgba(255,255,255,0.07) inset !important;
  transform: translateY(-4px) !important;
}
header, nav {
  background: rgba(2,1,10,0.82) !important;
  backdrop-filter: blur(36px) !important;
  -webkit-backdrop-filter: blur(36px) !important;
  border-bottom: 1px solid rgba(255,255,255,0.06) !important;
}
footer {
  background: rgba(2,1,10,0.88) !important;
  backdrop-filter: blur(24px) !important;
  border-top: 1px solid rgba(255,255,255,0.05) !important;
}
[role="dialog"], .bg-navy, [class*="bg-navy"] {
  background: rgba(4,2,20,0.92) !important;
  backdrop-filter: blur(32px) !important;
  border: 1px solid rgba(255,255,255,0.09) !important;
}
input, textarea, select {
  background: rgba(255,255,255,0.05) !important;
  border-color: rgba(255,255,255,0.1) !important;
  color: rgba(255,255,255,0.87) !important;
}
input:focus, textarea:focus, select:focus {
  background: rgba(255,255,255,0.08) !important;
  border-color: rgba(255,165,0,0.4) !important;
  box-shadow: 0 0 0 2px rgba(255,165,0,0.15) !important;
  outline: none !important;
}
select option { background: #090420 !important; }
[class*="bg-dark"], [class*="bg-gray-9"], [class*="bg-black"], [class*="bg-zinc-9"] {
  background: transparent !important;
}
.card [class*="aspect"], .card .aspect-square {
  background: linear-gradient(135deg, rgba(255,165,0,0.04) 0%, rgba(80,60,200,0.06) 100%) !important;
}
th { background: rgba(255,255,255,0.04) !important; }
tbody tr:nth-child(even) td { background: rgba(255,255,255,0.018) !important; }
tbody tr:hover td { background: rgba(255,165,0,0.04) !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
::-webkit-scrollbar-thumb { background: rgba(255,165,0,0.28); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,165,0,0.5); }
main, .container-main { position: relative; z-index: 1; }
.btn-secondary {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  backdrop-filter: blur(12px) !important;
}
.btn-secondary:hover {
  background: rgba(255,255,255,0.1) !important;
  border-color: rgba(255,255,255,0.22) !important;
}
'''
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(css)
    print("OK index.css updated")
else:
    print("X index.css not found")

# ════ 2. HomePage.jsx — حذف background مشکی از Hero section ════
home_path = os.path.join(SRC, 'pages', 'HomePage.jsx')
if os.path.exists(home_path):
    with open(home_path, encoding='utf-8') as f:
        home = f.read()
    original = home

    replacements = [
        ("background: '#000'", "background: 'transparent'"),
        ("background: '#000000'", "background: 'transparent'"),
        ("background: \"#000\"", "background: \"transparent\""),
        ("background: \"#000000\"", "background: \"transparent\""),
        ("background: 'black'", "background: 'transparent'"),
        ("background: \"black\"", "background: \"transparent\""),
        ("background: 'rgb(0,0,0)'", "background: 'transparent'"),
        ("background: 'rgb(0, 0, 0)'", "background: 'transparent'"),
        ("backgroundColor: '#000'", "backgroundColor: 'transparent'"),
        ("backgroundColor: '#000000'", "backgroundColor: 'transparent'"),
        ("backgroundColor: 'black'", "backgroundColor: 'transparent'"),
    ]
    for old, new in replacements:
        if old in home:
            home = home.replace(old, new)
            print(f"  OK removed: {old}")

    # regex برای background رنگ های تاریک در section hero
    home = re.sub(r"(height:\s*'100vh'[^}]*?)background:\s*'#[0-9a-fA-F]{3,6}'", r"\1background: 'transparent'", home)
    home = re.sub(r"background:\s*'#0[0-9a-fA-F]+'", "background: 'transparent'", home)

    if home != original:
        with open(home_path, 'w', encoding='utf-8') as f:
            f.write(home)
        print("OK HomePage.jsx updated - black background removed from hero")
    else:
        print("WARNING HomePage.jsx: inline black background not found with simple patterns")
        print("Showing suspicious lines:")
        for i, line in enumerate(home.split('\n')):
            if 'background' in line and any(x in line for x in ['000', 'black', '#00']):
                print(f"   Line {i+1}: {line.strip()[:100]}")
else:
    print("X HomePage.jsx not found")

# ════ 3. GalaxyBackground.jsx ════════════════════════════════════
galaxy_dir = os.path.join(SRC, 'components', 'layout')
os.makedirs(galaxy_dir, exist_ok=True)
galaxy_path = os.path.join(galaxy_dir, 'GalaxyBackground.jsx')

GALAXY = open(galaxy_path, encoding="utf-8").read() if os.path.exists(galaxy_path) else ""
if GALAXY and "position: 'fixed'" in GALAXY and "zIndex: -1" in GALAXY:
    print("OK GalaxyBackground.jsx is correct, no changes needed")
else:
    GALAXY_NEW = """import { useEffect, useRef } from 'react'

export default function GalaxyBackground() {
  const canvasRef = useRef(null)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId

    const STARS = Array.from({ length: 220 }, () => ({
      x: Math.random(), y: Math.random(),
      r: Math.random() * 1.6 + 0.2,
      twinkle: Math.random() * Math.PI * 2,
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      color: Math.random() > 0.8
        ? `hsl(${200 + Math.random() * 60},80%,85%)`
        : `hsl(${25 + Math.random() * 20},60%,92%)`,
    }))
    const DUST = Array.from({ length: 6 }, () => ({
      x: Math.random(), y: Math.random(),
      rx: Math.random() * 0.35 + 0.15, ry: Math.random() * 0.25 + 0.1,
      opacity: Math.random() * 0.07 + 0.02,
      hue: Math.random() > 0.5 ? 260 : 200,
    }))
    const METEORS = Array.from({ length: 3 }, () => ({
      x: 0, y: 0, speed: Math.random() * 0.003 + 0.002,
      len: Math.random() * 0.08 + 0.04, opacity: 0, active: false,
      timer: Math.random() * 300 + 100,
    }))

    function resize() {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    function draw() {
      const W = canvas.width, H = canvas.height
      ctx.clearRect(0, 0, W, H)
      const bg = ctx.createRadialGradient(W*0.4, H*0.35, 0, W*0.5, H*0.5, W*0.85)
      bg.addColorStop(0, 'rgba(15,8,60,1)')
      bg.addColorStop(0.3, 'rgba(8,4,35,1)')
      bg.addColorStop(0.6, 'rgba(4,2,20,1)')
      bg.addColorStop(1, 'rgba(1,0,8,1)')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, W, H)
      DUST.forEach(d => {
        const g = ctx.createRadialGradient(d.x*W, d.y*H, 0, d.x*W, d.y*H, d.rx*W)
        g.addColorStop(0, `hsla(${d.hue},70%,55%,${d.opacity})`)
        g.addColorStop(1, 'transparent')
        ctx.save(); ctx.scale(1, d.ry/d.rx)
        ctx.fillStyle = g
        ctx.beginPath(); ctx.arc(d.x*W, d.y*H/(d.ry/d.rx), d.rx*W, 0, Math.PI*2)
        ctx.fill(); ctx.restore()
      })
      STARS.forEach(s => {
        s.twinkle += s.twinkleSpeed
        const a = 0.5 + Math.sin(s.twinkle) * 0.5
        const col = s.color.replace('hsl(', 'hsla(').replace(')', `,${a})`)
        const glow = ctx.createRadialGradient(s.x*W, s.y*H, 0, s.x*W, s.y*H, s.r*3)
        glow.addColorStop(0, col); glow.addColorStop(1, 'transparent')
        ctx.fillStyle = glow
        ctx.beginPath(); ctx.arc(s.x*W, s.y*H, s.r*3, 0, Math.PI*2); ctx.fill()
        ctx.fillStyle = col
        ctx.beginPath(); ctx.arc(s.x*W, s.y*H, s.r*0.6, 0, Math.PI*2); ctx.fill()
      })
      METEORS.forEach(m => {
        if (!m.active) {
          if (--m.timer <= 0) {
            m.x = Math.random()*0.7; m.y = Math.random()*0.4
            m.opacity = 1; m.active = true; m.timer = Math.random()*400+200
          }
        } else {
          m.x += m.speed*1.5; m.y += m.speed; m.opacity -= 0.012
          if (m.opacity <= 0) { m.active = false; return }
          const ex = m.x - m.len*1.5, ey = m.y - m.len
          const gr = ctx.createLinearGradient(m.x*W, m.y*H, ex*W, ey*H)
          gr.addColorStop(0, `rgba(255,255,255,${m.opacity})`)
          gr.addColorStop(0.4, `rgba(200,220,255,${m.opacity*0.4})`)
          gr.addColorStop(1, 'transparent')
          ctx.strokeStyle = gr; ctx.lineWidth = 1.5
          ctx.beginPath(); ctx.moveTo(m.x*W, m.y*H); ctx.lineTo(ex*W, ey*H); ctx.stroke()
        }
      })
      animId = requestAnimationFrame(draw)
    }
    draw()
    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize) }
  }, [])

  return (
    <canvas ref={canvasRef} style={{
      position: 'fixed', top: 0, left: 0,
      width: '100vw', height: '100vh',
      zIndex: -1, pointerEvents: 'none', display: 'block',
    }} />
  )
}
"""
    with open(galaxy_path, 'w', encoding='utf-8') as f:
        f.write(GALAXY_NEW)
    print("OK GalaxyBackground.jsx rewritten")

# ════ 4. Layout.jsx ══════════════════════════════════════════════
layout_path = os.path.join(SRC, 'components', 'layout', 'Layout.jsx')
if os.path.exists(layout_path):
    with open(layout_path, encoding='utf-8') as f:
        layout = f.read()
    if 'GalaxyBackground' in layout:
        print("OK Layout.jsx already has GalaxyBackground")
    else:
        print("WARNING Layout.jsx does NOT have GalaxyBackground!")
        print("   Please add manually:")
        print("   import GalaxyBackground from './GalaxyBackground'")
        print("   And add <GalaxyBackground /> at start of return")
else:
    print(f"WARNING Layout.jsx not found at {layout_path}")

print("\n" + "="*50)
print("DONE! Now do Ctrl+Shift+R in browser")
print("="*50)
