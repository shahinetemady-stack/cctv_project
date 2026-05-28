import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# بررسی همه قابلیت‌ها
print("QuickContactModal:", 'QuickContactModal' in content)
print("showQuickAdd:", 'showQuickAdd' in content)
print("+ جدید:", '+ جدید' in content)
print("InvoicePrintExport:", 'InvoicePrintExport' in content)
print("<InvoicePrintExport:", '<InvoicePrintExport' in content)
print("invoiceRef:", 'invoiceRef' in content)
print("handlePrint:", 'handlePrint' in content)

# پیدا کردن محل دکمه بستن در InvoiceDetail
idx = content.find('function InvoiceDetail')
if idx >= 0:
    detail = content[idx:idx+5000]
    close_idx = detail.find('بستن')
    if close_idx >= 0:
        print("\n=== محل دکمه بستن ===")
        print(detail[close_idx-200:close_idx+100])
