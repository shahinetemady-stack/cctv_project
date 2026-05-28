import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# پیدا کردن InvoiceDetail
detail_start = None
for i, line in enumerate(lines):
    if 'function InvoiceDetail' in line:
        detail_start = i
        print(f"InvoiceDetail starts at line {i+1}")
        break

if detail_start:
    # نمایش ۵۰ خط آخر InvoiceDetail (نزدیک به return)
    detail_lines = lines[detail_start:]
    # پیدا کردن آخرین return
    for i in range(len(detail_lines)-1, 0, -1):
        if 'return' in detail_lines[i] or 'onClose' in detail_lines[i] or 'button' in detail_lines[i].lower():
            print(f"line {detail_start+i+1}: {repr(detail_lines[i])}")
            if detail_start + i > detail_start + 200:
                break

    # نمایش ۳۰ خط آخر تابع
    print("\n=== آخر InvoiceDetail ===")
    end_idx = None
    depth = 0
    for i, line in enumerate(detail_lines):
        depth += line.count('{') - line.count('}')
        if i > 5 and depth <= 0:
            end_idx = i
            break

    if end_idx:
        for i, line in enumerate(detail_lines[max(0,end_idx-30):end_idx+1], detail_start+max(0,end_idx-30)+1):
            print(f"{i}: {line}")
