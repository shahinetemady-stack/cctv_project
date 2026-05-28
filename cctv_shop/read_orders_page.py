import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'account', 'OrdersPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

print("Lines:", content.count('\n'))
print("Has tracking:", 'track' in content.lower())
print("Has Link:", 'Link' in content)

lines = content.split('\n')
print("\n=== آخر فایل ===")
for i, line in enumerate(lines[-25:], len(lines)-25):
    print(f"{i}: {line}")
