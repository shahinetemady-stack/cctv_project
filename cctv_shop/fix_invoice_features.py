import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن دکمه + جدید بعد از input جستجو
old = """            <div className="p-2 border-b border-white/10">
              <input autoFocus value={search} onChange={e => setSearch(e.target.value)}
                placeholder="جستجو..." className="input text-xs w-full"
                onClick={e => e.stopPropagation()} />
            </div>"""

new = """            <div className="p-2 border-b border-white/10 flex gap-2">
              <input autoFocus value={search} onChange={e => setSearch(e.target.value)}
                placeholder="جستجو..." className="input text-xs flex-1"
                onClick={e => e.stopPropagation()} />
              <button
                onClick={e => { e.stopPropagation(); setOpen(false); setShowQuickAdd(true) }}
                className="text-xs px-3 py-1.5 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 transition-colors whitespace-nowrap font-bold">
                + جدید
              </button>
            </div>"""

if old in content:
    content = content.replace(old, new)
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ دکمه + جدید اضافه شد")
else:
    print("✗ پیدا نشد")

# بررسی InvoicePrintExport و دکمه‌های آن
if 'InvoicePrintExport' in content:
    print("✓ InvoicePrintExport موجود است")
    # چک کردن که آیا در InvoiceDetail استفاده شده
    idx = content.find('<InvoicePrintExport')
    if idx >= 0:
        print("✓ در InvoiceDetail استفاده شده")
        print(content[idx:idx+100])
    else:
        print("✗ در InvoiceDetail استفاده نشده — اضافه می‌کنیم")
        # پیدا کردن دکمه بستن در InvoiceDetail
        old_btn = '      <button onClick={onClose} className="btn-secondary text-sm px-4 py-2">بستن</button>'
        new_btn = '      <InvoicePrintExport invoiceRef={invoiceRef} invoiceNumber={invoice?.invoice_number || id} />\n      <button onClick={onClose} className="btn-secondary text-sm px-4 py-2">بستن</button>'
        if old_btn in content:
            content = content.replace(old_btn, new_btn)
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✓ دکمه‌های PDF/Print اضافه شدند")
