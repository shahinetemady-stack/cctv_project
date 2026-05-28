import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_COLORS = {
  draft: '#888', confirmed: '#0066FF', paid: '#00C896', cancelled: '#FF3B3B',
}
const STATUS_LABELS = {
  draft: 'پیش‌نویس', confirmed: 'تأیید شده', paid: 'تسویه شده', cancelled: 'لغو شده',
}

const INVOICE_SKINS = [
  { id: 'skin1', label: 'قرمز-آبی', emoji: '🔴' },
  { id: 'skin2', label: 'طلایی-تیره', emoji: '🟡' },
  { id: 'skin3', label: 'قرمز-مشکی', emoji: '⚫' },
  { id: 'skin4', label: 'نارنجی-دریایی', emoji: '🟠' },
]

function buildInvoiceHTML(inv, skin, company) {
  const items = inv.items || []
  const rows = items.map((x, i) =>
    `<tr>
      <td style="text-align:center">${i + 1}</td>
      <td>${x.product_name || ''}</td>
      <td style="text-align:center">${x.quantity || 0}</td>
      <td style="text-align:left">${Number(x.unit_price || 0).toLocaleString()}</td>
      <td style="text-align:left;font-weight:700">${Number(x.subtotal || 0).toLocaleString()}</td>
    </tr>`
  ).join('')

  const logoHTML = company.logoUrl
    ? `<img src="${company.logoUrl}" style="height:50px;object-fit:contain" />`
    : `<div style="width:50px;height:50px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:22px;background:rgba(255,255,255,0.2)">🎥</div>`

  const skins = {
    skin1: {
      css: `
        body{font-family:Tahoma;direction:rtl;margin:0;padding:0;color:#222;background:#fff}
        .hdr{background:linear-gradient(135deg,#c0392b,#2980b9);padding:0;position:relative;overflow:hidden;height:120px}
        .hdr-left{position:absolute;right:0;top:0;width:55%;height:100%;background:#c0392b;clip-path:polygon(0 0,100% 0,85% 100%,0 100%);display:flex;align-items:center;padding:0 30px;gap:14px}
        .hdr-right{position:absolute;left:0;top:0;width:50%;height:100%;background:#2980b9;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;padding:0 30px}
        .company-name{font-size:20px;font-weight:900;color:white;letter-spacing:1px}
        .company-sub{font-size:10px;color:rgba(255,255,255,0.8);margin-top:2px}
        .inv-title{font-size:28px;font-weight:900;color:white;letter-spacing:3px}
        .inv-num{font-size:12px;color:rgba(255,255,255,0.85);margin-top:4px}
        .body{padding:24px 30px}
        .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:22px}
        .info-box{border:1px solid #e0e0e0;border-radius:6px;padding:12px 16px}
        .info-box h4{font-size:10px;color:#c0392b;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px;border-bottom:1px solid #f0f0f0;padding-bottom:6px}
        .info-box p{margin:3px 0;font-size:13px;color:#333}
        .info-box .name{font-size:15px;font-weight:700;color:#111}
        table{width:100%;border-collapse:collapse;margin-bottom:22px}
        thead tr{background:#2980b9}
        th{color:white;padding:10px 12px;font-size:11px;text-align:right}
        td{padding:10px 12px;border-bottom:1px solid #f0f0f0;font-size:12px}
        tr:nth-child(even) td{background:#f7faff}
        .totals{display:flex;justify-content:flex-end;margin-bottom:22px}
        .totals table{min-width:260px;border:1px solid #e0e0e0;border-radius:6px;overflow:hidden}
        .totals th{background:#c0392b;color:white;padding:10px 14px;text-align:right}
        .totals td{padding:9px 14px;border-bottom:1px solid #f0f0f0}
        .tot-main td{font-size:16px;font-weight:900;color:#c0392b}
        .tot-paid td{color:#059669}
        .tot-rem td{color:#e74c3c;font-weight:700}
        .ftr{background:#2980b9;color:white;padding:14px 30px;display:flex;justify-content:space-between;align-items:center;font-size:11px}
        .stamp{border:2px dashed rgba(255,255,255,0.4);border-radius:50%;width:75px;height:75px;display:flex;align-items:center;justify-content:center;font-size:10px;text-align:center;color:rgba(255,255,255,0.6)}
        @media print{@page{margin:0};body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
      `,
      header: `
        <div class="hdr">
          <div class="hdr-left">${logoHTML}<div><div class="company-name">${company.name}</div><div class="company-sub">${company.address}</div><div class="company-sub">${company.phone}</div></div></div>
          <div class="hdr-right"><div class="inv-title">INVOICE</div><div class="inv-num">شماره: ${inv.invoice_number || ''}</div><div class="inv-num">تاریخ: ${inv.created_at || ''}</div></div>
        </div>
      `,
      footer: `<div class="ftr"><span>${company.name} | ${company.phone}</span><div class="stamp">مهر<br>و<br>امضا</div><span>این فاکتور رایانه‌ای است</span></div>`
    },

    skin2: {
      css: `
        body{font-family:Tahoma;direction:rtl;margin:0;padding:0;color:#222;background:#fff}
        .hdr{background:#1a1a2e;padding:24px 30px;display:flex;justify-content:space-between;align-items:center}
        .logo-area{display:flex;align-items:center;gap:12px}
        .company-name{font-size:18px;font-weight:900;color:#f0b429;letter-spacing:1px}
        .company-sub{font-size:10px;color:rgba(255,255,255,0.6);margin-top:2px}
        .inv-area{text-align:left}
        .inv-title{font-size:32px;font-weight:900;color:#f0b429;letter-spacing:2px}
        .inv-num{font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px}
        .divider{height:4px;background:linear-gradient(90deg,#f0b429,#e07b00)}
        .body{padding:24px 30px}
        .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px}
        .info-box{background:#f9f9f9;border-radius:8px;padding:14px 16px;border-right:4px solid #f0b429}
        .info-box h4{font-size:10px;color:#e07b00;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px}
        .info-box .name{font-size:15px;font-weight:800;color:#111}
        .info-box p{margin:3px 0;font-size:12px;color:#555}
        table{width:100%;border-collapse:collapse;margin-bottom:24px}
        thead tr{background:#1a1a2e}
        th{color:#f0b429;padding:11px 13px;font-size:11px;text-align:right;letter-spacing:0.5px}
        td{padding:10px 13px;border-bottom:1px solid #f0f0f0;font-size:12px}
        tr:nth-child(even) td{background:#fffdf5}
        .totals{display:flex;justify-content:flex-end;margin-bottom:24px}
        .totals table{min-width:260px;border-radius:8px;overflow:hidden;border:1px solid #e0e0e0}
        .totals th{background:#1a1a2e;color:#f0b429;padding:10px 14px;text-align:right}
        .totals td{padding:9px 14px;border-bottom:1px solid #f5f5f5}
        .tot-main td{font-size:17px;font-weight:900;color:#e07b00;background:#fffdf0}
        .tot-paid td{color:#059669}
        .tot-rem td{color:#dc2626;font-weight:700}
        .ftr{background:#1a1a2e;padding:16px 30px;display:flex;justify-content:space-between;align-items:center}
        .ftr-text{color:rgba(255,255,255,0.6);font-size:11px}
        .stamp{border:2px dashed #f0b429;border-radius:50%;width:75px;height:75px;display:flex;align-items:center;justify-content:center;font-size:10px;text-align:center;color:#f0b429}
        @media print{@page{margin:0};body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
      `,
      header: `
        <div class="hdr">
          <div class="logo-area">${logoHTML}<div><div class="company-name">${company.name}</div><div class="company-sub">${company.address}</div><div class="company-sub">${company.phone}</div></div></div>
          <div class="inv-area"><div class="inv-title">INVOICE</div><div class="inv-num">شماره: ${inv.invoice_number || ''}</div><div class="inv-num">تاریخ: ${inv.created_at || ''}</div></div>
        </div>
        <div class="divider"></div>
      `,
      footer: `<div class="ftr"><div class="ftr-text">${company.name}</div><div class="stamp">مهر<br>و<br>امضا</div><div class="ftr-text">این فاکتور رایانه‌ای است</div></div>`
    },

    skin3: {
      css: `
        body{font-family:Tahoma;direction:rtl;margin:0;padding:0;color:#222;background:#fff}
        .hdr{display:grid;grid-template-columns:1fr 1fr;min-height:110px}
        .hdr-r{background:#1a1a1a;padding:20px 30px;display:flex;flex-direction:column;justify-content:center}
        .hdr-l{background:#c0392b;padding:20px 30px;position:relative;display:flex;flex-direction:column;justify-content:center;align-items:flex-end;clip-path:polygon(15% 0,100% 0,100% 100%,0 100%)}
        .logo-area{display:flex;align-items:center;gap:12px;margin-bottom:8px}
        .company-name{font-size:18px;font-weight:900;color:white}
        .company-sub{font-size:10px;color:rgba(255,255,255,0.6);margin-top:1px}
        .inv-title{font-size:30px;font-weight:900;color:white;letter-spacing:3px}
        .inv-num{font-size:11px;color:rgba(255,255,255,0.85);margin-top:4px}
        .body{padding:24px 30px}
        .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:22px}
        .info-box{padding:12px 16px;border-bottom:2px solid #c0392b}
        .info-box h4{font-size:10px;color:#c0392b;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px}
        .info-box .name{font-size:15px;font-weight:800;color:#111}
        .info-box p{margin:3px 0;font-size:12px;color:#555}
        table{width:100%;border-collapse:collapse;margin-bottom:22px}
        thead tr{background:#1a1a1a}
        th{color:white;padding:11px 13px;font-size:11px;text-align:right}
        td{padding:10px 13px;border-bottom:1px solid #eee;font-size:12px}
        tr:nth-child(even) td{background:#fafafa}
        .totals{display:flex;justify-content:flex-end;margin-bottom:22px}
        .totals table{min-width:260px}
        .totals th{background:#c0392b;color:white;padding:10px 14px;text-align:right}
        .totals td{padding:9px 14px;border-bottom:1px solid #f0f0f0}
        .tot-main td{font-size:17px;font-weight:900;color:#c0392b;border-top:2px solid #c0392b}
        .tot-paid td{color:#059669}
        .tot-rem td{color:#dc2626;font-weight:700}
        .ftr{background:#1a1a1a;color:white;padding:14px 30px;display:flex;justify-content:space-between;align-items:center;font-size:11px}
        .stamp{border:2px dashed rgba(255,255,255,0.3);border-radius:50%;width:75px;height:75px;display:flex;align-items:center;justify-content:center;font-size:10px;text-align:center;color:rgba(255,255,255,0.4)}
        @media print{@page{margin:0};body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
      `,
      header: `
        <div class="hdr">
          <div class="hdr-r">
            <div class="logo-area">${logoHTML}<div><div class="company-name">${company.name}</div><div class="company-sub">${company.phone}</div></div></div>
            <div class="company-sub">${company.address}</div>
          </div>
          <div class="hdr-l">
            <div class="inv-title">INVOICE</div>
            <div class="inv-num">شماره: ${inv.invoice_number || ''}</div>
            <div class="inv-num">تاریخ: ${inv.created_at || ''}</div>
            <div class="inv-num">وضعیت: ${inv.status_display || ''}</div>
          </div>
        </div>
      `,
      footer: `<div class="ftr"><span>${company.name} | ${company.phone}</span><div class="stamp">مهر<br>و<br>امضا</div><span>این فاکتور رایانه‌ای است</span></div>`
    },

    skin4: {
      css: `
        body{font-family:Tahoma;direction:rtl;margin:0;padding:0;color:#222;background:#fff}
        .hdr{background:#1e3a5f;padding:22px 30px;position:relative;overflow:hidden}
        .hdr::after{content:'';position:absolute;bottom:-20px;left:-10px;width:220px;height:100px;background:#f97316;border-radius:60% 60% 0 0;transform:rotate(-5deg)}
        .hdr::before{content:'';position:absolute;top:-30px;left:60px;width:160px;height:120px;background:#f97316;border-radius:50%;opacity:0.4}
        .hdr-inner{display:flex;justify-content:space-between;align-items:center;position:relative;z-index:2}
        .logo-area{display:flex;align-items:center;gap:12px}
        .company-name{font-size:18px;font-weight:900;color:white}
        .company-sub{font-size:10px;color:rgba(255,255,255,0.7);margin-top:2px}
        .inv-area{text-align:left;background:rgba(255,255,255,0.1);backdrop-filter:blur(4px);padding:12px 20px;border-radius:10px}
        .inv-title{font-size:24px;font-weight:900;color:#f97316;letter-spacing:2px}
        .inv-num{font-size:11px;color:rgba(255,255,255,0.85);margin-top:3px}
        .spacer{height:30px}
        .body{padding:24px 30px}
        .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:22px}
        .info-box{border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;position:relative}
        .info-box::before{content:'';position:absolute;top:0;right:0;width:4px;height:100%;background:#f97316;border-radius:0 10px 10px 0}
        .info-box h4{font-size:10px;color:#f97316;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px}
        .info-box .name{font-size:15px;font-weight:800;color:#111}
        .info-box p{margin:3px 0;font-size:12px;color:#555}
        table{width:100%;border-collapse:collapse;margin-bottom:22px;border-radius:10px;overflow:hidden}
        thead tr{background:#1e3a5f}
        th{color:white;padding:11px 13px;font-size:11px;text-align:right}
        td{padding:10px 13px;border-bottom:1px solid #f0f0f0;font-size:12px}
        tr:nth-child(even) td{background:#fff8f5}
        .totals{display:flex;justify-content:flex-end;margin-bottom:22px}
        .totals table{min-width:260px;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb}
        .totals th{background:#1e3a5f;color:white;padding:10px 14px;text-align:right}
        .totals td{padding:9px 14px;border-bottom:1px solid #f5f5f5}
        .tot-main td{font-size:17px;font-weight:900;color:#f97316;background:#fff8f5}
        .tot-paid td{color:#059669}
        .tot-rem td{color:#dc2626;font-weight:700}
        .ftr{position:relative;overflow:hidden;background:#1e3a5f;padding:16px 30px}
        .ftr::after{content:'';position:absolute;bottom:-15px;right:-10px;width:120px;height:80px;background:#f97316;border-radius:50%}
        .ftr-inner{display:flex;justify-content:space-between;align-items:center;position:relative;z-index:2}
        .ftr-text{color:rgba(255,255,255,0.8);font-size:11px}
        .stamp{border:2px dashed rgba(255,255,255,0.4);border-radius:50%;width:75px;height:75px;display:flex;align-items:center;justify-content:center;font-size:10px;text-align:center;color:rgba(255,255,255,0.5)}
        @media print{@page{margin:0};body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
      `,
      header: `
        <div class="hdr">
          <div class="hdr-inner">
            <div class="logo-area">${logoHTML}<div><div class="company-name">${company.name}</div><div class="company-sub">${company.phone}</div><div class="company-sub">${company.address}</div></div></div>
            <div class="inv-area"><div class="inv-title">INVOICE</div><div class="inv-num">شماره: ${inv.invoice_number || ''}</div><div class="inv-num">تاریخ: ${inv.created_at || ''}</div></div>
          </div>
        </div>
        <div class="spacer"></div>
      `,
      footer: `<div class="ftr"><div class="ftr-inner"><div class="ftr-text">${company.name} | ${company.phone}</div><div class="stamp">مهر<br>و<br>امضا</div><div class="ftr-text">این فاکتور رایانه‌ای است</div></div></div>`
    }
  }

  const s = skins[skin] || skins.skin1

  return `<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8">
<title>فاکتور ${inv.invoice_number || ''}</title>
<style>${s.css}</style>
</head>
<body>
${s.header}
<div class="body">
  <div class="info-grid">
    <div class="info-box">
      <h4>فروشنده</h4>
      <div class="name">${company.name}</div>
      ${company.managerName ? `<p>مدیر: ${company.managerName}</p>` : ''}
      <p>${company.phone}</p>
      <p>${company.address}</p>
    </div>
    <div class="info-box">
      <h4>خریدار</h4>
      <div class="name">${inv.customer_name || ''}</div>
      <p>${inv.customer_phone || ''}</p>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="text-align:center;width:40px">#</th>
        <th>شرح کالا / خدمات</th>
        <th style="text-align:center;width:70px">تعداد</th>
        <th style="text-align:left;width:120px">قیمت واحد</th>
        <th style="text-align:left;width:120px">جمع</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>

  <div class="totals">
    <table>
      <thead><tr><th colspan="2">خلاصه مالی</th></tr></thead>
      <tbody>
        <tr class="tot-main"><td>جمع کل:</td><td>${Number(inv.total_amount || 0).toLocaleString()} تومان</td></tr>
        ${Number(inv.paid_amount) > 0 ? `<tr class="tot-paid"><td>پرداخت شده:</td><td>${Number(inv.paid_amount || 0).toLocaleString()} تومان</td></tr>` : ''}
        ${Number(inv.remaining_amount) > 0 ? `<tr class="tot-rem"><td>مانده بدهی:</td><td>${Number(inv.remaining_amount || 0).toLocaleString()} تومان</td></tr>` : ''}
      </tbody>
    </table>
  </div>

  ${inv.note ? `<div style="background:#fffbf0;border:1px solid #fde68a;border-radius:8px;padding:14px;margin-bottom:20px;font-size:12px"><b>توضیحات:</b> ${inv.note}</div>` : ''}
</div>
${s.footer}
</body>
</html>`
}

// ─── modal چاپ فاکتور با 4 طرح ───────────────────────────────
function PrintModal({ inv, onClose }) {
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 0,
  })

  const [skin, setSkin] = useState('skin1')
  const [company, setCompany] = useState({
    name: localStorage.getItem('inv_name') || '',
    managerName: localStorage.getItem('inv_manager') || '',
    phone: localStorage.getItem('inv_phone') || '',
    address: localStorage.getItem('inv_address') || '',
    logoUrl: settings?.site_logo || localStorage.getItem('inv_logo') || '',
  })

  // اگر settings لود شد، اطلاعات را پر کن
  const [initialized, setInitialized] = useState(false)
  if (settings && !initialized) {
    setInitialized(true)
    setCompany(c => ({
      ...c,
      name: c.name || settings.site_name || '',
      phone: c.phone || settings.contact_phone || '',
      address: c.address || settings.contact_address || '',
      logoUrl: settings.site_logo || c.logoUrl || '',
    }))
  }

  function saveAndPrint() {
    localStorage.setItem('inv_name', company.name)
    localStorage.setItem('inv_manager', company.managerName)
    localStorage.setItem('inv_phone', company.phone)
    localStorage.setItem('inv_address', company.address)
    if (company.logoUrl) localStorage.setItem('inv_logo', company.logoUrl)
    const html = buildInvoiceHTML(inv, skin, company)
    const win = window.open('', '_blank', 'width=1000,height=750')
    win.document.write(html)
    win.document.close()
    win.focus()
    setTimeout(() => win.print(), 600)
  }

  const skinColors = {
    skin1: { active: '#c0392b', bg: 'linear-gradient(135deg,#c0392b,#2980b9)' },
    skin2: { active: '#f0b429', bg: 'linear-gradient(135deg,#1a1a2e,#f0b429)' },
    skin3: { active: '#c0392b', bg: 'linear-gradient(135deg,#1a1a1a,#c0392b)' },
    skin4: { active: '#f97316', bg: 'linear-gradient(135deg,#1e3a5f,#f97316)' },
  }

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/80 p-4">
      <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-white text-lg">🖨️ چاپ / PDF فاکتور</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        {/* انتخاب طرح */}
        <div className="mb-5">
          <label className="label text-xs mb-3 block">طرح فاکتور</label>
          <div className="grid grid-cols-4 gap-3">
            {INVOICE_SKINS.map(s => (
              <button key={s.id} onClick={() => setSkin(s.id)}
                className={`rounded-xl border-2 overflow-hidden transition-all ${skin === s.id ? 'border-brand scale-105' : 'border-white/10 hover:border-white/30'}`}>
                <div style={{ background: skinColors[s.id].bg, height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span style={{ fontSize: 24 }}>{s.emoji}</span>
                </div>
                <div className="p-2 text-center">
                  <div className="text-xs text-white font-semibold">{s.label}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* اطلاعات شرکت */}
        <div className="mb-5 bg-white/5 rounded-xl p-4">
          <label className="label text-xs mb-3 block">اطلاعات فروشنده</label>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-[10px] mb-1 block">نام مجموعه *</label>
              <input value={company.name}
                onChange={e => setCompany(c => ({ ...c, name: e.target.value }))}
                className="input text-sm" placeholder="نام شرکت / فروشگاه" />
            </div>
            <div>
              <label className="label text-[10px] mb-1 block">نام مدیر</label>
              <input value={company.managerName}
                onChange={e => setCompany(c => ({ ...c, managerName: e.target.value }))}
                className="input text-sm" placeholder="نام و نام خانوادگی" />
            </div>
            <div>
              <label className="label text-[10px] mb-1 block">تلفن</label>
              <input value={company.phone}
                onChange={e => setCompany(c => ({ ...c, phone: e.target.value }))}
                className="input text-sm" dir="ltr" />
            </div>
            <div>
              <label className="label text-[10px] mb-1 block">آدرس</label>
              <input value={company.address}
                onChange={e => setCompany(c => ({ ...c, address: e.target.value }))}
                className="input text-sm" />
            </div>
          </div>
          <div className="mt-3">
            <label className="label text-[10px] mb-1 block">لوگو (URL تصویر یا از SiteSettings)</label>
            <div className="flex gap-2 items-center">
              <input value={company.logoUrl}
                onChange={e => setCompany(c => ({ ...c, logoUrl: e.target.value }))}
                className="input text-xs flex-1" dir="ltr" placeholder="https://... یا از تنظیمات سایت" />
              {company.logoUrl && (
                <img src={company.logoUrl} alt="logo"
                  className="w-10 h-10 object-contain rounded border border-white/20"
                  onError={e => e.target.style.display = 'none'} />
              )}
            </div>
            {settings?.site_logo && (
              <button onClick={() => setCompany(c => ({ ...c, logoUrl: settings.site_logo }))}
                className="text-xs text-brand mt-1">← استفاده از لوگوی سایت</button>
            )}
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={saveAndPrint} className="btn-primary flex-1 py-3 text-sm font-semibold">
            🖨️ پرینت / ذخیره PDF
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-3 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── جزئیات فاکتور ───────────────────────────────────────────
function InvoiceDetail({ id, onClose }) {
  const qc = useQueryClient()
  const [showPrint, setShowPrint] = useState(false)
  const { data: inv, isLoading } = useQuery({
    queryKey: ['sale-invoice', id],
    queryFn: () => api.get(`/accounting/sale-invoices/${id}/`).then(r => r.data),
  })
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })
  const [payForm, setPayForm] = useState({ show: false, method: 'transfer', amount: '', to_account_id: '', date: new Date().toISOString().split('T')[0], reference: '' })
  const [msg, setMsg] = useState(null)

  const payMut = useMutation({
    mutationFn: (d) => api.post('/accounting/sale-payments/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['sale-invoice', id])
      qc.invalidateQueries(['sale-invoices'])
      setPayForm(f => ({ ...f, show: false, amount: '', reference: '' }))
      setMsg({ type: 'success', text: 'پرداخت ثبت شد' })
      setTimeout(() => setMsg(null), 2000)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const statusMut = useMutation({
    mutationFn: (s) => api.patch(`/accounting/sale-invoices/${id}/`, { status: s }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(['sale-invoice', id]); qc.invalidateQueries(['sale-invoices']) },
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!inv) return null

  return (
    <div className="space-y-4">
      {showPrint && <PrintModal inv={inv} onClose={() => setShowPrint(false)} />}
      <div className="card p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-bold text-white text-xl">{inv.invoice_number}</h2>
            <div className="text-xs text-gray-steel mt-1">{inv.source_display} | {inv.created_by} | {inv.created_at}</div>
            <div className="text-sm text-white mt-1">{inv.customer_name} | {inv.customer_phone}</div>
            {inv.order_number && <div className="text-xs text-blue-400 mt-0.5">سفارش: {inv.order_number}</div>}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setShowPrint(true)}
              className="text-xs px-4 py-2 rounded-lg bg-brand/20 hover:bg-brand/30 text-brand transition-all font-semibold">
              🖨️ چاپ / PDF
            </button>
            <span style={{ color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20', padding: '4px 12px', borderRadius: 20, fontSize: 12 }}>
              {inv.status_display}
            </span>
            <button onClick={onClose} className="text-gray-steel hover:text-white">✕</button>
          </div>
        </div>
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: 'جمع کل', value: fmt(inv.subtotal) + ' ت', color: '#fff' },
            { label: 'تخفیف', value: fmt(inv.discount_amount) + ' ت', color: '#FF9500' },
            { label: 'مبلغ نهایی', value: fmt(inv.total_amount) + ' ت', color: '#0066FF' },
            { label: 'پرداخت شده', value: fmt(inv.paid_amount) + ' ت', color: '#00C896' },
            { label: 'مانده', value: fmt(inv.remaining_amount) + ' ت', color: inv.remaining_amount > 0 ? '#FF3B3B' : '#00C896' },
          ].map(item => (
            <div key={item.label} className="bg-white/5 rounded-lg p-3 text-center">
              <div className="text-[10px] text-gray-steel mb-1">{item.label}</div>
              <div className="text-sm font-bold" style={{ color: item.color }}>{item.value}</div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-4 text-xs">
          <span className="text-gray-steel">بهای تمام شده: <span className="text-white">{fmt(inv.total_cost)} ت</span></span>
          <span className="text-gray-steel">سود: <span className={inv.gross_profit >= 0 ? 'text-green-400' : 'text-red-400'}>{fmt(inv.gross_profit)} ت</span></span>
        </div>
        <div className="flex gap-2 mt-4">
          {['draft', 'confirmed', 'paid', 'cancelled'].map(s => (
            <button key={s} onClick={() => statusMut.mutate(s)} disabled={inv.status === s}
              style={{ borderColor: inv.status === s ? STATUS_COLORS[s] : 'transparent', color: STATUS_COLORS[s] }}
              className="text-xs px-3 py-1.5 rounded-lg border-2 bg-white/5 disabled:opacity-100 hover:bg-white/10 transition-all">
              {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-3">اقلام فاکتور</h3>
        <div className="overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['کالا', 'SKU', 'تعداد', 'قیمت واحد', 'تخفیف%', 'جمع', 'بهای تمام شده', 'سود'].map(h => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inv.items?.map((item, i) => (
                <tr key={item.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '8px 10px' }}>{item.product_name}</td>
                  <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{item.variant_sku}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>{fmt(item.quantity)}</td>
                  <td style={{ padding: '8px 10px' }}>{fmt(item.unit_price)}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'center', color: '#FF9500' }}>{item.discount_percent > 0 ? item.discount_percent + '%' : '—'}</td>
                  <td style={{ padding: '8px 10px', fontWeight: 600 }}>{fmt(item.subtotal)}</td>
                  <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)' }}>{fmt(item.total_cost)}</td>
                  <td style={{ padding: '8px 10px', fontWeight: 600, color: item.profit >= 0 ? '#00C896' : '#FF3B3B' }}>{fmt(item.profit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">پرداخت‌ها</h3>
          {inv.remaining_amount > 0 && (
            <button onClick={() => setPayForm(f => ({ ...f, show: true }))} className="text-xs text-brand hover:text-brand/80">+ ثبت پرداخت</button>
          )}
        </div>
        {payForm.show && (
          <div className="bg-white/5 rounded-xl p-4 mb-4 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label text-xs mb-1 block">روش</label>
                <select value={payForm.method} onChange={e => setPayForm(f => ({ ...f, method: e.target.value }))} className="input text-xs">
                  <option value="cash">نقد</option>
                  <option value="transfer">حواله</option>
                  <option value="card">کارت</option>
                  <option value="online">آنلاین</option>
                  <option value="credit">نسیه</option>
                </select>
              </div>
              <div>
                <label className="label text-xs mb-1 block">مبلغ</label>
                <input type="number" value={payForm.amount} onChange={e => setPayForm(f => ({ ...f, amount: e.target.value }))} className="input text-xs" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">حساب</label>
                <select value={payForm.to_account_id} onChange={e => setPayForm(f => ({ ...f, to_account_id: e.target.value }))} className="input text-xs">
                  <option value="">انتخاب...</option>
                  {accounts.filter(a => a.currency === 'IRR').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <input type="date" value={payForm.date} onChange={e => setPayForm(f => ({ ...f, date: e.target.value }))} className="input text-xs" />
              </div>
              <div className="col-span-2">
                <label className="label text-xs mb-1 block">پیگیری</label>
                <input value={payForm.reference} onChange={e => setPayForm(f => ({ ...f, reference: e.target.value }))} className="input text-xs" />
              </div>
            </div>
            {msg && <div className={`text-xs rounded-lg px-3 py-2 ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}
            <div className="flex gap-2">
              <button onClick={() => payMut.mutate({ invoice_id: id, ...payForm })} disabled={!payForm.amount || payMut.isPending} className="btn-primary text-xs px-4 py-2 disabled:opacity-50">ثبت</button>
              <button onClick={() => setPayForm(f => ({ ...f, show: false }))} className="btn-secondary text-xs px-4 py-2">انصراف</button>
            </div>
          </div>
        )}
        {inv.payments?.length === 0 ? (
          <div className="text-center py-4 text-gray-steel text-xs">پرداختی ثبت نشده</div>
        ) : (
          <div className="space-y-2">
            {inv.payments?.map(p => (
              <div key={p.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
                <div>
                  <div className="text-xs text-white">{p.method_display} {p.to_account ? `→ ${p.to_account}` : ''}</div>
                  <div className="text-[10px] text-gray-steel">{p.date} {p.reference && `| ${p.reference}`} | {p.created_by}</div>
                </div>
                <div className="text-sm font-bold text-green-400">{fmt(p.amount)} ت</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Quick Add Customer ───────────────────────────────────────
function QuickAddCustomer({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const qc = useQueryClient()

  async function save() {
    if (!name.trim()) { setErr('نام الزامی است'); return }
    setLoading(true)
    try {
      const res = await api.post('/accounting/contacts/', { name, phone, contact_type: 'customer' })
      qc.invalidateQueries(['customer-search', ''])
      onCreated({ id: res.data.id, name: res.data.name, phone: res.data.phone || '' })
    } catch (e) { setErr(e.response?.data?.error || 'خطا') }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4">
      <div className="card p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-sm">مشتری جدید</h3>
          <button onClick={onClose} className="text-gray-steel text-xl">×</button>
        </div>
        <div className="space-y-3">
          <div><label className="label text-xs mb-1 block">نام *</label><input value={name} onChange={e => setName(e.target.value)} className="input text-sm" placeholder="نام کامل" autoFocus /></div>
          <div><label className="label text-xs mb-1 block">تلفن</label><input value={phone} onChange={e => setPhone(e.target.value)} className="input text-sm" dir="ltr" placeholder="09..." /></div>
        </div>
        {err && <div className="text-red-400 text-xs mt-2">{err}</div>}
        <div className="flex gap-2 mt-4">
          <button onClick={save} disabled={loading} className="btn-primary flex-1 py-2 text-sm disabled:opacity-50">{loading ? '...' : '✓ ذخیره'}</button>
          <button onClick={onClose} className="btn-secondary px-4 py-2 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── فرم فاکتور جدید ─────────────────────────────────────────
function NewInvoiceForm({ onClose, onSuccess, prefillOrder }) {
  const { data: variants = [] } = useQuery({ queryKey: ['variants-list'], queryFn: () => api.get('/catalog/variants/').then(r => r.data) })
  const qc = useQueryClient()
  const [customerSearch, setCustomerSearch] = useState('')
  const [customer, setCustomer] = useState(prefillOrder ? { id: prefillOrder.customer_id, name: prefillOrder.customer_name, phone: prefillOrder.customer_phone } : null)
  const [showCustomerDrop, setShowCustomerDrop] = useState(false)
  const [showQuickAdd, setShowQuickAdd] = useState(false)
  const { data: customers = [] } = useQuery({
    queryKey: ['customer-search', customerSearch],
    queryFn: () => api.get('/accounting/customers/search/', { params: { q: customerSearch } }).then(r => r.data),
    enabled: customerSearch.length >= 2,
  })
  const [items, setItems] = useState(prefillOrder?.items?.map(i => ({ variant_id: String(i.variant_id), quantity: String(i.quantity), unit_price: String(i.unit_price), discount_percent: '0' })) || [{ variant_id: '', quantity: '', unit_price: '', discount_percent: '0' }])
  const [hdr, setHdr] = useState({ discount_amount: '0', shipping_cost: '0', tax_amount: '0', note: '', status: 'confirmed', order_id: prefillOrder?.id || '', source: prefillOrder ? 'order' : 'manual' })
  const [msg, setMsg] = useState(null)
  const createMut = useMutation({
    mutationFn: (d) => api.post('/accounting/sale-invoices/', d).then(r => r.data),
    onSuccess: (data) => { setMsg({ type: 'success', text: `فاکتور ${data.invoice_number} صادر شد` }); qc.invalidateQueries(['sale-invoices']); qc.invalidateQueries(['pending-orders']); setTimeout(() => onSuccess?.(data.id), 1500) },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })
  const calcSubtotal = () => items.reduce((s, it) => s + Math.round((Number(it.quantity) || 0) * (Number(it.unit_price) || 0) * (1 - (Number(it.discount_percent) || 0) / 100)), 0)
  const total = calcSubtotal() - Number(hdr.discount_amount || 0) + Number(hdr.shipping_cost || 0) + Number(hdr.tax_amount || 0)
  function handleSubmit() {
    if (!customer) return setMsg({ type: 'error', text: 'مشتری را انتخاب کنید' })
    if (items.some(it => !it.variant_id || !it.quantity || !it.unit_price)) return setMsg({ type: 'error', text: 'اطلاعات اقلام را کامل کنید' })
    createMut.mutate({ customer_id: customer.id, customer_name: customer.name, customer_phone: customer.phone || '', ...hdr, items: items.map(it => ({ ...it, quantity: Number(it.quantity), unit_price: Number(it.unit_price), discount_percent: Number(it.discount_percent) })) })
  }
  return (
    <div className="space-y-4">
      {showQuickAdd && <QuickAddCustomer onClose={() => setShowQuickAdd(false)} onCreated={c => { setCustomer(c); setCustomerSearch(c.name); setShowQuickAdd(false) }} />}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">اطلاعات مشتری</h3>
        <div className="relative max-w-sm">
          <div className="flex items-center justify-between mb-1">
            <label className="label text-xs">جستجوی مشتری *</label>
            <button type="button" onClick={() => setShowQuickAdd(true)} className="text-xs text-brand hover:text-brand/80 font-semibold">+ مشتری جدید</button>
          </div>
          <input value={customerSearch} onChange={e => { setCustomerSearch(e.target.value); setShowCustomerDrop(true) }} onFocus={() => setShowCustomerDrop(true)} placeholder="نام یا شماره موبایل..." className="input text-sm" />
          {showCustomerDrop && customers.length > 0 && (
            <div className="absolute z-50 top-full right-0 left-0 mt-1 bg-navy border border-white/10 rounded-xl shadow-xl overflow-hidden">
              {customers.map(c => (
                <button key={c.id} className="w-full text-right px-4 py-3 hover:bg-white/5 border-b border-white/5 last:border-0" onClick={() => { setCustomer(c); setCustomerSearch(c.name); setShowCustomerDrop(false) }}>
                  <div className="text-sm text-white">{c.name}</div>
                  <div className="text-xs text-gray-steel">{c.phone}</div>
                </button>
              ))}
            </div>
          )}
          {showCustomerDrop && <div className="fixed inset-0 z-40" onClick={() => setShowCustomerDrop(false)} />}
          {customer && <div className="text-xs text-green-400 mt-1">✓ {customer.name} | {customer.phone}</div>}
        </div>
      </div>
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">اقلام فاکتور</h3>
          <button onClick={() => setItems(i => [...i, { variant_id: '', quantity: '', unit_price: '', discount_percent: '0' }])} className="text-xs text-brand">+ افزودن کالا</button>
        </div>
        <div className="space-y-3">
          {items.map((item, idx) => (
            <div key={idx} className="bg-white/5 rounded-xl p-3">
              <div className="grid grid-cols-5 gap-3">
                <div className="col-span-2"><label className="label text-[10px] mb-1 block">کالا *</label><select value={item.variant_id} onChange={e => setItems(i => i.map((it, j) => j === idx ? { ...it, variant_id: e.target.value } : it))} className="input text-xs"><option value="">انتخاب...</option>{variants.map(v => <option key={v.id} value={v.id}>{v.product_name} [{v.sku}]</option>)}</select></div>
                <div><label className="label text-[10px] mb-1 block">تعداد *</label><input type="number" value={item.quantity} onChange={e => setItems(i => i.map((it, j) => j === idx ? { ...it, quantity: e.target.value } : it))} className="input text-xs" /></div>
                <div><label className="label text-[10px] mb-1 block">قیمت واحد *</label><input type="number" value={item.unit_price} onChange={e => setItems(i => i.map((it, j) => j === idx ? { ...it, unit_price: e.target.value } : it))} className="input text-xs" /></div>
                <div><label className="label text-[10px] mb-1 block">تخفیف %</label><input type="number" min="0" max="100" value={item.discount_percent} onChange={e => setItems(i => i.map((it, j) => j === idx ? { ...it, discount_percent: e.target.value } : it))} className="input text-xs" /></div>
              </div>
              <div className="flex items-center justify-between mt-2">
                <div className="text-xs text-gray-steel">جمع: <span className="text-white font-bold">{fmt(Math.round((Number(item.quantity)||0)*(Number(item.unit_price)||0)*(1-(Number(item.discount_percent)||0)/100)))}</span> ت</div>
                {items.length > 1 && <button onClick={() => setItems(i => i.filter((_, j) => j !== idx))} className="text-xs text-red-400">× حذف</button>}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">تخفیف و هزینه‌های اضافی</h3>
        <div className="grid grid-cols-4 gap-4">
          <div><label className="label text-xs mb-1 block">تخفیف کل</label><input type="number" value={hdr.discount_amount} onChange={e => setHdr(h => ({ ...h, discount_amount: e.target.value }))} className="input text-sm" /></div>
          <div><label className="label text-xs mb-1 block">هزینه ارسال</label><input type="number" value={hdr.shipping_cost} onChange={e => setHdr(h => ({ ...h, shipping_cost: e.target.value }))} className="input text-sm" /></div>
          <div><label className="label text-xs mb-1 block">مالیات</label><input type="number" value={hdr.tax_amount} onChange={e => setHdr(h => ({ ...h, tax_amount: e.target.value }))} className="input text-sm" /></div>
          <div><label className="label text-xs mb-1 block">وضعیت</label><select value={hdr.status} onChange={e => setHdr(h => ({ ...h, status: e.target.value }))} className="input text-sm"><option value="draft">پیش‌نویس</option><option value="confirmed">تأیید شده</option></select></div>
        </div>
        <div className="mt-3"><label className="label text-xs mb-1 block">توضیحات</label><input value={hdr.note} onChange={e => setHdr(h => ({ ...h, note: e.target.value }))} className="input text-sm" /></div>
        <div className="mt-4 text-left"><div className="text-xs text-gray-steel">مبلغ نهایی:</div><div className="text-2xl font-bold text-brand">{fmt(total)} ریال</div></div>
      </div>
      {msg && <div className={`rounded-lg px-4 py-3 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}
      <div className="flex gap-3">
        <button onClick={handleSubmit} disabled={createMut.isPending} className="btn-primary flex-1 py-3 disabled:opacity-50">{createMut.isPending ? 'در حال صدور...' : 'صدور فاکتور'}</button>
        <button onClick={onClose} className="btn-secondary px-6 py-3">انصراف</button>
      </div>
    </div>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
export default function SaleInvoicePage() {
  const [view, setView] = useState('list')
  const [selectedId, setSelectedId] = useState(null)
  const [prefillOrder, setPrefillOrder] = useState(null)
  const [tab, setTab] = useState('invoices')
  const [autoPayment, setAutoPayment] = useState(false)
  const { data: invoices = [], isLoading } = useQuery({ queryKey: ['sale-invoices'], queryFn: () => api.get('/accounting/sale-invoices/').then(r => r.data), enabled: view === 'list' })
  const { data: pendingOrders = [] } = useQuery({ queryKey: ['pending-orders'], queryFn: () => api.get('/accounting/pending-orders/').then(r => r.data), enabled: view === 'list' })

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {view !== 'list' && <button onClick={() => { setView('list'); setPrefillOrder(null); setAutoPayment(false) }} className="text-gray-steel hover:text-white text-sm">← برگشت</button>}
          <h1 className="font-display font-bold text-2xl text-white">{view === 'list' ? 'فاکتورهای فروش' : view === 'new' ? 'فاکتور جدید' : 'جزئیات فاکتور'}</h1>
        </div>
        {view === 'list' && <button onClick={() => setView('new')} className="btn-primary text-sm px-4 py-2">+ فاکتور جدید</button>}
      </div>

      {view === 'list' && (
        <>
          <div className="flex gap-2 mb-4 border-b border-white/10">
            {[['invoices', `فاکتورها (${invoices.length})`], ['pending', `سفارشات در انتظار (${pendingOrders.filter(o => !o.has_invoice).length})`]].map(([k, v]) => (
              <button key={k} onClick={() => setTab(k)} className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${tab === k ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>{v}</button>
            ))}
          </div>
          {tab === 'invoices' && (
            <div className="card p-5">
              {isLoading ? <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div> : invoices.length === 0 ? (
                <div className="text-center py-12"><div className="text-4xl mb-3">🧾</div><div className="text-gray-steel text-sm mb-4">هنوز فاکتوری صادر نشده</div><button onClick={() => setView('new')} className="btn-primary text-sm px-6 py-2">+ صدور اولین فاکتور</button></div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead><tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>{['شماره فاکتور','مشتری','تاریخ','وضعیت','مبلغ نهایی','پرداخت شده','مانده','سود',''].map(h => <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>)}</tr></thead>
                  <tbody>
                    {invoices.map((inv, i) => (
                      <tr key={inv.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#0066FF' }}>{inv.invoice_number}</td>
                        <td style={{ padding: '10px 12px' }}><div>{inv.customer_name}</div><div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{inv.customer_phone}</div></td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{inv.created_at}</td>
                        <td style={{ padding: '10px 12px' }}><span style={{ color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>{inv.status_display}</span></td>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>{fmt(inv.total_amount)} ت</td>
                        <td style={{ padding: '10px 12px', color: '#00C896' }}>{fmt(inv.paid_amount)} ت</td>
                        <td style={{ padding: '10px 12px', color: inv.remaining_amount > 0 ? '#FF3B3B' : '#00C896', fontWeight: inv.remaining_amount > 0 ? 700 : 400 }}>{inv.remaining_amount > 0 ? fmt(inv.remaining_amount) + ' ت' : '✓ تسویه'}</td>
                        <td style={{ padding: '10px 12px', color: inv.gross_profit >= 0 ? '#00C896' : '#FF3B3B' }}>{fmt(inv.gross_profit)} ت</td>
                        <td style={{ padding: '10px 12px' }}><button onClick={() => { setSelectedId(inv.id); setView('detail') }} className="text-xs text-brand hover:text-brand/80">مشاهده</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
          {tab === 'pending' && (
            <div className="space-y-3">
              {pendingOrders.filter(o => !o.has_invoice).length === 0 ? <div className="card p-12 text-center text-gray-steel text-sm">سفارش در انتظاری وجود ندارد</div>
              : pendingOrders.filter(o => !o.has_invoice).map(order => (
                <div key={order.id} className="card p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-3"><span className="font-bold text-white text-sm">{order.order_number}</span><span style={{ color: '#FF9500', background: '#FF950020', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>{order.status_display}</span></div>
                      <div className="text-xs text-gray-steel mt-1">{order.customer_name} | {order.customer_phone}</div>
                    </div>
                    <div className="text-left"><div className="text-sm font-bold text-white">{fmt(order.total_amount)} ت</div><button onClick={() => { setPrefillOrder(order); setView('new') }} className="btn-primary text-xs px-4 py-2 mt-2">صدور فاکتور</button></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {view === 'new' && <NewInvoiceForm onClose={() => { setView('list'); setPrefillOrder(null) }} onSuccess={(newId) => { setPrefillOrder(null); if (newId) { setSelectedId(newId); setAutoPayment(true); setView('detail') } else setView('list') }} prefillOrder={prefillOrder} />}
      {view === 'detail' && selectedId && <InvoiceDetail id={selectedId} onClose={() => setView('list')} />}
    </div>
  )
}
