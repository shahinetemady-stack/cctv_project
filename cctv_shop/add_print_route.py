import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# کپی InvoicePrintPage.jsx
src = os.path.join('..', '..', 'outputs', 'InvoicePrintPage.jsx') if not os.path.exists('InvoicePrintPage.jsx') else 'InvoicePrintPage.jsx'

# اضافه کردن route به App.jsx
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'InvoicePrintPage' not in app:
    # اضافه کردن import
    app = app.replace(
        "import SaleInvoicePage",
        "import InvoicePrintPage from './pages/admin/InvoicePrintPage'\nimport SaleInvoicePage"
    )
    # اضافه کردن route — این route باید بیرون از Layout باشد
    app = app.replace(
        '<Route path="/" element={<Layout />}>',
        '<Route path="invoice-print" element={<InvoicePrintPage />} />\n      <Route path="/" element={<Layout />}>'
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ Route اضافه شد")
else:
    print("✓ قبلاً موجود بود")

print("✓ آماده — فایل InvoicePrintPage.jsx را در src/pages/admin/ کپی کنید")
