import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# حذف خط مشکل‌دار
new_lines = []
for i, line in enumerate(lines):
    if 'showPrint' in line or 'InvoicePrintView' in line:
        print(f"حذف خط {i+1}: {line.strip()}")
        continue
    new_lines.append(line)

content = '\n'.join(new_lines)

# اضافه کردن useState showPrint به InvoiceDetail اگر نبود
# و اضافه کردن دکمه پرینت ساده

# پیدا کردن دکمه بستن که الان داریم
if '✕ بستن' in content:
    # اضافه کردن دکمه پرینت قبل از بستن
    content = content.replace(
        '''        <button onClick={onClose}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs transition-all mr-auto">
          ✕ بستن
        </button>''',
        '''        <button onClick={() => printInvoice(inv, null)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand/20 hover:bg-brand/30 text-brand text-xs transition-all">
          🖨️ پرینت / PDF
        </button>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs transition-all mr-auto">
          ✕ بستن
        </button>'''
    )
    print("✓ دکمه پرینت اضافه شد")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"✓ فایل ذخیره شد ({content.count(chr(10))} خط)")
