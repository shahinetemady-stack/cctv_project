import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن STATUS_COLORS اگر نبود
if 'STATUS_COLORS' not in content:
    status_colors = """
const STATUS_COLORS = {
  draft:     { bg: '#374151', text: '#9CA3AF', label: 'پیش‌نویس' },
  issued:    { bg: '#1e3a5f', text: '#60A5FA', label: 'صادر شده' },
  paid:      { bg: '#064e3b', text: '#34D399', label: 'پرداخت شده' },
  partial:   { bg: '#4c1d95', text: '#A78BFA', label: 'پرداخت جزئی' },
  cancelled: { bg: '#7f1d1d', text: '#F87171', label: 'لغو شده' },
}

"""
    # اضافه کردن بعد از fmt function
    content = content.replace(
        'function fmt(n)',
        status_colors + 'function fmt(n)'
    )
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ STATUS_COLORS اضافه شد")
else:
    print("✓ STATUS_COLORS موجود است")

import subprocess, sys
# تست syntax
r = subprocess.run(['node', '--check', page_path], capture_output=True, text=True)
if r.returncode == 0:
    print("✓ syntax درست است")
else:
    print("✗ خطای syntax:", r.stderr[-200:])
