import os, re

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# پیدا کردن همه بخش‌های اضافه شده مشکل‌دار و حذف آن‌ها
# ۱. حذف printInvoice function (که داخل فایل به اشتباه جا گرفته)
# ۲. حذف InvoicePrintExport
# ۳. حذف QuickContactModal
# ۴. حذف دکمه‌های اضافه

# روش ساده: پیدا کردن خطوط بین markers
bad_patterns = [
    '// ─── Print Beautiful Invoice',
    '// ─── PDF / Print Export',
    '// ─── Quick Contact Creator Modal',
    '{/* دکمه‌های خروجی */}',
    'function printInvoice(',
    'function InvoicePrintExport(',
    'function QuickContactModal(',
    'InvoicePrintView',
]

# بررسی وجود هر pattern
for p in bad_patterns:
    count = content.count(p)
    if count > 0:
        print(f"Found: '{p}' ({count} times)")

# پیدا کردن شروع کد اضافه شده
# اولین چیز اضافه شده QuickContactModal است
quick_idx = content.find('// ─── Quick Contact Creator Modal')
print_idx = content.find('// ─── Print Beautiful Invoice')
pdf_idx = content.find('// ─── PDF / Print Export')

markers = [i for i in [quick_idx, print_idx, pdf_idx] if i >= 0]
if markers:
    first_bad = min(markers)
    print(f"\nFirst bad code at position: {first_bad}")
    print(f"Context: {repr(content[first_bad:first_bad+100])}")

    # پیدا کردن export default function SaleInvoicePage
    export_idx = content.rfind('export default function SaleInvoicePage')
    print(f"export default at: {export_idx}")

    if export_idx > first_bad:
        # حذف همه چیز بین first_bad و export default
        clean_content = content[:first_bad] + content[export_idx:]
        print(f"✓ حذف {export_idx - first_bad} کاراکتر از کد اضافه")
    else:
        # printInvoice بعد از export است
        clean_content = content
        # حذف printInvoice که داخل فایل به اشتباه جا گرفته
        for bad in bad_patterns:
            if bad in clean_content:
                idx = clean_content.find(bad)
                # پیدا کردن پایان تابع
                next_fn = clean_content.find('\nexport default', idx)
                if next_fn < 0:
                    next_fn = clean_content.find('\nfunction ', idx + 100)
                if next_fn > idx:
                    removed = clean_content[idx:next_fn]
                    clean_content = clean_content[:idx] + clean_content[next_fn:]
                    print(f"✓ حذف: {bad}")

    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(clean_content)
    print(f"✓ فایل ذخیره شد ({clean_content.count(chr(10))} خط)")
else:
    print("هیچ کد اضافه‌ای پیدا نشد")
