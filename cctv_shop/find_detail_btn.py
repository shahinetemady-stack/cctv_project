import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# پیدا کردن همه خطوط با بستن/onClose
print("=== خطوط با بستن ===")
for i, line in enumerate(lines, 1):
    if 'بستن' in line:
        print(f"{i}: {repr(line)}")

# پیدا کردن InvoiceDetail function
print("\n=== InvoiceDetail header lines ===")
for i, line in enumerate(lines, 1):
    if 'function InvoiceDetail' in line:
        print(f"{i}: {line}")
        # نمایش ۵ خط بعد
        for j in range(1, 6):
            print(f"{i+j}: {lines[i+j-1]}")
