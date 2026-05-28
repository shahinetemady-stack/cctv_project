import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
footer_path = os.path.join(FRONTEND, 'components', 'layout', 'Footer.jsx')

with open(footer_path, encoding='utf-8') as f:
    content = f.read()

print("Lines:", content.count('\n'))
print("useQuery:", 'useQuery' in content)
print("api:", 'api' in content)
print("settings:", 'settings' in content)
print("socials:", 'socials' in content)

lines = content.split('\n')
print("\n=== ۱۵ خط اول ===")
for i, l in enumerate(lines[:15], 1):
    print(f"{i}: {l}")
