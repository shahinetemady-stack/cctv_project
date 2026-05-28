import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن بخش open && در ThirdPartyPicker
idx = content.find('showQuickAdd')
if idx >= 0:
    print("showQuickAdd found at:", idx)
    # نمایش ۵۰ خط بعد از ThirdPartyPicker
    picker_idx = content.find('function ThirdPartyPicker')
    lines = content[picker_idx:picker_idx+2000].split('\n')
    for i, l in enumerate(lines[:60], 1):
        print(f"{i}: {l}")
