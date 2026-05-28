import os

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
APP = os.path.join(PROJECT, 'cctv_frontend', 'src', 'App.jsx')

with open(APP, encoding='utf-8') as f:
    content = f.read()

if 'ThemeSettingsPage' not in content:
    # اضافه کردن import
    content = content.replace(
        "import InvoicePrintPage",
        "import ThemeSettingsPage from './pages/admin/ThemeSettingsPage'\nimport InvoicePrintPage"
    )
    # اضافه کردن route
    content = content.replace(
        '<Route path="admin/kardex"',
        '<Route path="admin/theme" element={<RequireAuth><ThemeSettingsPage /></RequireAuth>} />\n        <Route path="admin/kardex"'
    )
    with open(APP, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Route اضافه شد: /admin/theme")
else:
    print("✓ قبلاً موجود بود")

# کپی فایل‌ها
import shutil
src_dir = BASE
dst_pages = os.path.join(PROJECT, 'cctv_frontend', 'src', 'pages', 'admin')
dst_home = os.path.join(PROJECT, 'cctv_frontend', 'src', 'components', 'home')
os.makedirs(dst_pages, exist_ok=True)
os.makedirs(dst_home, exist_ok=True)

for f, d in [
    ('ThemeSettingsPage.jsx', os.path.join(dst_pages, 'ThemeSettingsPage.jsx')),
    ('HeroSection_final.jsx', os.path.join(dst_home, 'HeroSection.jsx')),
]:
    src = os.path.join(src_dir, f)
    if os.path.exists(src):
        shutil.copy(src, d)
        print(f"✓ {f}")
    else:
        print(f"✗ {f} پیدا نشد — دستی کپی کنید")

print("\n✅ تمام!")
print("آدرس پنل تنظیمات قالب: http://localhost:3000/admin/theme")
