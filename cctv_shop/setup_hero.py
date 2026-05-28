"""
python setup_hero.py
نصب Hero Section سینماتیک
"""
import os, shutil

BASE = os.path.join('..', 'cctv_frontend')
SRC = os.path.join(BASE, 'src')
PUBLIC = os.path.join(BASE, 'public')

# ساخت پوشه images در public
img_dir = os.path.join(PUBLIC, 'images')
os.makedirs(img_dir, exist_ok=True)

# کپی عکس‌های قطعات
imgs = {
    'cam_lens.jpg': 'cam_lens.jpg',
    'cam_parts.jpg': 'cam_parts.jpg',
    'cam_body.jpg': 'cam_body.jpg',
    'cam_pcb.jpg': 'cam_pcb.jpg',
    'cam_lens2.jpg': 'cam_lens2.jpg',
}
outputs_dir = os.path.join('..', '..', 'outputs')
for src_name, dst_name in imgs.items():
    src = os.path.join(outputs_dir, src_name)
    dst = os.path.join(img_dir, dst_name)
    if os.path.exists(src):
        shutil.copy(src, dst)
        print(f"✓ {dst_name}")
    else:
        print(f"✗ {src_name} پیدا نشد")

# ساخت پوشه components/home
comp_dir = os.path.join(SRC, 'components', 'home')
os.makedirs(comp_dir, exist_ok=True)

# کپی HeroSection
shutil.copy(
    os.path.join(outputs_dir, 'HeroSection.jsx'),
    os.path.join(comp_dir, 'HeroSection.jsx')
)
print("✓ HeroSection.jsx")

# کپی HomePage
shutil.copy(
    os.path.join(outputs_dir, 'HomePage_cinematic.jsx'),
    os.path.join(SRC, 'pages', 'HomePage.jsx')
)
print("✓ HomePage.jsx")

print("\n✅ نصب کامل شد!")
print("npm run dev را اجرا کنید")
