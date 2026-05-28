"""
python add_galaxy.py
اضافه کردن GalaxyBackground و glass effects به سایت
"""
import os, shutil

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
FE      = os.path.join(PROJECT, 'cctv_frontend')
SRC     = os.path.join(FE, 'src')

# ─── ۱. کپی GalaxyBackground ─────────────────────────────────
comp_dir = os.path.join(SRC, 'components', 'layout')
os.makedirs(comp_dir, exist_ok=True)
shutil.copy(
    os.path.join(BASE, 'GalaxyBackground.jsx'),
    os.path.join(comp_dir, 'GalaxyBackground.jsx')
)
print("✓ GalaxyBackground.jsx کپی شد")

# ─── ۲. کپی HeroVideo ────────────────────────────────────────
home_dir = os.path.join(SRC, 'components', 'home')
os.makedirs(home_dir, exist_ok=True)
shutil.copy(
    os.path.join(BASE, 'HeroVideo_scrub.jsx'),
    os.path.join(home_dir, 'HeroVideo.jsx')
)
print("✓ HeroVideo.jsx کپی شد")

# ─── ۳. اضافه کردن GalaxyBackground به Layout.jsx ────────────
layout_path = os.path.join(comp_dir, 'Layout.jsx')
if os.path.exists(layout_path):
    with open(layout_path, encoding='utf-8') as f:
        layout = f.read()

    if 'GalaxyBackground' not in layout:
        # اضافه کردن import
        layout = "import GalaxyBackground from './GalaxyBackground'\n" + layout

        # اضافه کردن component به ابتدای return
        layout = layout.replace(
            'return (\n    <',
            'return (\n    <>\n    <GalaxyBackground />\n    <'
        )
        # بستن fragment
        layout = layout.replace(
            '\n  )\n}',
            '\n    </>\n  )\n}',
            1
        )

        with open(layout_path, 'w', encoding='utf-8') as f:
            f.write(layout)
        print("✓ GalaxyBackground به Layout.jsx اضافه شد")
    else:
        print("✓ قبلاً موجود بود")
else:
    print(f"✗ Layout.jsx پیدا نشد در {layout_path}")
    # سعی در پیدا کردن Layout
    for root, dirs, files in os.walk(SRC):
        for f in files:
            if 'layout' in f.lower() or 'Layout' in f:
                print(f"   → {os.path.join(root, f)}")

# ─── ۴. اضافه کردن glass CSS به index.css ────────────────────
css_candidates = [
    os.path.join(SRC, 'index.css'),
    os.path.join(SRC, 'styles', 'index.css'),
    os.path.join(SRC, 'styles', 'globals.css'),
]

css_path = None
for c in css_candidates:
    if os.path.exists(c):
        css_path = c
        break

if css_path:
    with open(css_path, encoding='utf-8') as f:
        css = f.read()

    with open(os.path.join(BASE, 'galaxy_styles.css'), encoding='utf-8') as f:
        galaxy_css = f.read()

    if 'Glass Effect' not in css:
        css += '\n\n' + galaxy_css
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css)
        print(f"✓ Glass CSS اضافه شد به {css_path}")
    else:
        print("✓ قبلاً موجود بود")
else:
    print("✗ index.css پیدا نشد")

print("\n✅ کامل شد!")
print("سایت را refresh کنید")
