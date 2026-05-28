import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'بستن' in line or ('onClose' in line and 'btn' in line):
        # نمایش ۵ خط قبل و بعد
        start = max(0, i-4)
        end = min(len(lines), i+3)
        print(f"\n=== خط {i} ===")
        for j in range(start, end):
            print(f"{j+1}: {lines[j]}", end='')
