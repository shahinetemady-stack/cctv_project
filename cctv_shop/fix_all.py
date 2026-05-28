"""
python fix_all.py
درست کردن کهکشان کل سایت + glass effect قوی‌تر
"""
import os, shutil

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
FE      = os.path.join(PROJECT, 'cctv_frontend')
SRC     = os.path.join(FE, 'src')

# ─── ۱. Layout.jsx — اضافه کردن GalaxyBackground ─────────────
layout_path = os.path.join(SRC, 'components', 'layout', 'Layout.jsx')
with open(layout_path, encoding='utf-8') as f:
    layout = f.read()

if 'GalaxyBackground' not in layout:
    # اضافه کردن import
    first_import = layout.find('import ')
    layout = layout[:first_import] + "import GalaxyBackground from './GalaxyBackground'\n" + layout[first_import:]
    
    # پیدا کردن return و اضافه کردن GalaxyBackground
    # باید بعد از اولین div یا fragment باشد
    ret_idx = layout.find('return (')
    if ret_idx >= 0:
        # پیدا کردن اولین < بعد از return
        open_idx = layout.find('<', ret_idx)
        # اضافه کردن GalaxyBackground قبل از محتوای اصلی
        layout = layout[:open_idx] + '<>\n      <GalaxyBackground />\n      ' + layout[open_idx:]
        # بستن fragment قبل از آخرین )
        last_paren = layout.rfind('\n  )')
        layout = layout[:last_paren] + '\n    </>' + layout[last_paren:]
    
    with open(layout_path, 'w', encoding='utf-8') as f:
        f.write(layout)
    print("✓ GalaxyBackground به Layout اضافه شد")
else:
    print("✓ GalaxyBackground قبلاً در Layout بود")

# ─── ۲. HomePage — حذف GalaxyBackground اضافی ────────────────
home_path = os.path.join(SRC, 'pages', 'HomePage.jsx')
with open(home_path, encoding='utf-8') as f:
    home = f.read()

# حذف import GalaxyBackground از HomePage (چون در Layout است)
home = home.replace("import GalaxyBackground from '../components/layout/GalaxyBackground'\n", '')
# حذف <GalaxyBackground /> از HomePage
home = home.replace("      {theme !== 'explode' && <GalaxyBackground />}\n\n      ", '      ')

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(home)
print("✓ HomePage از GalaxyBackground تمیز شد")

# ─── ۳. CSS قوی‌تر ────────────────────────────────────────────
css_path = os.path.join(SRC, 'index.css')
with open(css_path, encoding='utf-8') as f:
    css = f.read()

# حذف CSS قدیمی
for marker in ['/* ─── Glass Effect', '/* ─── Galaxy & Glass']:
    if marker in css:
        idx = css.find(marker)
        css = css[:idx].rstrip()
        break

new_css = '''

/* ═══════════════════════════════════════════════
   GALAXY & GLASS EFFECT
═══════════════════════════════════════════════ */

/* پس‌زمینه پایه */
body {
  background: #000008 !important;
  color: rgba(255,255,255,0.85) !important;
}

/* ── Glass Card ── */
.card {
  background: rgba(8, 4, 30, 0.72) !important;
  backdrop-filter: blur(24px) saturate(160%) !important;
  -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  box-shadow:
    0 8px 32px rgba(0,0,0,0.5),
    0 1px 0 rgba(255,255,255,0.06) inset !important;
  transition: border-color 0.3s, box-shadow 0.3s !important;
}
.card:hover {
  border-color: rgba(255,165,0,0.2) !important;
  box-shadow:
    0 16px 48px rgba(0,0,0,0.6),
    0 0 30px rgba(255,165,0,0.05),
    0 1px 0 rgba(255,255,255,0.06) inset !important;
}

/* ── Header ── */
header, [class*="header"] {
  background: rgba(3,1,14,0.88) !important;
  backdrop-filter: blur(32px) !important;
  -webkit-backdrop-filter: blur(32px) !important;
  border-bottom: 1px solid rgba(255,255,255,0.06) !important;
  box-shadow: 0 4px 30px rgba(0,0,0,0.5) !important;
}

/* ── Modals ── */
.fixed.z-\\[300\\] > .card,
.fixed.z-\\[200\\] > .card,
.fixed.z-\\[400\\] > .card,
.fixed.z-\\[100\\] > .card {
  background: rgba(5,2,20,0.92) !important;
  backdrop-filter: blur(40px) !important;
  -webkit-backdrop-filter: blur(40px) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  box-shadow: 0 24px 64px rgba(0,0,0,0.7) !important;
}

/* پس‌زمینه modal */
.fixed.inset-0.bg-black\\/70,
.fixed.inset-0.bg-black\\/80 {
  backdrop-filter: blur(8px) !important;
  -webkit-backdrop-filter: blur(8px) !important;
}

/* ── Input ── */
.input {
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  color: rgba(255,255,255,0.9) !important;
  backdrop-filter: blur(10px) !important;
}
.input:focus {
  background: rgba(255,255,255,0.08) !important;
  border-color: rgba(255,165,0,0.4) !important;
  box-shadow: 0 0 0 3px rgba(255,165,0,0.08) !important;
  outline: none !important;
}
.input::placeholder {
  color: rgba(255,255,255,0.25) !important;
}

/* ── Dropdown / bg-navy ── */
.bg-navy, [class*="bg-navy"] {
  background: rgba(3,1,16,0.95) !important;
  backdrop-filter: blur(24px) !important;
  -webkit-backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6) !important;
}

/* ── Table ── */
table { background: transparent !important; }
tbody tr:nth-child(even) td { background: rgba(255,255,255,0.02) !important; }
tbody tr:hover td { background: rgba(255,165,0,0.03) !important; }
th { background: rgba(255,255,255,0.03) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
::-webkit-scrollbar-thumb { background: rgba(255,165,0,0.25); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,165,0,0.45); }

/* ── container-main ── */
.container-main { position: relative; z-index: 1; }

/* ── Label ── */
.label { color: rgba(255,255,255,0.45) !important; }

/* ── Select ── */
select { background: rgba(8,4,30,0.8) !important; color: rgba(255,255,255,0.85) !important; }
select option { background: #0a0520 !important; }

/* ── btn-secondary ── */
.btn-secondary {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  backdrop-filter: blur(10px) !important;
}
.btn-secondary:hover {
  background: rgba(255,255,255,0.1) !important;
  border-color: rgba(255,255,255,0.2) !important;
}

/* ── skeleton ── */
.skeleton {
  background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%) !important;
  background-size: 200% 100% !important;
  animation: shimmer 1.5s infinite !important;
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
'''

css += new_css
with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)
print("✓ CSS قوی‌تر اعمال شد")

print("\n✅ همه تغییرات اعمال شد!")
print("سایت را refresh کنید")
