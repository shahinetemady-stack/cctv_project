import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# اضافه کردن دکمه‌های print/PDF قبل از بستن InvoiceDetail (خط ۴۱۹-۴۲۱)
# پیدا کردن خط "  )\n}"  در InvoiceDetail
# InvoiceDetail از خط ۱۹۸ شروع می‌شود

# پیدا کردن محل درست
for i in range(415, 425):
    print(f"{i+1}: {repr(lines[i])}")

print("\n--- اضافه کردن دکمه‌ها ---")

# اضافه کردن قبل از خط ۴۱۹ (  ) )
print_section = """
      {/* دکمه‌های خروجی */}
      <div className="flex gap-2 mt-4 pt-4 border-t border-white/10">
        <button onClick={() => window.print()}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs transition-all">
          🖨️ پرینت
        </button>
        <button onClick={() => {
          const style = document.createElement('style')
          style.innerHTML = '@media print { body * { visibility: hidden; } .invoice-print, .invoice-print * { visibility: visible; } .invoice-print { position: absolute; left: 0; top: 0; width: 100%; } }'
          document.head.appendChild(style)
          window.print()
          setTimeout(() => document.head.removeChild(style), 1000)
        }} className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs transition-all">
          📄 PDF
        </button>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand/20 hover:bg-brand/30 text-brand text-xs transition-all mr-auto">
          ✕ بستن
        </button>
      </div>"""

# اضافه کردن قبل از خط ۴۱۹ (    </div>)
target_line = 418  # index 0-based = line 419
lines.insert(target_line, print_section)

content = '\n'.join(lines)

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ دکمه‌های print/PDF و بستن اضافه شدند")
print(f"New total lines: {content.count(chr(10))}")
