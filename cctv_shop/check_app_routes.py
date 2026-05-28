import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
app_path = os.path.join(FRONTEND, 'App.jsx')

with open(app_path, encoding='utf-8') as f:
    content = f.read()

print("InvoicePrintPage in App:", 'InvoicePrintPage' in content)
print("invoice-print in App:", 'invoice-print' in content)

# نمایش ساختار routes
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'Route' in line or 'InvoicePrint' in line:
        print(f"{i+1}: {line.strip()[:100]}")
