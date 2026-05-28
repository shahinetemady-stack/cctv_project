import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
app_path = os.path.join(FRONTEND, 'App.jsx')

with open(app_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن route قبل از <Route element={<Layout />}>
# این route باید خارج از Layout باشد
old = '      <Route element={<Layout />}>'
new = '      <Route path="invoice-print" element={<InvoicePrintPage />} />\n      <Route element={<Layout />}>'

if 'invoice-print' not in content:
    content = content.replace(old, new)
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Route اضافه شد")
else:
    print("✓ Route قبلاً موجود بود")

# تایید
print("invoice-print in App:", 'invoice-print' in content)
