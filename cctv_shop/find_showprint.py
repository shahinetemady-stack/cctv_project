import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# نمایش خطوط ۴۲۵-۴۴۰
print("=== خطوط مشکل‌دار ===")
for i, line in enumerate(lines[424:445], 425):
    print(f"{i}: {line}")
