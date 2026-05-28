"""
python apply_fixes.py
اعمال همه تغییرات
"""
import os, shutil

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
FE      = os.path.join(PROJECT, 'cctv_frontend')
SRC     = os.path.join(FE, 'src')

# ۱. کپی HomePage آپدیت شده
shutil.copy(
    os.path.join(BASE, 'HomePage_smart.jsx'),
    os.path.join(SRC, 'pages', 'HomePage.jsx')
)
print("✓ HomePage.jsx آپدیت شد")

# ۲. آپدیت index.css
css_path = os.path.join(SRC, 'index.css')
with open(css_path, encoding='utf-8') as f:
    css = f.read()

# حذف CSS قدیمی و اضافه کردن جدید
if 'Glass Effect' in css:
    start = css.find('/* ─── Glass Effect')
    if start == -1:
        start = css.find('/* ─── Galaxy & Glass')
    if start > 0:
        css = css[:start].rstrip()
    print("✓ CSS قدیمی حذف شد")

with open(os.path.join(BASE, 'galaxy_styles.css'), encoding='utf-8') as f:
    new_css = f.read()

css += '\n\n' + new_css

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)
print("✓ CSS جدید اعمال شد")

print("\n✅ کامل شد! صفحه را refresh کنید")
