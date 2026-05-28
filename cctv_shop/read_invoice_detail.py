import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# نمایش InvoiceDetail از خط ۱۹۸ تا ۲۵۰
print("=== InvoiceDetail (lines 198-260) ===")
for i, line in enumerate(lines[197:260], 198):
    print(f"{i}: {line}")
