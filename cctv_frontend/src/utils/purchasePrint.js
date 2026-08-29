// ساخت HTML پرینت فاکتور خرید — با همان مکانیزم صفحه /invoice-print
// (ذخیره در localStorage و باز شدن در تب جدید)
import { formatDate } from './date'

const fmt = (n) => Number(n || 0).toLocaleString('fa-IR')

export function buildPurchasePrintHTML(inv) {
  const isDomestic = inv.purchase_type === 'domestic'
  const itemsRows = (inv.items || []).map((it, i) => `
    <tr>
      <td>${i + 1}</td>
      <td style="text-align:right">${it.product_name}<div class="sku">${it.variant_sku || ''}</div></td>
      <td>${fmt(it.quantity)}</td>
      ${isDomestic ? '' : `<td>${fmt(it.carton_count)}</td>`}
      <td>${isDomestic ? `${fmt(it.unit_price_irr)} ریال` : `${fmt(it.unit_price_cny)} ¥`}</td>
      <td>${isDomestic ? `${fmt((it.unit_price_irr || 0) * (it.quantity || 0))} ریال` : `${fmt((it.unit_price_cny || 0) * (it.quantity || 0))} ¥`}</td>
    </tr>`).join('')

  const totalLine = isDomestic
    ? `<div class="total-row"><span>جمع کل فاکتور:</span><b>${fmt(inv.total_irr)} ریال</b></div>`
    : `<div class="total-row"><span>جمع یوان:</span><b>${fmt(inv.total_cny)} ¥</b></div>
       <div class="total-row"><span>جمع ریال (با حمل و ترخیص):</span><b>${fmt(inv.total_irr)} ریال</b></div>`

  return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>فاکتور خرید ${inv.invoice_number || '#' + inv.id}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Tahoma, 'Segoe UI', sans-serif; background: #fff; color: #111; padding: 24px; font-size: 13px; }
  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #FBC02D; padding-bottom: 12px; margin-bottom: 16px; }
  .title { font-size: 20px; font-weight: bold; }
  .type-badge { display: inline-block; background: ${isDomestic ? '#e8f5e9' : '#e3f2fd'}; color: ${isDomestic ? '#2e7d32' : '#1565c0'}; border-radius: 20px; padding: 3px 12px; font-size: 11px; margin-right: 8px; }
  .meta { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; background: #faf8f3; border: 1px solid #eee; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; }
  .meta div { font-size: 12px; }
  .meta b { display: inline-block; min-width: 80px; color: #666; font-weight: normal; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th { background: #222; color: #FBC02D; padding: 8px 10px; font-size: 12px; text-align: center; }
  td { border-bottom: 1px solid #eee; padding: 8px 10px; text-align: center; font-size: 12px; }
  .sku { color: #888; font-size: 10px; direction: ltr; }
  .totals { margin-left: auto; width: 320px; border: 1px solid #eee; border-radius: 10px; overflow: hidden; }
  .total-row { display: flex; justify-content: space-between; padding: 10px 14px; font-size: 13px; }
  .total-row:nth-child(odd) { background: #faf8f3; }
  .total-row b { color: #b8860b; }
  .note { border: 1px dashed #ccc; border-radius: 10px; padding: 10px 14px; font-size: 12px; color: #555; margin-top: 12px; }
  .footer { margin-top: 24px; text-align: center; color: #999; font-size: 10px; border-top: 1px solid #eee; padding-top: 10px; }
</style>
</head>
<body>
  <div class="header">
    <div>
      <span class="title">فاکتور خرید ${inv.invoice_number || '#' + inv.id}</span>
      <span class="type-badge">${inv.purchase_type_display || ''}</span>
    </div>
    <div>تاریخ: ${formatDate(inv.date)}</div>
  </div>

  <div class="meta">
    <div><b>تامین‌کننده:</b> ${inv.supplier?.name || '—'}</div>
    <div><b>وضعیت:</b> ${inv.status_display || ''}</div>
    <div><b>انبار:</b> ${inv.warehouse?.name || '—'}${inv.warehouse_destination ? ' ← ' + inv.warehouse_destination.name : ''}</div>
    ${inv.shipping_contact ? `<div><b>شرکت حمل:</b> ${inv.shipping_contact.name}</div>` : ''}
    ${!isDomestic && inv.rate_purchase_cny ? `<div><b>نرخ یوان خرید:</b> ${fmt(inv.rate_purchase_cny)} ریال</div>` : ''}
    ${inv.received_at ? `<div><b>تاریخ رسیدن:</b> ${formatDate(inv.received_at)}</div>` : ''}
  </div>

  <table>
    <thead>
      <tr>
        <th>#</th><th>کالا</th><th>تعداد</th>${isDomestic ? '' : '<th>کارتن</th>'}<th>قیمت واحد</th><th>جمع</th>
      </tr>
    </thead>
    <tbody>${itemsRows}</tbody>
  </table>

  <div class="totals">${totalLine}</div>

  ${inv.note ? `<div class="note"><b>توضیحات:</b> ${inv.note}</div>` : ''}

  <div class="footer">دوربینکار — سامانه مدیریت فروش قطعات دوربین مداربسته</div>
</body>
</html>`
}

export function printPurchaseInvoice(inv) {
  localStorage.setItem('invoice_print_html', buildPurchasePrintHTML(inv))
  const win = window.open(window.location.origin + '/invoice-print', '_blank', 'width=1050,height=800')
  if (!win) alert('لطفاً Pop-up را در مرورگر فعال کنید')
  else win.focus()
}
