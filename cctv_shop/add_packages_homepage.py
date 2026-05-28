import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')

with open(home_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن import
if 'FeaturedPackages' not in content:
    # پیدا کردن اولین import
    first_import_end = content.find('\n', content.find('import ')) + 1
    content = content[:first_import_end] + "import { FeaturedPackages } from '../components/PackageComponents'\n" + content[first_import_end:]
    print("✓ import اضافه شد")

# اضافه کردن سکشن پکیج‌ها قبل از سکشن همکاران
old = '''        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-brand to-steel p-10 text-center">'''
new = '''        <FeaturedPackages />

        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-brand to-steel p-10 text-center">'''

if old in content and 'FeaturedPackages' not in content.split('import')[0]:
    content = content.replace(old, new)
    print("✓ FeaturedPackages به HomePage اضافه شد")
elif '<FeaturedPackages' in content:
    print("✓ قبلاً اضافه شده بود")
else:
    print("✗ جای مناسب پیدا نشد")

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
