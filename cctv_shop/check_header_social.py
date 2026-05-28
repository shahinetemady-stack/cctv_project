import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
header_path = os.path.join(FRONTEND, 'components', 'layout', 'Header.jsx')

with open(header_path, encoding='utf-8') as f:
    content = f.read()

print("useSiteSettings:", 'useSiteSettings' in content)
print("useQuery:", 'useQuery' in content)
print("wa.me:", 'wa.me' in content)
print("settings:", 'settings' in content)

# نمایش بخش social
idx = content.find('wa.me')
if idx >= 0:
    print("\n=== Social section ===")
    print(content[idx-100:idx+200])
else:
    print("\n✗ دکمه واتساپ پیدا نشد")
    # نمایش خط‌های مربوط به settings
    for i, line in enumerate(content.split('\n'), 1):
        if 'settings' in line.lower():
            print(f"{i}: {line}")
