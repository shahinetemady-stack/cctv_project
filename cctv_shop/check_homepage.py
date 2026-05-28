import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')

with open(home_path, encoding='utf-8') as f:
    content = f.read()

print("Lines:", content.count('\n'))
print("Has FeaturedPackages:", 'FeaturedPackages' in content)

# نمایش آخر فایل
lines = content.split('\n')
print("\n=== آخر فایل ===")
for i, line in enumerate(lines[-20:], len(lines)-20):
    print(f"{i}: {line}")
