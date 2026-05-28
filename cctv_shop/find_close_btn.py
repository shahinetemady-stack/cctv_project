import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن محل دکمه بستن در InvoiceDetail
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'بستن' in line or 'onClose' in line:
        print(f"{i}: {line}")
