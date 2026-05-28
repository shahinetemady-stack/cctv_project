import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'admin', 'SaleInvoicePage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# پیدا کردن بخش خراب (دکمه‌های اضافه شده قبلی)
problem_start = None
problem_end = None
for i, line in enumerate(lines):
    if '{/* دکمه‌های خروجی */}' in line:
        problem_start = i
    if problem_start and '✕ بستن' in line:
        problem_end = i + 3  # تا بستن div و دکمه
        break

if problem_start and problem_end:
    print(f"حذف خطوط {problem_start+1} تا {problem_end+1}")
    del lines[problem_start:problem_end]
    print("✓ کد خراب حذف شد")

content = '\n'.join(lines)

# ─── اضافه کردن تابع printInvoice زیبا ────────────────────────
print_fn = '''
// ─── Print Beautiful Invoice ─────────────────────────────────
function printInvoice(inv, settings) {
  const items = inv.items || []
  const total = items.reduce((s, i) => s + (i.total_price || i.quantity * i.unit_price || 0), 0)
  const paid = inv.paid_amount || 0
  const remaining = total - paid

  const html = `
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8">
<title>فاکتور ${inv.invoice_number}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Tahoma, Arial, sans-serif; direction: rtl; color: #1a1a2e; background: #fff; padding: 30px; }
  .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #0066FF; padding-bottom: 20px; margin-bottom: 24px; }
  .company-info h1 { font-size: 22px; color: #0066FF; font-weight: bold; margin-bottom: 6px; }
  .company-info p { font-size: 12px; color: #666; line-height: 1.6; }
  .invoice-info { text-align: left; }
  .invoice-info h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 8px; }
  .invoice-info table { font-size: 12px; }
  .invoice-info td { padding: 3px 8px; }
  .invoice-info td:first-child { color: #666; }
  .invoice-info td:last-child { font-weight: bold; color: #0066FF; }
  .parties { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
  .party-box { border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }
  .party-box h3 { font-size: 11px; color: #999; margin-bottom: 8px; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; }
  .party-box p { font-size: 13px; font-weight: bold; color: #1a1a2e; }
  .party-box small { font-size: 11px; color: #666; }
  table.items { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
  table.items th { background: #0066FF; color: white; padding: 10px 12px; font-size: 12px; font-weight: bold; }
  table.items td { padding: 10px 12px; font-size: 12px; border-bottom: 1px solid #f0f0f0; }
  table.items tr:nth-child(even) { background: #f8f9ff; }
  table.items tfoot td { font-weight: bold; background: #f8f9ff; border-top: 2px solid #0066FF; }
  .totals { display: flex; justify-content: flex-end; margin-bottom: 24px; }
  .totals table { font-size: 13px; }
  .totals td { padding: 6px 12px; }
  .totals tr.total td { font-size: 16px; font-weight: bold; color: #0066FF; background: #f0f5ff; border-radius: 4px; }
  .totals tr.paid td { color: #00a651; }
  .totals tr.remaining td { color: #e53935; }
  .footer { border-top: 1px solid #e0e0e0; padding-top: 16px; display: flex; justify-content: space-between; font-size: 11px; color: #999; }
  .stamp { text-align: center; margin-top: 40px; }
  .stamp-box { display: inline-block; border: 2px dashed #ccc; border-radius: 50%; width: 100px; height: 100px; line-height: 100px; color: #ccc; font-size: 11px; }
  @media print {
    body { padding: 15px; }
    @page { margin: 1cm; }
  }
</style>
</head>
<body>
<div class="header">
  <div class="company-info">
    <h1>🎥 ${settings?.site_name || 'فروشگاه قطعات دوربین'}</h1>
    <p>${settings?.contact_address || ''}</p>
    <p>📞 ${settings?.contact_phone || ''} | ساعات کاری: ${settings?.working_hours || ''}</p>
  </div>
  <div class="invoice-info">
    <h2>فاکتور فروش</h2>
    <table>
      <tr><td>شماره فاکتور:</td><td>${inv.invoice_number}</td></tr>
      <tr><td>تاریخ:</td><td>${inv.date || inv.created_at?.split('T')[0] || ''}</td></tr>
      <tr><td>وضعیت:</td><td>${inv.status_display || inv.status || ''}</td></tr>
    </table>
  </div>
</div>

<div class="parties">
  <div class="party-box">
    <h3>فروشنده</h3>
    <p>${settings?.site_name || 'فروشگاه قطعات دوربین'}</p>
    <small>${settings?.contact_phone || ''}</small>
  </div>
  <div class="party-box">
    <h3>خریدار</h3>
    <p>${inv.contact_name || inv.contact || 'مشتری'}</p>
    <small>${inv.contact_phone || ''}</small>
  </div>
</div>

<table class="items">
  <thead>
    <tr>
      <th>#</th>
      <th>نام کالا</th>
      <th>تعداد</th>
      <th>قیمت واحد (ت)</th>
      <th>جمع (ت)</th>
    </tr>
  </thead>
  <tbody>
    ${items.map((item, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${item.variant_name || item.product_name || ''}</td>
        <td>${Number(item.quantity || 0).toLocaleString('fa-IR')}</td>
        <td>${Number(item.unit_price || 0).toLocaleString('fa-IR')}</td>
        <td>${Number(item.total_price || (item.quantity * item.unit_price) || 0).toLocaleString('fa-IR')}</td>
      </tr>
    `).join('')}
  </tbody>
</table>

<div class="totals">
  <table>
    <tr class="total"><td>جمع کل:</td><td>${Number(total).toLocaleString('fa-IR')} تومان</td></tr>
    ${paid > 0 ? `<tr class="paid"><td>پرداخت شده:</td><td>${Number(paid).toLocaleString('fa-IR')} تومان</td></tr>` : ''}
    ${remaining > 0 ? `<tr class="remaining"><td>مانده:</td><td>${Number(remaining).toLocaleString('fa-IR')} تومان</td></tr>` : ''}
  </table>
</div>

${inv.note ? `<div style="background:#fffbf0;border:1px solid #ffe082;border-radius:8px;padding:12px;margin-bottom:20px;font-size:12px"><strong>توضیحات:</strong> ${inv.note}</div>` : ''}

<div class="footer">
  <span>این فاکتور به صورت کامپیوتری صادر شده است</span>
  <div class="stamp"><div class="stamp-box">مهر و<br>امضا</div></div>
  <span>${settings?.site_name || ''} | ${settings?.contact_phone || ''}</span>
</div>
</body>
</html>`

  const win = window.open('', '_blank', 'width=900,height=700')
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => win.print(), 600)
}

'''

# اضافه کردن قبل از export default
if 'printInvoice' not in content:
    content = content.replace(
        'export default function SaleInvoicePage',
        print_fn + 'export default function SaleInvoicePage'
    )
    print("✓ printInvoice اضافه شد")

# پیدا کردن و اضافه کردن دکمه‌ها در InvoiceDetail
# ابتدا پیدا کردن api settings در InvoiceDetail
lines = content.split('\n')
for i in range(197, min(230, len(lines))):
    print(f"{i+1}: {lines[i]}")
