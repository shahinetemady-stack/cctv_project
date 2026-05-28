"""
این اسکریپت را داخل cctv_shop بگذارید و اجرا کنید:
python fix_invoice_final.py
"""
import os, sys

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

if not os.path.exists(page_path):
    print("خطا: فایل پیدا نشد:", page_path)
    sys.exit(1)

with open(page_path, encoding='utf-8') as f:
    content = f.read()

print(f"فایل خوانده شد: {content.count(chr(10))} خط")

changed = False

# ─── 1. دکمه + جدید در dropdown ──────────────────────────────
if '+ جدید' not in content:
    # پیدا کردن input جستجو در picker
    old = '                placeholder="جستجو..." className="input text-xs w-full"\n                onClick={e => e.stopPropagation()} />'
    new = '                placeholder="جستجو..." className="input text-xs flex-1"\n                onClick={e => e.stopPropagation()} />\n              <button\n                onClick={e => { e.stopPropagation(); setOpen(false); setShowQuickAdd(true) }}\n                className="text-xs px-3 py-1.5 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 font-bold whitespace-nowrap">\n                + جدید\n              </button>'
    if old in content:
        content = content.replace(old, new)
        # تغییر div wrapper به flex
        content = content.replace(
            '<div className="p-2 border-b border-white/10">\n              <input autoFocus',
            '<div className="p-2 border-b border-white/10 flex gap-2 items-center">\n              <input autoFocus'
        )
        print("✓ دکمه + جدید اضافه شد")
        changed = True
    else:
        print("✗ input جستجو پیدا نشد — بررسی دستی لازم است")

# ─── 2. دکمه‌های print/PDF در InvoiceDetail ──────────────────
if '<InvoicePrintExport' not in content:
    # پیدا کردن خط دکمه بستن
    lines = content.split('\n')
    close_line_idx = None
    for i, line in enumerate(lines):
        if 'بستن' in line and 'button' in line and 'onClose' in line:
            close_line_idx = i
            print(f"دکمه بستن در خط {i+1}: {line.strip()}")
            break

    if close_line_idx:
        # اضافه کردن دکمه‌ها قبل از دکمه بستن
        print_buttons = '''      <div className="flex gap-2">
        <button onClick={() => window.print()}
          className="flex items-center gap-1 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs">
          🖨️ پرینت
        </button>
        <button onClick={() => {
          const el = document.querySelector('.invoice-content')
          if (!el) return alert('محتوای فاکتور پیدا نشد')
          const win = window.open('', '_blank')
          win.document.write('<html dir="rtl"><head><meta charset="utf-8"><style>body{font-family:Tahoma;padding:20px;color:#000}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px;text-align:right}</style></head><body>' + el.innerHTML + '</body></html>')
          win.document.close()
          setTimeout(() => { win.print() }, 300)
        }} className="flex items-center gap-1 px-3 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs">
          📄 PDF/Print
        </button>
      </div>'''
        lines.insert(close_line_idx, print_buttons)
        content = '\n'.join(lines)
        print("✓ دکمه‌های print/PDF اضافه شدند")
        changed = True
    else:
        print("✗ دکمه بستن پیدا نشد")
        # نمایش تمام خطوط با بستن
        for i, line in enumerate(lines):
            if 'بستن' in line:
                print(f"  خط {i+1}: {line.strip()}")

if changed:
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n✓ فایل ذخیره شد")
else:
    print("\n✗ هیچ تغییری اعمال نشد")
