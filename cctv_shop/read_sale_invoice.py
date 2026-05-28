import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

print("Lines:", content.count('\n'))
print("Has PDF:", 'pdf' in content.lower())
print("Has print:", 'print' in content.lower())
print("Has contact:", 'contact' in content.lower())
print("Has quick add:", 'quick' in content.lower() or 'سریع' in content)

lines = content.split('\n')
print("\n=== ۲۵ خط اول ===")
for i, l in enumerate(lines[:25], 1):
    print(f"{i}: {l}")

print("\n=== آخر فایل ===")
for i, l in enumerate(lines[-20:], len(lines)-20):
    print(f"{i}: {l}")
