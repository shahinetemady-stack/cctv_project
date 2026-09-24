import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import { mediaUrl } from '../../utils/media'
import { formatDate } from '../../utils/date'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../../components/ui/AmountInput'
import SearchSelect, { advanceFlow } from '../../components/ui/SearchSelect'
import AddContactModal from '../../components/accounting/AddContactModal'
import JalaliDateInput from '../../components/ui/JalaliDateInput'
import { jalaliText, jalaliHolidayInfo } from '../../utils/jalali'
import { UserStamp } from '../../components/ui'

// برچسب سطح مشتری برای نمایش در فرم فاکتور فروش
const TIER_LABELS = { public: 'مشتری عمومی', partner: 'همکار (بدون سطح)', silver: 'همکار سیلور', gold: 'همکار گلد', platinum: 'همکار پلاتینیوم' }
const SETTLEMENT_LABELS = { cash: 'نقدی', credit: 'تو حسابی', month1: 'یکماهه' }

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_COLORS = { draft:'#888', confirmed:'#555', paid:'#222', cancelled:'#999' }
const STATUS_LABELS = { draft:'پیش‌نویس', confirmed:'تأیید شده', paid:'تسویه شده', cancelled:'باطل‌شده' }

const SKINS = [
  { id:'skin1', label:'Yellow Strike', desc:'نوار مورب زرد-مشکی' },
  { id:'skin2', label:'Bold Blocks',   desc:'بلوک زرد مورب' },
  { id:'skin3', label:'Steel & Gold',  desc:'طوسی تیره با accent زرد' },
  { id:'skin4', label:'Slate Wave',    desc:'طوسی روشن با موج زرد' },
]

const DEFAULT_INVOICE_TEXTS = {
  header_note: '',
  footer_note: 'این فاکتور رایانه‌ای است و بدون مهر و امضا معتبر می‌باشد.',
  thank_you: 'ممنون از خرید شما',
  terms: '',
}

function getInvoiceTexts() {
  try { return { ...DEFAULT_INVOICE_TEXTS, ...JSON.parse(localStorage.getItem('inv_texts') || '{}') } }
  catch { return DEFAULT_INVOICE_TEXTS }
}

function getCompanyInfo(settings) {
  const saved = {}
  try { Object.assign(saved, JSON.parse(localStorage.getItem('inv_company') || '{}')) } catch {}
  return {
    name: saved.name || settings?.site_name || '',
    managerName: saved.managerName || '',
    phone: saved.phone || settings?.contact_phone || '',
    address: saved.address || settings?.contact_address || '',
    logoUrl: saved.logoUrl || (settings?.site_logo
      ? mediaUrl(settings.site_logo)
      : ''),
  }
}

// ─── CSS فاکتور ───────────────────────────────────────────────
function skinCSS(skinId) {
  const base = `
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:Tahoma,Arial,sans-serif;direction:rtl;background:#fff;color:#111;font-size:13px}
    @media print{
      @page{margin:0.8cm}
      *{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;color-adjust:exact!important}
    }
    .page{min-height:100vh;display:flex;flex-direction:column;background:#fff}
    .body{padding:24px 32px;flex:1}
    .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}
    table.items{width:100%;border-collapse:collapse;margin-bottom:20px}
    table.items td{padding:9px 11px;border-bottom:0.5px solid #eee;font-size:12px}
    table.items tr:nth-child(even) td{background-color:#fafafa}
    .stamp{border-radius:50%;width:72px;height:72px;display:flex;align-items:center;justify-content:center;font-size:9px;text-align:center;line-height:1.4}
  `

  const skins = {
    skin1: base + `
      .hdr{background-color:#fff;padding:22px 32px;position:relative;border-bottom:1px solid #eee}
      .hdr-stripe-v{position:absolute;top:0;right:0;width:5px;height:100%;background-color:#f5c400}
      .hdr-inner{display:flex;justify-content:space-between;align-items:center}
      .logo-area{display:flex;align-items:center;gap:14px}
      .logo-circle{width:46px;height:46px;border-radius:50%;background-color:#f5c400;border:3px solid #222;display:flex;align-items:center;justify-content:center;font-size:22px}
      .co-name{font-size:19px;font-weight:900;color:#222}
      .co-sub{font-size:11px;color:#888;margin-top:3px}
      .inv-area{text-align:left}
      .inv-word{font-size:24px;font-weight:900;color:#222;letter-spacing:3px}
      .inv-num{font-size:12px;color:#888;margin-top:4px}
      .inv-date{display:inline-block;background-color:#222;color:#f5c400;font-size:10px;font-weight:700;padding:3px 10px;border-radius:4px;margin-top:4px}
      .diagonal{height:18px;background-color:#222;display:flex;align-items:center;padding-right:32px}
      .diagonal-inner{width:40%;height:100%;background-color:#f5c400}
      .ib{border-right:3px solid #f5c400;padding:12px 14px;background-color:#fffde7;border-radius:0 6px 6px 0}
      .ib-t{font-size:9px;color:#b89800;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
      .ib-n{font-size:14px;font-weight:800;color:#222;margin-bottom:3px}
      .ib-s{font-size:11px;color:#888}
      table.items thead tr{background-color:#222}
      table.items th{color:#f5c400;padding:11px;font-size:11px;text-align:right;font-weight:600}
      .amount-box{display:flex;justify-content:space-between;align-items:center;background-color:#222;border-radius:6px;padding:12px 16px}
      .amount-label{font-size:10px;color:#f5c400;letter-spacing:1px;margin-bottom:3px}
      .amount-cur{font-size:9px;color:#f5c400;opacity:0.7}
      .amount-val{font-size:22px;font-weight:900;color:#fff}
      .ftr{background-color:#f5f5f5;border-top:3px solid #f5c400;padding:14px 32px;display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#888}
      .stamp{border:1.5px dashed #f5c400;color:#b89800}
    `,
    skin2: base + `
      .hdr{background-color:#fff}
      .hdr-top{display:flex;justify-content:space-between;align-items:stretch}
      .hdr-r{padding:20px 32px;display:flex;align-items:flex-start;gap:14px;flex:1}
      .logo-sq{width:42px;height:42px;border-radius:6px;background-color:#f5f5f5;border:1.5px solid #eee;display:flex;align-items:center;justify-content:center;font-size:20px}
      .co-name{font-size:18px;font-weight:900;color:#222}
      .co-sub{font-size:11px;color:#888;margin-top:3px}
      .hdr-l{background-color:#f5c400;padding:20px 24px;display:flex;flex-direction:column;justify-content:center;min-width:130px}
      .inv-word{font-size:22px;font-weight:900;color:#222;letter-spacing:2px}
      .inv-num{font-size:10px;color:rgba(0,0,0,0.55);margin-top:4px}
      .meta-bar{background-color:#222;padding:8px 32px;display:flex;justify-content:space-between;font-size:11px;color:#aaa}
      .meta-bar span.hl{color:#f5c400}
      .ib{border-bottom:2px solid #f5c400;padding:11px 0 9px}
      .ib-t{font-size:9px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
      .ib-n{font-size:14px;font-weight:800;color:#222;margin-bottom:3px}
      .ib-s{font-size:11px;color:#aaa}
      table.items thead tr{border-bottom:2.5px solid #222}
      table.items th{color:#222;padding:11px;font-size:11px;text-align:right;font-weight:700;border-bottom:2.5px solid #222}
      .paid-bar{background-color:#f5c400;border-radius:5px;padding:8px 14px;margin-bottom:6px;display:flex;justify-content:space-between;font-size:11px;font-weight:700;color:#222}
      .total-bar{background-color:#222;border-radius:5px;padding:10px 14px;display:flex;justify-content:space-between;font-size:13px;font-weight:900;color:#fff}
      .total-bar span.hl{color:#f5c400}
      .thank-box{margin-top:16px;border-right:3px solid #f5c400;padding:8px 12px;background-color:#fffde7;border-radius:0 4px 4px 0;font-size:11px;color:#888}
      .ftr{background-color:#fafafa;border-top:1px solid #eee;padding:12px 32px;display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#aaa}
      .stamp{border:1.5px dashed #ccc;color:#bbb}
    `,
    skin3: base + `
      .hdr{background-color:#fff}
      .hdr-top{background-color:#4a4a4a;padding:22px 32px;display:flex;justify-content:space-between;align-items:center}
      .logo-area{display:flex;align-items:center;gap:14px}
      .logo-round{width:44px;height:44px;border-radius:6px;background-color:#f5c400;display:flex;align-items:center;justify-content:center;font-size:21px}
      .co-name{font-size:19px;font-weight:900;color:#fff}
      .co-sub{font-size:11px;color:rgba(255,255,255,0.6);margin-top:3px}
      .inv-box-right{text-align:left}
      .inv-word{font-size:10px;letter-spacing:3px;color:#f5c400;margin-bottom:5px}
      .inv-num{font-size:22px;font-weight:900;color:#fff;line-height:1}
      .inv-meta{font-size:10px;color:rgba(255,255,255,0.5);margin-top:4px}
      .bar-gradient{height:5px;background-color:#f5c400}
      .hdr-bot{background-color:#e8e8e8;padding:7px 32px;display:flex;justify-content:space-between;font-size:10px;color:#555;border-bottom:1px solid #ddd}
      .ib{border-right:3px solid #f5c400;padding:11px 13px;background-color:#fafafa;border-radius:0 5px 5px 0}
      .ib-t{font-size:9px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
      .ib-n{font-size:14px;font-weight:800;color:#333;margin-bottom:3px}
      .ib-s{font-size:11px;color:#aaa}
      table.items thead tr{background-color:#4a4a4a}
      table.items th{color:#f5c400;padding:11px;font-size:11px;text-align:right;font-weight:600}
      .tot-area{display:flex;justify-content:space-between;align-items:stretch;gap:16px;margin-top:4px}
      .sub-totals{flex:1}
      .sub-row{display:flex;justify-content:space-between;font-size:11px;color:#888;padding:5px 0;border-bottom:0.5px solid #eee}
      .main-tot{background-color:#4a4a4a;border-radius:6px;padding:12px 16px;min-width:140px;display:flex;flex-direction:column;align-items:flex-end}
      .main-label{font-size:9px;color:rgba(255,255,255,0.6);letter-spacing:1px;margin-bottom:3px}
      .main-val{font-size:20px;font-weight:900;color:#f5c400;line-height:1.1}
      .main-cur{font-size:9px;color:#f5c400;opacity:0.7;margin-top:2px}
      .ftr{background-color:#e8e8e8;border-top:2.5px solid #4a4a4a;padding:13px 32px;display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#888}
      .stamp{border:1.5px dashed #f5c400;color:#b89800}
    `,
    skin4: base + `
      .hdr{background-color:#fff;padding:20px 32px 0}
      .hdr-inner{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
      .logo-area{display:flex;align-items:center;gap:14px}
      .logo-sq{width:42px;height:42px;border-radius:6px;background-color:#ebebeb;border:1.5px solid #ccc;display:flex;align-items:center;justify-content:center;font-size:20px}
      .co-name{font-size:18px;font-weight:900;color:#333}
      .co-sub{font-size:11px;color:#888;margin-top:3px}
      .inv-panel{background-color:#f5c400;border-radius:7px;padding:12px 16px;text-align:left}
      .inv-word{font-size:18px;font-weight:900;color:#222;letter-spacing:1px;line-height:1}
      .inv-num{font-size:10px;color:rgba(0,0,0,0.5);margin-top:4px}
      .inv-date{font-size:10px;color:rgba(0,0,0,0.5)}
      .wave-bar{height:14px;background-color:#e0e0e0;margin-bottom:0}
      .wave-y{height:14px;width:42%;background-color:#f5c400;margin-top:-14px}
      .ib{border:0.5px solid #e0e0e0;border-top:2.5px solid #666;border-radius:0 0 5px 5px;padding:11px 13px;background-color:#fafafa}
      .ib-t{font-size:9px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
      .ib-n{font-size:14px;font-weight:800;color:#333;margin-bottom:3px}
      .ib-s{font-size:11px;color:#aaa}
      table.items thead tr{border-bottom:2.5px solid #666}
      table.items th{color:#333;padding:11px;font-size:11px;text-align:right;font-weight:700;border-bottom:2.5px solid #666}
      table.items td:last-child{font-weight:700;color:#444}
      .bottom-area{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-top:4px}
      .note-box{flex:1;background-color:#fafafa;border:0.5px solid #eee;border-radius:5px;padding:10px 13px;font-size:11px;color:#888;line-height:1.6}
      .note-box strong{color:#555;display:block;margin-bottom:4px}
      .tot-box{min-width:150px}
      .tot-row{display:flex;justify-content:space-between;font-size:11px;color:#888;padding:5px 0;border-bottom:0.5px solid #eee}
      .tot-main{display:flex;justify-content:space-between;align-items:center;background-color:#555;border-radius:5px;padding:10px 14px;margin-top:6px}
      .tot-label{font-size:10px;color:rgba(255,255,255,0.65);letter-spacing:1px;margin-bottom:3px}
      .tot-val{font-size:18px;font-weight:900;color:#f5c400;line-height:1}
      .ftr{background-color:#e8e8e8;border-top:2.5px solid #f5c400;padding:13px 32px;display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#777}
      .stamp{border:1.5px dashed #bbb;color:#aaa}
    `
  }
  return skins[skinId] || skins.skin1
}

function buildInvoiceHTML(inv, skinId, company, texts) {
  const items = inv.items || []
  const total = Number(inv.total_amount || 0)
  const paid = Number(inv.paid_amount || 0)
  const remaining = Number(inv.remaining_amount || 0)

  const rows = items.map((x, i) =>
    `<tr>
      <td style="text-align:center;color:#aaa;width:36px">${i + 1}</td>
      <td>${x.product_name || ''}</td>
      <td style="text-align:center;width:70px">${x.quantity || 0}</td>
      <td style="width:130px;text-align:left">${Number(x.unit_price || 0).toLocaleString()}</td>
      <td style="width:130px;text-align:left;font-weight:700">${Number(x.subtotal || 0).toLocaleString()}</td>
    </tr>`
  ).join('')

  const logoHTML = company.logoUrl
    ? `<img src="${company.logoUrl}" style="height:44px;width:auto;object-fit:contain" />`
    : ''

  const headerNote = texts.header_note ? `<div style="font-size:11px;color:#888;margin-top:4px">${texts.header_note}</div>` : ''
  const footerNote = texts.footer_note || ''
  const thankYou = texts.thank_you || ''
  const terms = texts.terms ? `<div style="margin-top:14px;font-size:11px;color:#888;border-top:0.5px solid #eee;padding-top:10px">${texts.terms}</div>` : ''

  const bodies = {
    skin1: `
      <div class="page">
        <div class="hdr">
          <div class="hdr-stripe-v"></div>
          <div class="hdr-inner">
            <div class="logo-area">
              ${company.logoUrl ? `<div class="logo-circle">${logoHTML}</div>` : '<div class="logo-circle">🎥</div>'}
              <div>
                <div class="co-name">${company.name}</div>
                <div class="co-sub">${company.phone}${company.address ? ' | ' + company.address : ''}</div>
                ${company.managerName ? `<div class="co-sub">مدیر: ${company.managerName}</div>` : ''}
                ${headerNote}
              </div>
            </div>
            <div class="inv-area">
              <div class="inv-word">INVOICE</div>
              <div class="inv-num">${inv.invoice_number || ''}</div>
              <div class="inv-date">${inv.issue_date ? jalaliText(inv.issue_date) : formatDate(inv.created_at, { withTime: true })}</div>
              <div style="font-size:10px;color:#888;margin-top:4px">${inv.status_display || ''}</div>
            </div>
          </div>
          <div class="hdr-stripe-h"></div>
        </div>
        <div class="diagonal"><div class="diagonal-inner"></div></div>
        <div class="body">
          <div class="info-grid">
            <div class="ib"><div class="ib-t">فروشنده</div><div class="ib-n">${company.name}</div><div class="ib-s">${company.phone}</div>${company.address ? `<div class="ib-s">${company.address}</div>` : ''}</div>
            <div class="ib"><div class="ib-t">خریدار</div><div class="ib-n">${inv.customer_name || ''}</div><div class="ib-s">${inv.customer_phone || ''}</div></div>
          </div>
          <table class="items">
            <thead><tr><th>#</th><th>شرح کالا / خدمات</th><th style="text-align:center">تعداد</th><th style="text-align:left">قیمت واحد</th><th style="text-align:left">جمع</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          <div class="amount-box">
            <div><div class="amount-label">جمع کل فاکتور</div><div class="amount-cur">ریال</div></div>
            <div class="amount-val">${total.toLocaleString()}</div>
          </div>
          ${paid > 0 ? `<div style="display:flex;justify-content:space-between;font-size:11px;color:#888;padding:6px 0;border-bottom:0.5px solid #eee;margin-top:6px"><span>پرداخت شده:</span><span>${paid.toLocaleString()} ریال</span></div>` : ''}
          ${remaining > 0 ? `<div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700;color:#c41e3a;padding:6px 0;"><span>مانده بدهی:</span><span>${remaining.toLocaleString()} ریال</span></div>` : ''}
          ${terms}
        </div>
        <div class="ftr"><span>${company.name} | ${company.phone}</span><div class="stamp">${thankYou || 'مهر<br>امضا'}</div><span>${footerNote}</span></div>
      </div>`,

    skin2: `
      <div class="page">
        <div class="hdr">
          <div class="hdr-top">
            <div class="hdr-r">
              <div class="logo-sq">${company.logoUrl ? logoHTML : '🎥'}</div>
              <div><div class="co-name">${company.name}</div><div class="co-sub">${company.phone}${company.address ? ' | ' + company.address : ''}</div>${company.managerName ? `<div class="co-sub">مدیر: ${company.managerName}</div>` : ''}${headerNote}</div>
            </div>
            <div class="hdr-l"><div class="inv-word">INVOICE</div><div class="inv-num">${inv.invoice_number || ''}</div></div>
          </div>
          <div class="meta-bar"><span>تاریخ: <span class="hl">${inv.issue_date ? jalaliText(inv.issue_date) : formatDate(inv.created_at, { withTime: true })}</span></span><span>وضعیت: <span class="hl">${inv.status_display || ''}</span></span></div>
        </div>
        <div class="body">
          <div class="info-grid">
            <div class="ib"><div class="ib-t">فروشنده</div><div class="ib-n">${company.name}</div><div class="ib-s">${company.phone}</div></div>
            <div class="ib"><div class="ib-t">خریدار</div><div class="ib-n">${inv.customer_name || ''}</div><div class="ib-s">${inv.customer_phone || ''}</div></div>
          </div>
          <table class="items">
            <thead><tr><th>#</th><th>شرح کالا / خدمات</th><th style="text-align:center">تعداد</th><th style="text-align:left">قیمت واحد</th><th style="text-align:left">جمع</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          ${paid > 0 ? `<div class="paid-bar"><span>پرداخت شده</span><span>${paid.toLocaleString()} ریال</span></div>` : ''}
          <div class="total-bar"><span>جمع کل فاکتور</span><span class="hl">${total.toLocaleString()} ریال</span></div>
          ${remaining > 0 ? `<div style="display:flex;justify-content:space-between;font-size:11px;font-weight:700;color:#c41e3a;padding:8px 14px;border-radius:5px;background:#fff3f3;margin-top:6px"><span>مانده بدهی</span><span>${remaining.toLocaleString()} ریال</span></div>` : ''}
          ${thankYou ? `<div class="thank-box">${thankYou}</div>` : ''}
          ${terms}
        </div>
        <div class="ftr"><span>${footerNote}</span><div class="stamp">مهر<br>امضا</div><span>${company.name}</span></div>
      </div>`,

    skin3: `
      <div class="page">
        <div class="hdr">
          <div class="hdr-top">
            <div class="logo-area">
              <div class="logo-round">${company.logoUrl ? logoHTML : '🎥'}</div>
              <div><div class="co-name">${company.name}</div><div class="co-sub">${company.phone}</div>${company.managerName ? `<div class="co-sub">مدیر: ${company.managerName}</div>` : ''}${headerNote}</div>
            </div>
            <div class="inv-box-right">
              <div class="inv-word">INVOICE</div>
              <div class="inv-num">${inv.invoice_number || ''}</div>
              <div class="inv-meta">${inv.issue_date ? jalaliText(inv.issue_date) : formatDate(inv.created_at, { withTime: true })} | ${inv.status_display || ''}</div>
            </div>
          </div>
          <div class="bar-gradient"></div>
          <div class="hdr-bot"><span>فروشنده: ${company.name}${company.address ? ' | ' + company.address : ''}</span><span>خریدار: ${inv.customer_name || ''} | ${inv.customer_phone || ''}</span></div>
        </div>
        <div class="body">
          <div class="info-grid">
            <div class="ib"><div class="ib-t">فروشنده</div><div class="ib-n">${company.name}</div><div class="ib-s">${company.phone}</div>${company.address ? `<div class="ib-s">${company.address}</div>` : ''}</div>
            <div class="ib"><div class="ib-t">خریدار</div><div class="ib-n">${inv.customer_name || ''}</div><div class="ib-s">${inv.customer_phone || ''}</div></div>
          </div>
          <table class="items">
            <thead><tr><th>#</th><th>شرح کالا / خدمات</th><th style="text-align:center">تعداد</th><th style="text-align:left">قیمت واحد</th><th style="text-align:left">جمع</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          <div class="tot-area">
            <div class="sub-totals">
              <div class="sub-row"><span>جمع اقلام:</span><span>${total.toLocaleString()}</span></div>
              ${paid > 0 ? `<div class="sub-row"><span>پرداخت شده:</span><span>${paid.toLocaleString()}</span></div>` : ''}
              ${remaining > 0 ? `<div class="sub-row" style="color:#c41e3a;font-weight:700"><span>مانده بدهی:</span><span>${remaining.toLocaleString()}</span></div>` : ''}
              ${terms ? `<div style="margin-top:10px;font-size:11px;color:#888">${terms}</div>` : ''}
            </div>
            <div class="main-tot">
              <div class="main-label">جمع کل</div>
              <div class="main-val">${total.toLocaleString()}</div>
              <div class="main-cur">ریال</div>
            </div>
          </div>
        </div>
        <div class="ftr"><span>${company.name} | ${company.phone}</span><div class="stamp">مهر<br>امضا</div><span>${footerNote}</span></div>
      </div>`,

    skin4: `
      <div class="page">
        <div class="hdr">
          <div class="hdr-inner">
            <div class="logo-area">
              <div class="logo-sq">${company.logoUrl ? logoHTML : '🎥'}</div>
              <div><div class="co-name">${company.name}</div><div class="co-sub">${company.phone}${company.address ? ' | ' + company.address : ''}</div>${company.managerName ? `<div class="co-sub">مدیر: ${company.managerName}</div>` : ''}${headerNote}</div>
            </div>
            <div class="inv-panel">
              <div class="inv-word">INVOICE</div>
              <div class="inv-num">${inv.invoice_number || ''}</div>
              <div class="inv-date">${inv.issue_date ? jalaliText(inv.issue_date) : formatDate(inv.created_at, { withTime: true })} | ${inv.status_display || ''}</div>
            </div>
          </div>
        </div>
        <div class="wave-bar"></div>
        <div class="wave-y"></div>
        <div class="body">
          <div class="info-grid">
            <div class="ib"><div class="ib-t">فروشنده</div><div class="ib-n">${company.name}</div><div class="ib-s">${company.phone}</div></div>
            <div class="ib"><div class="ib-t">خریدار</div><div class="ib-n">${inv.customer_name || ''}</div><div class="ib-s">${inv.customer_phone || ''}</div></div>
          </div>
          <table class="items">
            <thead><tr><th>#</th><th>شرح کالا / خدمات</th><th style="text-align:center">تعداد</th><th style="text-align:left">قیمت واحد</th><th style="text-align:left">جمع</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          <div class="bottom-area">
            <div class="note-box">
              ${thankYou ? `<strong>${thankYou}</strong>` : ''}
              ${inv.note ? `یادداشت: ${inv.note}` : ''}
              ${terms ? `<div style="margin-top:6px">${terms}</div>` : ''}
            </div>
            <div class="tot-box">
              <div class="tot-row"><span>جمع اقلام:</span><span>${total.toLocaleString()}</span></div>
              ${paid > 0 ? `<div class="tot-row"><span>پرداخت شده:</span><span>${paid.toLocaleString()}</span></div>` : ''}
              ${remaining > 0 ? `<div class="tot-row" style="color:#c41e3a;font-weight:700"><span>مانده:</span><span>${remaining.toLocaleString()}</span></div>` : ''}
              <div class="tot-main">
                <div><div class="tot-label">جمع کل</div><div class="tot-val">${total.toLocaleString()}</div></div>
              </div>
            </div>
          </div>
        </div>
        <div class="ftr"><span>${company.name}</span><div class="stamp">مهر<br>امضا</div><span>${footerNote}</span></div>
      </div>`
  }

  return `<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="utf-8"><title>فاکتور ${inv.invoice_number || ''}</title><style>${skinCSS(skinId)}</style></head><body>
${bodies[skinId] || bodies.skin1}</body></html>\``
}

// ─── Admin Invoice Settings Modal ────────────────────────────
function AdminInvoiceSettings({ onClose }) {
  const [texts, setTexts] = useState(getInvoiceTexts)
  const [saved, setSaved] = useState(false)

  function save() {
    localStorage.setItem('inv_texts', JSON.stringify(texts))
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div className="fixed inset-0 z-[400] flex items-center justify-center bg-black/80 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-bold text-white text-base">⚙️ تنظیمات متن فاکتور</h3>
            <p className="text-xs text-gray-steel mt-1">فقط ادمین می‌تواند این تنظیمات را تغییر دهد</p>
          </div>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="label text-xs mb-1 block">متن کنار نام شرکت (Header Note)</label>
            <input value={texts.header_note}
              onChange={e => setTexts(t => ({ ...t, header_note: e.target.value }))}
              className="input text-sm" placeholder="مثلاً: واردکننده رسمی قطعات دوربین" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">متن پاورقی (Footer Note)</label>
            <input value={texts.footer_note}
              onChange={e => setTexts(t => ({ ...t, footer_note: e.target.value }))}
              className="input text-sm" placeholder="مثلاً: این فاکتور رایانه‌ای است..." />
          </div>
          <div>
            <label className="label text-xs mb-1 block">متن تشکر</label>
            <input value={texts.thank_you}
              onChange={e => setTexts(t => ({ ...t, thank_you: e.target.value }))}
              className="input text-sm" placeholder="مثلاً: ممنون از خرید شما" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">شرایط و قوانین (اختیاری)</label>
            <textarea value={texts.terms}
              onChange={e => setTexts(t => ({ ...t, terms: e.target.value }))}
              className="input text-sm" rows={3}
              placeholder="مثلاً: کالای فروخته شده بازگشت داده نمی‌شود..." />
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={save}
            className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all ${saved ? 'bg-green-500 text-white' : 'btn-primary'}`}>
            {saved ? '✓ ذخیره شد' : 'ذخیره تنظیمات'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5 text-sm">بستن</button>
        </div>
      </div>
    </div>
  )
}

// ─── Print Modal ──────────────────────────────────────────────
function PrintModal({ inv, onClose, isAdmin }) {
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 0,
  })
  const [skin, setSkin] = useState(() => localStorage.getItem('inv_skin') || 'skin1')
  const [showSettings, setShowSettings] = useState(false)
  const [company, setCompany] = useState(() => ({
    name: '', managerName: '', phone: '', address: '', logoUrl: ''
  }))
  const [initialized, setInitialized] = useState(false)

  if (settings && !initialized) {
    setInitialized(true)
    const saved = getCompanyInfo(settings)
    setCompany(saved)
  }

  function saveAndPrint() {
    localStorage.setItem('inv_skin', skin)
    localStorage.setItem('inv_company', JSON.stringify(company))
    const texts = getInvoiceTexts()
    const html = buildInvoiceHTML(inv, skin, company, texts)

    // ذخیره در localStorage و باز کردن صفحه پرینت
    localStorage.setItem('invoice_print_html', html)
    const printUrl = window.location.origin + '/invoice-print'
    const win = window.open(printUrl, '_blank', 'width=1050,height=800')
    if (!win) {
      alert('لطفاً Pop-up را در مرورگر فعال کنید')
    } else {
      win.focus()
    }
  }

  const skinPreview = {
    skin1: { top: '#222', accent: '#f5c400', label: 'Yellow Strike' },
    skin2: { top: '#f5c400', accent: '#222', label: 'Bold Blocks' },
    skin3: { top: '#4a4a4a', accent: '#f5c400', label: 'Steel & Gold' },
    skin4: { top: '#f5c400', accent: '#666', label: 'Slate Wave' },
  }

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/80 p-4">
      {showSettings && <AdminInvoiceSettings onClose={() => setShowSettings(false)} />}
      <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-white text-lg">🖨️ چاپ / PDF فاکتور</h3>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <button onClick={() => setShowSettings(true)}
                className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-gray-steel transition-all">
                ⚙️ تنظیمات متن
              </button>
            )}
            <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
          </div>
        </div>

        {/* انتخاب طرح */}
        <div className="mb-5">
          <label className="label text-xs mb-3 block">طرح فاکتور</label>
          <div className="grid grid-cols-4 gap-3">
            {SKINS.map(s => {
              const p = skinPreview[s.id]
              return (
                <button key={s.id} onClick={() => { setSkin(s.id); localStorage.setItem('inv_skin', s.id) }}
                  className={`rounded-xl border-2 overflow-hidden transition-all ${skin === s.id ? 'border-white scale-105' : 'border-white/10 hover:border-white/30'}`}>
                  <div style={{ background: '#fff', height: 68, padding: 7, display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ background: p.top, height: 20, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 5 }}>
                      <div style={{ background: p.accent, width: '30%', height: '60%', borderRadius: 2 }}></div>
                    </div>
                    <div style={{ background: '#f0f0f0', height: 7, borderRadius: 2 }}></div>
                    <div style={{ background: '#f0f0f0', height: 7, borderRadius: 2, width: '80%' }}></div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <div style={{ background: p.top, width: '40%', height: 10, borderRadius: 2 }}></div>
                    </div>
                  </div>
                  <div className="p-2 text-center" style={{ background: skin === s.id ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.2)' }}>
                    <div className="text-xs text-white font-semibold">{s.label}</div>
                    <div className="text-[9px] text-gray-steel">{s.desc}</div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* اطلاعات شرکت */}
        <div className="mb-5 bg-white/5 rounded-xl p-4">
          <label className="label text-xs mb-3 block">اطلاعات فروشنده</label>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label text-[10px] mb-1 block">نام مجموعه</label>
              <input value={company.name} onChange={e => setCompany(c => ({ ...c, name: e.target.value }))} className="input text-sm" /></div>
            <div><label className="label text-[10px] mb-1 block">نام مدیر</label>
              <input value={company.managerName} onChange={e => setCompany(c => ({ ...c, managerName: e.target.value }))} className="input text-sm" /></div>
            <div><label className="label text-[10px] mb-1 block">تلفن</label>
              <input value={company.phone} onChange={e => setCompany(c => ({ ...c, phone: e.target.value }))} className="input text-sm" dir="ltr" /></div>
            <div><label className="label text-[10px] mb-1 block">آدرس</label>
              <input value={company.address} onChange={e => setCompany(c => ({ ...c, address: e.target.value }))} className="input text-sm" /></div>
          </div>
          <div className="mt-3">
            <label className="label text-[10px] mb-1 block">لوگو (URL)</label>
            <div className="flex gap-2 items-center">
              <input value={company.logoUrl} onChange={e => setCompany(c => ({ ...c, logoUrl: e.target.value }))}
                className="input text-xs flex-1" dir="ltr" placeholder="https://..." />
              {company.logoUrl && <img src={company.logoUrl} alt="logo" className="w-10 h-10 object-contain rounded border border-white/20" onError={e => e.target.style.display = 'none'} />}
            </div>
            {settings?.site_logo && (
              <button onClick={() => setCompany(c => ({ ...c, logoUrl: mediaUrl(settings.site_logo) }))}
                className="text-xs text-brand mt-1 hover:text-brand/80">← استفاده از لوگوی سایت</button>
            )}
          </div>
        </div>

        {isAdmin && (
          <div className="mb-5 bg-white/5 border border-white/10 rounded-xl p-3 flex items-center justify-between">
            <div>
              <div className="text-xs text-white font-semibold">متن‌های فاکتور</div>
              <div className="text-[10px] text-gray-steel mt-0.5">پاورقی، تشکر، شرایط و قوانین قابل ویرایش هستند</div>
            </div>
            <button onClick={() => setShowSettings(true)}
              className="text-xs px-4 py-2 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 transition-all">
              ویرایش متن‌ها ✏️
            </button>
          </div>
        )}

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

// ─── EditPaymentModal ─────────────────────────────────────────
function EditPaymentModal({ payment, accounts, onClose, onSaved }) {
  const { data: full } = useQuery({
    queryKey: ['sale-payment', payment.id],
    queryFn: () => api.get(`/accounting/sale-payments/${payment.id}/`).then(r => r.data),
  })
  const [form, setForm] = useState({
    method: payment.method || 'transfer',
    amount: String(payment.amount ?? ''),
    date: payment.date || '',
    reference: payment.reference || '',
    note: '',
    to_account_id: '',
  })
  const [initialized, setInitialized] = useState(false)
  const [err, setErr] = useState('')

  if (full && !initialized) {
    setInitialized(true)
    setForm({
      method: full.method || 'transfer',
      amount: String(full.amount ?? ''),
      date: full.date || '',
      reference: full.reference || '',
      note: full.note || '',
      to_account_id: full.to_account_id || '',
    })
  }

  const saveMut = useMutation({
    mutationFn: d => api.patch(`/accounting/sale-payments/${payment.id}/`, d).then(r => r.data),
    onSuccess: () => onSaved?.(),
    onError: e => setErr(e.response?.data?.error || 'خطا در ویرایش پرداخت'),
  })

  function save() {
    if (!form.amount) { setErr('مبلغ الزامی است'); return }
    saveMut.mutate({
      to_account_id: form.to_account_id || null,
      method: form.method,
      amount: Number(form.amount),
      date: form.date,
      reference: form.reference,
      note: form.note,
    })
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-white">ویرایش پرداخت</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label text-xs mb-1 block">روش</label>
            <select value={form.method} onChange={e => setForm(f => ({ ...f, method: e.target.value }))} className="input text-xs">
              <option value="cash">نقد</option><option value="transfer">حواله</option><option value="card">کارت</option><option value="online">آنلاین</option><option value="credit">نسیه</option>
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">مبلغ</label>
            <AmountInput value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} className="input text-xs" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">حساب</label>
            <select value={form.to_account_id} onChange={e => setForm(f => ({ ...f, to_account_id: e.target.value }))} className="input text-xs">
              <option value="">انتخاب...</option>
              {accounts.filter(a => a.currency === 'IRR').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">تاریخ</label>
            <input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} className="input text-xs" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">پیگیری</label>
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))} className="input text-xs" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">یادداشت</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} className="input text-xs" />
          </div>
        </div>
        {err && <div className="text-red-400 text-xs mt-3 bg-red-500/10 rounded-lg px-3 py-2">{err}</div>}
        <div className="flex gap-3 mt-5">
          <button onClick={save} disabled={saveMut.isPending} className="btn-primary flex-1 py-2.5 text-sm font-semibold disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── AccountSmsPicker — ورود دستی یک یا چند حساب برای پیامک اطلاعات حساب ───
function AccountSmsPicker({ customerName, phone, pending, onSend, onClose }) {
  const [rows, setRows] = useState([{ account_number: '', holder: '' }])
  const setRow = (i, k, v) => setRows(rs => rs.map((r, idx) => idx === i ? { ...r, [k]: v } : r))
  const filled = rows.filter(r => r.account_number.trim())

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="card p-5 w-full max-w-sm" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-white">ارسال پیامک اطلاعات حساب</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="text-xs text-gray-steel mb-3">
          گیرنده: <span className="text-white">{customerName || '—'}</span> <span dir="ltr">({phone || 'بدون شماره'})</span>
        </div>
        <div className="space-y-2 mb-3 max-h-64 overflow-y-auto">
          {rows.map((r, i) => (
            <div key={i} className="bg-white/5 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <input value={r.account_number} onChange={e => setRow(i, 'account_number', e.target.value)}
                  placeholder="شماره حساب / کارت" dir="ltr"
                  className="input-field flex-1 text-sm text-left" />
                {rows.length > 1 && (
                  <button onClick={() => setRows(rs => rs.filter((_, idx) => idx !== i))}
                    className="text-red-400 hover:text-red-300 text-lg px-1" title="حذف">×</button>
                )}
              </div>
              <input value={r.holder} onChange={e => setRow(i, 'holder', e.target.value)}
                placeholder="نام صاحب حساب"
                className="input-field w-full text-sm" />
            </div>
          ))}
        </div>
        <button onClick={() => setRows(rs => [...rs, { account_number: '', holder: '' }])}
          className="text-xs text-brand hover:text-brand/80 font-semibold mb-4">+ افزودن حساب دیگر</button>
        <div className="flex gap-2">
          <button onClick={() => onSend(filled)} disabled={pending || filled.length === 0}
            className="btn-primary flex-1 py-2.5 text-sm font-semibold disabled:opacity-50">
            {pending ? 'در حال ارسال...' : `ارسال (${filled.length} پیامک)`}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── InvoiceDetail ────────────────────────────────────────────
function InvoiceDetail({ id, onClose, isAdmin, onEdit }) {
  const qc = useQueryClient()
  const { can, isSuperuser } = usePermissions()
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
  const [editPay, setEditPay] = useState(null)
  const [msg, setMsg] = useState(null)

  const payMut = useMutation({
    mutationFn: d => api.post('/accounting/sale-payments/', d).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['sale-invoice', id]); qc.invalidateQueries(['sale-invoices'])
      setPayForm(f => ({ ...f, show: false }))
      // خلاصه تخصیص خودکار FIFO — پول ممکن است به فاکتورهای قدیمی‌تر هم رفته باشد
      const parts = (r.allocated || []).map(a => `${Number(a.amount).toLocaleString('fa-IR')} ← فاکتور ${a.invoice_number}`)
      let text = 'پرداخت ثبت شد'
      if (parts.length) text += ' — تخصیص: ' + parts.join('، ')
      if (r.leftover > 0) text += ` — مازاد ${Number(r.leftover).toLocaleString('fa-IR')} ریال به بستانکاری مشتری رفت`
      setMsg({ type: 'success', text })
      setTimeout(() => setMsg(null), 6000)
    },
    onError: e => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })
  const delPayMut = useMutation({
    mutationFn: pid => api.delete(`/accounting/sale-payments/${pid}/`),
    onSuccess: () => { qc.invalidateQueries(['sale-invoice', id]); qc.invalidateQueries(['sale-invoices']); setMsg({ type: 'success', text: 'پرداخت حذف شد' }); setTimeout(() => setMsg(null), 2000) },
    onError: e => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })
  const statusMut = useMutation({
    mutationFn: s => api.patch(`/accounting/sale-invoices/${id}/`, { status: s }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(['sale-invoice', id]); qc.invalidateQueries(['sale-invoices']) },
  })
  // حذف فاکتور — فقط پیش‌نویس (تأییدشده/تسویه‌شده باید ابطال شود)
  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/accounting/sale-invoices/${id}/`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(['sale-invoices']); onClose() },
    onError: e => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در حذف فاکتور' }),
  })
  const [confirmDelete, setConfirmDelete] = useState(false)
  // ابطال فاکتور تأییدشده/تسویه‌شده — رکورد باقی می‌ماند، موجودی برمی‌گردد
  const voidMut = useMutation({
    mutationFn: () => api.post(`/accounting/sale-invoices/${id}/void/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['sale-invoice', id])
      qc.invalidateQueries(['sale-invoices'])
      toast.success('فاکتور باطل شد')
    },
    onError: e => toast.error(e.response?.data?.error || 'خطا در ابطال فاکتور'),
  })

  // ارسال دستی پیامک اطلاعات حساب پرداخت به مشتری (ورود دستی، هر حساب یک پیامک جدا)
  const [showSmsPicker, setShowSmsPicker] = useState(false)
  const smsMut = useMutation({
    mutationFn: accounts => api.post(`/accounting/sale-invoices/${id}/send-account-info/`, { accounts }).then(r => r.data),
    onSuccess: d => { setShowSmsPicker(false); toast.success(`${d.sent || ''} پیامک اطلاعات حساب ارسال شد`) },
    onError: e => toast.error(e.response?.data?.error || 'خطا در ارسال پیامک'),
  })

  function handleVoid() {
    if (window.confirm(`فاکتور ${inv.invoice_number} باطل شود؟\nموجودی اقلام برگردانده می‌شود و این عمل قابل بازگشت نیست.`)) {
      voidMut.mutate()
    }
  }

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!inv) return null

  return (
    <div className="space-y-4">
      {showPrint && <PrintModal inv={inv} onClose={() => setShowPrint(false)} isAdmin={isAdmin} />}
      {showSmsPicker && (
        <AccountSmsPicker
          customerName={inv.customer_name}
          phone={inv.customer_phone}
          pending={smsMut.isPending}
          onSend={accs => smsMut.mutate(accs)}
          onClose={() => setShowSmsPicker(false)}
        />
      )}
      {editPay && (
        <EditPaymentModal
          payment={editPay}
          accounts={accounts}
          onClose={() => setEditPay(null)}
          onSaved={() => {
            qc.invalidateQueries(['sale-invoice', id])
            qc.invalidateQueries(['sale-invoices'])
            setEditPay(null)
            setMsg({ type: 'success', text: 'پرداخت به‌روز شد' })
            setTimeout(() => setMsg(null), 2000)
          }}
        />
      )}
      <div className="card p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-bold text-white text-xl">{inv.invoice_number}</h2>
            <div className="text-xs text-gray-steel mt-1">
              {inv.source_display} | تاریخ فاکتور: <b className="text-white">{inv.issue_date ? jalaliText(inv.issue_date) : '—'}</b> | ثبت شده توسط {inv.created_by || '—'} در {formatDate(inv.created_at, { withTime: true })}
              {inv.updated_by && <> | ✏️ ویرایش شده توسط {inv.updated_by} در {formatDate(inv.updated_at, { withTime: true })}</>}
            </div>
            <div className="text-sm text-white mt-1">{inv.customer_name} | {inv.customer_phone}</div>
            {inv.seller_name && <div className="text-xs text-gray-steel mt-0.5">🧑‍💼 فروشنده: <b className="text-white">{inv.seller_name}</b></div>}
            {inv.order_number && <div className="text-xs text-blue-400 mt-0.5">سفارش: {inv.order_number}</div>}
          </div>
          <div className="flex items-center gap-3">
            {['draft', 'confirmed'].includes(inv.status) && can('sale_edit') && (
              <button onClick={onEdit} className="btn-secondary text-xs px-4 py-2 font-semibold">✏️ ویرایش فاکتور</button>
            )}
            {can('sale_edit') && inv.status === 'draft' && (
              confirmDelete ? (
                <span className="flex items-center gap-2">
                  <span className="text-[10px] text-red-400">فاکتور پیش‌نویس حذف شود؟</span>
                  <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                    className="text-xs px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 disabled:opacity-50">
                    {deleteMut.isPending ? '...' : 'بله، حذف'}
                  </button>
                  <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-steel hover:text-white">خیر</button>
                </span>
              ) : (
                <button onClick={() => setConfirmDelete(true)}
                  className="text-xs px-3 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors font-semibold">
                  🗑 حذف
                </button>
              )
            )}
            {can('sale_edit') && ['confirmed', 'paid'].includes(inv.status) && (
              <button onClick={handleVoid} disabled={voidMut.isPending}
                className="text-xs px-3 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors font-semibold disabled:opacity-50">
                {voidMut.isPending ? '...' : '⛔ ابطال فاکتور'}
              </button>
            )}
            <button onClick={() => setShowPrint(true)} className="btn-primary text-xs px-4 py-2 font-semibold">🖨️ چاپ / PDF</button>
            {can('sale_view') && ['confirmed', 'paid'].includes(inv.status) && (
              <button onClick={() => setShowSmsPicker(true)}
                title="ارسال پیامک مبلغ + شماره حساب به مشتری"
                className="text-xs px-3 py-2 rounded-lg text-brand border border-brand/40 hover:bg-brand/10 transition-colors font-semibold">
                💬 پیامک حساب
              </button>
            )}
            <span style={{ color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20', padding: '4px 12px', borderRadius: 20, fontSize: 12 }}>{inv.status_display}</span>
            <button onClick={onClose} className="text-gray-steel hover:text-white">✕</button>
          </div>
        </div>
        <div className="grid grid-cols-5 gap-3">
          {[{ label:'جمع کل', value:fmt(inv.subtotal)+' ریال', color:'var(--color-text-primary)' },{ label:'تخفیف', value:fmt(inv.discount_amount)+' ریال', color:'#FF9500' },{ label:'مبلغ نهایی', value:fmt(inv.total_amount)+' ریال', color:'#0066FF' },{ label:'پرداخت شده', value:fmt(inv.paid_amount)+' ریال', color:'#00C896' },{ label:'مانده', value:fmt(inv.remaining_amount)+' ریال', color:inv.remaining_amount>0?'#FF3B3B':'#00C896' }].map(item => (
            <div key={item.label} className="bg-white/5 rounded-lg p-3 text-center">
              <div className="text-[10px] text-gray-steel mb-1">{item.label}</div>
              <div className="text-sm font-bold" style={{ color: item.color }}>{item.value}</div>
            </div>
          ))}
        </div>
        {isSuperuser && (
          <div className="mt-3 flex gap-4 text-xs">
            <span className="text-gray-steel">بهای تمام شده: <span className="text-white">{fmt(inv.total_cost)} ریال</span></span>
            <span className="text-gray-steel">سود: <span className={inv.gross_profit >= 0 ? 'text-green-400' : 'text-red-400'}>{fmt(inv.gross_profit)} ریال</span></span>
          </div>
        )}
        {can('sale_edit') && (
          <div className="flex gap-2 mt-4">
            {['draft','confirmed','paid','cancelled'].map(s => (
              <button key={s} onClick={() => statusMut.mutate(s)} disabled={inv.status === s}
                style={{ borderColor: inv.status===s ? STATUS_COLORS[s] : 'transparent', color: STATUS_COLORS[s] }}
                className="text-xs px-3 py-1.5 rounded-lg border-2 bg-white/5 disabled:opacity-100 hover:bg-white/10 transition-all">
                {STATUS_LABELS[s]}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-3">اقلام فاکتور</h3>
        <div className="overflow-x-auto">
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
            <thead>
              <tr style={{ borderBottom:'0.5px solid rgba(255,255,255,0.1)' }}>
                {['کالا','SKU','تعداد','قیمت واحد','تخفیف%','جمع',...(isSuperuser ? ['بهای تمام شده','سود'] : [])].map(h => (
                  <th key={h} style={{ padding:'6px 10px', textAlign:'right', color:'var(--color-text-secondary)', fontWeight:500, whiteSpace:'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inv.items?.map((item, i) => (
                <tr key={item.id} style={{ borderBottom:'0.5px solid rgba(255,255,255,0.05)', background:i%2?'rgba(255,255,255,0.02)':'transparent' }}>
                  <td style={{ padding:'8px 10px' }}>{item.product_name}</td>
                  <td style={{ padding:'8px 10px', color:'var(--color-text-secondary)', fontSize:11 }}>{item.variant_sku}</td>
                  <td style={{ padding:'8px 10px', textAlign:'center' }}>{fmt(item.quantity)}</td>
                  <td style={{ padding:'8px 10px' }}>{fmt(item.unit_price)}</td>
                  <td style={{ padding:'8px 10px', textAlign:'center', color:'#FF9500' }}>{item.discount_percent > 0 ? item.discount_percent + '%' : '—'}</td>
                  <td style={{ padding:'8px 10px', fontWeight:600, color:'#0066FF' }}>{fmt(item.subtotal)}</td>
                  {isSuperuser && <td style={{ padding:'8px 10px', color:'var(--color-text-secondary)' }}>{fmt(item.total_cost)}</td>}
                  {isSuperuser && <td style={{ padding:'8px 10px', fontWeight:600, color:item.profit>=0?'#00C896':'#FF3B3B' }}>{fmt(item.profit)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">پرداخت‌ها</h3>
          {inv.remaining_amount > 0 && can('sale_payment') && <button onClick={() => setPayForm(f => ({ ...f, show: true }))} className="text-xs text-brand hover:text-brand/80">+ ثبت پرداخت</button>}
        </div>
        {payForm.show && (
          <div className="bg-white/5 rounded-xl p-4 mb-4 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div><label className="label text-xs mb-1 block">روش</label>
                <select value={payForm.method} onChange={e => setPayForm(f => ({ ...f, method: e.target.value }))} className="input text-xs">
                  <option value="cash">نقد</option><option value="transfer">حواله</option><option value="card">کارت</option><option value="online">آنلاین</option><option value="credit">نسیه</option>
                </select></div>
              <div><label className="label text-xs mb-1 block">مبلغ</label><AmountInput value={payForm.amount} onChange={e => setPayForm(f => ({ ...f, amount: e.target.value }))} className="input text-xs" /></div>
              <div><label className="label text-xs mb-1 block">حساب</label>
                <select value={payForm.to_account_id} onChange={e => setPayForm(f => ({ ...f, to_account_id: e.target.value }))} className="input text-xs">
                  <option value="">انتخاب...</option>{accounts.filter(a => a.currency === 'IRR').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select></div>
              <div><label className="label text-xs mb-1 block">تاریخ</label><input type="date" value={payForm.date} onChange={e => setPayForm(f => ({ ...f, date: e.target.value }))} className="input text-xs" /></div>
              <div className="col-span-2"><label className="label text-xs mb-1 block">پیگیری</label><input value={payForm.reference} onChange={e => setPayForm(f => ({ ...f, reference: e.target.value }))} className="input text-xs" /></div>
            </div>
            {msg && <div className={`text-xs rounded-lg px-3 py-2 ${msg.type==='success'?'bg-green-500/20 text-green-400':'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}
            <div className="flex gap-2">
              <button onClick={() => payMut.mutate({ invoice_id:id, ...payForm })} disabled={!payForm.amount || payMut.isPending} className="btn-primary text-xs px-4 py-2 disabled:opacity-50">ثبت</button>
              <button onClick={() => setPayForm(f => ({ ...f, show:false }))} className="btn-secondary text-xs px-4 py-2">انصراف</button>
            </div>
          </div>
        )}
        {msg && !payForm.show && <div className={`mb-3 text-xs rounded-lg px-3 py-2 ${msg.type==='success'?'bg-green-500/20 text-green-400':'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}
        {(inv.payments||[]).length === 0 ? <div className="text-center py-4 text-gray-steel text-xs">پرداختی ثبت نشده</div> : (
          <div className="space-y-2">
            {inv.payments.map(p => (
              <div key={p.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
                <div><div className="text-xs text-white">{p.method_display}{p.to_account?' → '+p.to_account:''}</div><div className="text-[10px] text-gray-steel">{formatDate(p.date)}{p.reference?' | '+p.reference:''} | {p.created_by}</div></div>
                <div className="flex items-center gap-3">
                  <div className="text-sm font-bold text-green-400">{fmt(p.amount)} ریال</div>
                  {can('sale_edit') && (
                    <>
                      <button onClick={() => setEditPay(p)} className="text-[11px] text-brand hover:text-brand/80">ویرایش</button>
                      <button onClick={() => { if (window.confirm('این پرداخت حذف شود؟')) delPayMut.mutate(p.id) }}
                        disabled={delPayMut.isPending}
                        className="text-[11px] text-red-400 hover:text-red-300 disabled:opacity-50">حذف</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── فیلد قیمت فروش با راهنمای آخرین فروش (قیمت + نحوه تسویه + تاریخ) ──
function SalePriceField({ value, onChange, onEnter, customerId, variantId, disabled, className = 'input text-xs' }) {
  const { data: last } = useQuery({
    queryKey: ['sale-last-price', customerId, variantId],
    queryFn: () => api.get('/accounting/sale-invoices/last-price/', {
      params: { customer_id: customerId, variant_id: variantId },
    }).then(r => r.data),
    enabled: !!customerId && !!variantId,
  })
  return (
    <div>
      <AmountInput value={value} onChange={onChange} disabled={disabled}
        placeholder={last?.found ? String(last.unit_price) : '0'}
        className={className} data-flow="si"
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); onEnter ? onEnter(e) : advanceFlow('si', e.target) } }} />
      {last?.found && (
        <div className="text-[10px] text-gold mt-1 font-bold">
          آخرین فروش: {Number(last.unit_price).toLocaleString('fa-IR')} ریال — {last.settlement_display} — {formatDate(last.date)}
        </div>
      )}
    </div>
  )
}

function NewInvoiceForm({ onClose, onSuccess, prefillOrder, editing }) {
  const { creatableContactTypes } = usePermissions()
  const canCreateContact = creatableContactTypes === null || creatableContactTypes.length > 0
  const { data: variants = [] } = useQuery({ queryKey:['variants-list'], queryFn:()=>api.get('/catalog/variants/').then(r=>r.data) })
  const qc = useQueryClient()
  const { data: editInv, isLoading: editLoading } = useQuery({ queryKey:['sale-invoice',editing], queryFn:()=>api.get(`/accounting/sale-invoices/${editing}/`).then(r=>r.data), enabled:!!editing })
  const [customerSearch, setCustomerSearch] = useState('')
  const [custIdx, setCustIdx] = useState(-1)   // ناوبری کیبوردی دراپ‌داون مشتری
  const [customer, setCustomer] = useState(prefillOrder?{id:prefillOrder.customer_id,name:prefillOrder.customer_name,phone:prefillOrder.customer_phone}:null)
  const [custHdr, setCustHdr] = useState({ customer_name:'', customer_phone:'' })
  const [showCustomerDrop, setShowCustomerDrop] = useState(false)
  const [showQuickAdd, setShowQuickAdd] = useState(false)
  const [pendingContact, setPendingContact] = useState(null)  // طرف حساب بدون موبایل معتبر — فرم تکمیلی
  const [pendingPhone, setPendingPhone] = useState('')
  const { data: customers = [] } = useQuery({ queryKey:['customer-search',customerSearch], queryFn:()=>api.get('/accounting/customer-search/',{params:{q:customerSearch}}).then(r=>r.data), enabled:!editing&&customerSearch.length>=2 })
  // فروشنده — از پرسنل فعال؛ seller_id همان user_id پرسنل است که بک‌اند روی فاکتور می‌نشاند
  const { data: staffList = [] } = useQuery({ queryKey:['seller-staff'], queryFn:()=>api.get('/accounting/staff/').then(r=>r.data) })
  const [sellerId, setSellerId] = useState('')
  const [items, setItems] = useState(prefillOrder?.items?.map(i=>({variant_id:String(i.variant_id),quantity:String(i.quantity),unit_price:String(i.unit_price),discount_percent:'0'}))||[{variant_id:'',quantity:'',unit_price:'',discount_percent:'0'}])
  const [hdr, setHdr] = useState({discount_amount:'0',shipping_cost:'0',tax_amount:'0',note:'',status:'confirmed',order_id:prefillOrder?.id||'',source:prefillOrder?'order':'manual'})
  const [initialized, setInitialized] = useState(false)
  const [msg, setMsg] = useState(null)
  // فروش داخلی/خارجی + نحوه تسویه + موعد
  const [settlement, setSettlement] = useState('cash')
  const [dueDate, setDueDate] = useState('')
  const [issueDate, setIssueDate] = useState('')  // تاریخ صدور فاکتور — خالی یعنی امروز

  // نرخ یوان مرجع روز — تبدیل قیمت فروش خارجی به یوان
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  const dayRate = Number(rateData?.rate_cny_to_irt || 0)

  // موعد تسویه تو حسابی — ثابت ۱۴ روز از تاریخ صدور، بدون سؤال از کاربر
  useEffect(() => {
    if (settlement !== 'credit') return
    const d = issueDate ? new Date(issueDate + 'T00:00:00') : new Date()
    d.setDate(d.getDate() + 14)
    setDueDate(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`)
  }, [settlement, issueDate])

  // سطح مشتری و کلید ستون قیمت — قیمت کالا بر اساس همین انتخاب می‌شود
  const tier = customer?.tier || 'public'
  const priceKey = tier === 'platinum' ? settlement
    : tier === 'silver' ? 'month1'
    : tier === 'gold' ? 'credit'
    : 'retail'

  // با انتخاب مشتری، نحوه تسویه پیش‌فرض بر اساس سطحش (فروش خارجی همیشه انتخابی است)
  // سیلور و گلد تسویه‌شان نقدی است — ستون یکماهه/توحسابی فقط مبنای «قیمت» آن‌هاست، نه نوع تسویه
  useEffect(() => {
    if (!customer) return
    setSettlement(tier === 'platinum' ? 'credit' : 'cash')
  }, [customer?.id])

  // قیمت فرمول واریانت‌ها برای همین مشتری
  const { data: variantsPricing = [] } = useQuery({
    queryKey: ['variants-pricing', customer?.id],
    queryFn: () => api.get('/catalog/variants/', { params: { for_user: customer.id } }).then(r => r.data),
    enabled: !!customer && !editing,
  })
  const variantById = Object.fromEntries(variantsPricing.map(v => [String(v.id), v]))
  const priceDefault = (v) => {
    const p = v?.pricing
    if (!p) return ''
    if (p.tier === 'platinum' && p.options) return p.options[priceKey] ?? p.price
    return p.price
  }

  // پیش‌پر کردن فرم در حالت ویرایش
  if (editing && editInv && !initialized) {
    setInitialized(true)
    setCustHdr({ customer_name: editInv.customer_name || '', customer_phone: editInv.customer_phone || '' })
    setIssueDate(editInv.issue_date || '')
    setSellerId(editInv.seller_id ? String(editInv.seller_id) : '')
    setItems(editInv.items?.length ? editInv.items.map(i => ({
      variant_id: String(i.variant_id),
      quantity: String(i.quantity),
      unit_price: String(i.unit_price),
      discount_percent: String(i.discount_percent ?? '0'),
    })) : [{ variant_id:'', quantity:'', unit_price:'', discount_percent:'0' }])
    setHdr(h => ({
      ...h,
      discount_amount: String(editInv.discount_amount ?? '0'),
      shipping_cost: String(editInv.shipping_cost ?? '0'),
      tax_amount: String(editInv.tax_amount ?? '0'),
      note: editInv.note || '',
    }))
  }

  // آیتم‌ها فقط برای فاکتورهای دستی قابل ویرایش‌اند
  const itemsEditable = !editing || editInv?.source === 'manual'

  const createMut = useMutation({
    mutationFn:d=>api.post('/accounting/sale-invoices/',d).then(r=>r.data),
    onSuccess:data=>{setMsg({type:'success',text:`فاکتور ${data.invoice_number} صادر شد`});qc.invalidateQueries(['sale-invoices']);qc.invalidateQueries(['pending-orders']);setTimeout(()=>onSuccess?.(data.id),1500)},
    onError:e=>setMsg({type:'error',text:e.response?.data?.error||'خطا'}),
  })
  const editMut = useMutation({
    mutationFn:d=>api.patch(`/accounting/sale-invoices/${editing}/`,d).then(r=>r.data),
    onSuccess:()=>{setMsg({type:'success',text:'تغییرات فاکتور ذخیره شد'});qc.invalidateQueries(['sale-invoices']);qc.invalidateQueries(['sale-invoice',editing]);setTimeout(()=>onSuccess?.(),800)},
    onError:e=>setMsg({type:'error',text:e.response?.data?.error||'خطا'}),
  })
  const calcSubtotal=()=>items.reduce((s,it)=>s+Math.round((Number(it.quantity)||0)*(Number(it.unit_price)||0)*(1-(Number(it.discount_percent)||0)/100)),0)
  const total=calcSubtotal()-Number(hdr.discount_amount||0)+Number(hdr.shipping_cost||0)+Number(hdr.tax_amount||0)
  function handleSubmit(){
    if (editing) {
      if(!custHdr.customer_name)return setMsg({type:'error',text:'نام مشتری الزامی است'})
      const payload = {
        customer_name: custHdr.customer_name,
        customer_phone: custHdr.customer_phone,
        seller_id: sellerId ? Number(sellerId) : null,
        discount_amount: Number(hdr.discount_amount||0),
        shipping_cost: Number(hdr.shipping_cost||0),
        tax_amount: Number(hdr.tax_amount||0),
        note: hdr.note,
        issue_date: issueDate || null,
      }
      if (itemsEditable) {
        if(items.some(it=>!it.variant_id||!it.quantity||!it.unit_price))return setMsg({type:'error',text:'اطلاعات اقلام را کامل کنید'})
        payload.items = items.map(it=>({variant_id:it.variant_id,quantity:Number(it.quantity),unit_price:Number(it.unit_price),discount_percent:Number(it.discount_percent||0)}))
      }
      editMut.mutate(payload)
      return
    }
    if(!customer)return setMsg({type:'error',text:'مشتری را انتخاب کنید'})
    if(settlement==='credit'&&!dueDate)return setMsg({type:'error',text:'موعد تسویه را برای فاکتور تو حسابی وارد کنید'})
    // ردیف‌های کاملاً خالی (مثل ردیف خودکار Enter) نادیده گرفته می‌شوند
    const filled = items.filter(it=>it.variant_id||it.quantity||it.unit_price)
    if(!filled.length)return setMsg({type:'error',text:'حداقل یک قلم کالا وارد کنید'})
    if(filled.some(it=>!it.variant_id||!it.quantity||!it.unit_price))return setMsg({type:'error',text:'اطلاعات اقلام را کامل کنید'})
    createMut.mutate({customer_id:customer.id,customer_name:customer.name,customer_phone:customer.phone||'',...hdr,
      sale_type:'domestic',currency:'IRR',settlement,due_date:dueDate||null,issue_date:issueDate||null,
      seller_id: sellerId ? Number(sellerId) : null,
      items:filled.map(it=>({...it,quantity:Number(it.quantity),unit_price:Number(it.unit_price),discount_percent:Number(it.discount_percent)}))})
  }
  if (editing && editLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  return (
    <div className="space-y-4">
      {showQuickAdd&&<AddContactModal forInvoice creatableTypes={creatableContactTypes} onClose={()=>setShowQuickAdd(false)} onCreated={c=>{setCustomer(c);setCustomerSearch(c.name);setShowQuickAdd(false)}} />}
      <div className="card p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
          <h3 className="text-sm font-semibold text-white">اطلاعات مشتری</h3>
          {/* تاریخ صدور فاکتور — سمت چپ کارت؛ خالی یعنی امروز */}
          <div className="w-full sm:w-72">
            <label className="label text-xs mb-1 block">📅 تاریخ فاکتور <span className="text-gray-steel font-normal">(خالی = امروز)</span></label>
            <JalaliDateInput value={issueDate} onChange={setIssueDate} />
          </div>
        </div>
        {editing ? (
          <div className="grid grid-cols-2 gap-3 max-w-lg">
            <div>
              <label className="label text-xs mb-1 block">نام مشتری *</label>
              <input value={custHdr.customer_name} onChange={e=>setCustHdr(c=>({...c,customer_name:e.target.value}))} className="input text-sm" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">تلفن</label>
              <input value={custHdr.customer_phone} onChange={e=>setCustHdr(c=>({...c,customer_phone:e.target.value}))} className="input text-sm" dir="ltr" />
            </div>
          </div>
        ) : (
        <div className="relative max-w-sm">
          <div className="flex items-center justify-between mb-1">
            <label className="label text-xs">جستجوی مشتری *</label>
            {canCreateContact && <button type="button" onClick={()=>setShowQuickAdd(true)} className="text-xs text-brand hover:text-brand/80 font-semibold">+ طرف حساب جدید</button>}
          </div>
          <div className="relative">
            <input value={customerSearch}
              onChange={e=>{
                setCustomerSearch(e.target.value)
                setShowCustomerDrop(true)
                setCustIdx(0)
                // وقتی کاربر شروع به تایپ می‌کند یعنی می‌خواهد مشتری دیگری — انتخاب قبلی پاک می‌شود
                if (customer) setCustomer(null)
              }}
              onFocus={e=>{ setShowCustomerDrop(true); if (customer) e.target.select() }}
              placeholder="نام یا شماره موبایل (فارسی/انگلیسی)..." className="input text-sm"
              style={customer ? { paddingLeft: '2rem' } : undefined}
              data-flow="si"
              onKeyDown={e=>{
                if(e.key==='ArrowDown'){e.preventDefault();setCustIdx(i=>Math.min(i+1,customers.length-1))}
                else if(e.key==='ArrowUp'){e.preventDefault();setCustIdx(i=>Math.max(i-1,0))}
                else if(e.key==='Enter'){
                  e.preventDefault()
                  const c = custIdx>=0 && customers[custIdx] ? customers[custIdx] : customers[0]
                  if (c) document.getElementById(`cust-opt-${c.id}`)?.click()
                  else advanceFlow('si', e.target)
                }
                else if(e.key==='Escape'){setShowCustomerDrop(false)}
              }} />
            {/* پاک کردن سریع انتخاب — داخل خود باکس */}
            {customer && (
              <button type="button" title="پاک کردن انتخاب"
                onClick={()=>{
                  setCustomer(null); setCustomerSearch(''); setDueDate('')
                  setTimeout(() => document.querySelector('input[data-flow="si"]')?.focus(), 0)
                }}
                className="absolute left-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/40 text-xs flex items-center justify-center">
                ✕
              </button>
            )}
          </div>
          {showCustomerDrop&&customers.length>0&&(
            <div className="absolute z-50 top-full right-0 left-0 mt-1 bg-navy border border-white/10 rounded-xl shadow-xl overflow-hidden">
              {customers.map((c, ci)=>(<button key={c.id} id={`cust-opt-${c.id}`}
                className={`w-full text-right px-4 py-3 border-b border-white/5 last:border-0 ${ci===custIdx?'bg-brand/20':'hover:bg-white/5'}`}
                onMouseEnter={()=>setCustIdx(ci)}
                onClick={async ()=>{
                  if (c.is_contact) {
                    // طرف حساب دستی — اگر موبایل معتبر ندارد، اول موبایل می‌پرسیم
                    if (!/^09\d{9}$/.test(c.phone || '')) {
                      setPendingContact(c)
                      setPendingPhone('')
                      setShowCustomerDrop(false)
                      return
                    }
                    try {
                      const r = await api.post('/accounting/customers/', { name: c.name, phone: c.phone, contact_id: c.id }).then(r => r.data)
                      setCustomer({ id: r.id, name: r.name, phone: r.phone, tier: r.tier || 'public' })
                    } catch (e) {
                      setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت مشتری' })
                      setShowCustomerDrop(false)
                      return
                    }
                  } else setCustomer(c)
                  setCustomerSearch(c.name)
                  setShowCustomerDrop(false)
                }}>
                <div className="flex items-center justify-between">
                  <div className="text-sm text-white">{c.name}{c.is_contact && <span className="text-[9px] text-gray-steel mr-1">(طرف حساب)</span>}</div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${c.tier==='public'?'bg-white/10 text-gray-steel':'bg-brand/20 text-brand'}`}>{TIER_LABELS[c.tier]||c.tier}</span>
                </div>
                <div className="text-xs text-gray-steel" dir="ltr">{c.phone}</div></button>))}
            </div>
          )}
          {showCustomerDrop&&<div className="fixed inset-0 z-40" onClick={()=>setShowCustomerDrop(false)} />}
          {/* فرم تکمیلی — طرف حساب بدون موبایل: اول موبایل گرفته می‌شود بعد مشتری ثبت می‌شود */}
          {pendingContact && !customer && (
            <div className="mt-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3">
              <div className="text-xs text-yellow-400 font-bold mb-2">📱 برای ثبت «{pendingContact.name}» موبایل لازم است</div>
              <div className="flex gap-2">
                <input value={pendingPhone} onChange={e=>setPendingPhone(e.target.value.replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))}
                  placeholder="09123456789" dir="ltr" className="input text-sm flex-1" maxLength={11} />
                <button type="button"
                  onClick={async ()=>{
                    if (!/^09\d{9}$/.test(pendingPhone)) return setMsg({type:'error',text:'شماره موبایل معتبر نیست (مثال: 09123456789)'})
                    try {
                      const r = await api.post('/accounting/customers/', { name: pendingContact.name, phone: pendingPhone, contact_id: pendingContact.id }).then(r => r.data)
                      setCustomer({ id: r.id, name: r.name, phone: r.phone, tier: r.tier || 'public' })
                      setCustomerSearch(pendingContact.name)
                      setPendingContact(null)
                    } catch (e) { setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت مشتری' }) }
                  }}
                  className="btn-primary text-xs px-4">ثبت و انتخاب</button>
                <button type="button" onClick={()=>setPendingContact(null)} className="btn-secondary text-xs px-3">انصراف</button>
              </div>
            </div>
          )}
          {customer&&(
            <div className="flex items-center gap-2 mt-1">
              <div className="text-xs text-green-400">✓ {customer.name} | {customer.phone} — <b>{TIER_LABELS[tier]}</b></div>
              <button type="button"
                onClick={()=>{ setCustomer(null); setCustomerSearch(''); setDueDate('') }}
                className="text-[10px] text-gray-steel hover:text-red-400 transition-colors">
                ✕ تغییر مشتری
              </button>
            </div>
          )}
        </div>
        )}

        {/* فروشنده — پرسنل فعال از همان اندپوینت پرسنل؛ پیش‌فرض «بدون فروشنده» */}
        <div className="mt-4 pt-4 border-t border-white/10 max-w-sm">
          <label className="label text-xs mb-1 block">🧑‍💼 فروشنده</label>
          <SearchSelect
            value={sellerId}
            onChange={setSellerId}
            placeholder="بدون فروشنده"
            options={[
              { value: '', label: 'بدون فروشنده' },
              ...staffList.map(s => ({ value: s.user_id, label: s.name, sub: s.phone })),
            ]}
          />
          {sellerId && (
            <button type="button" onClick={() => setSellerId('')}
              className="text-[10px] text-gray-steel hover:text-red-400 transition-colors mt-1">
              ✕ حذف فروشنده
            </button>
          )}
        </div>

        {/* نحوه تسویه — فقط پلاتینیوم انتخاب می‌کند؛ برای بقیه سطوح خودکار تعیین می‌شود
            و نمایش داده نمی‌شود (ستون قیمتِ سطح مشتری لو نمی‌رود). موعد تسویه فقط برای credit لازم است. */}
        {customer && !editing && (tier === 'platinum' || settlement === 'credit') && (
          <div className="mt-4 pt-4 border-t border-white/10">
            {tier === 'platinum' && (
              <>
                <label className="label text-xs mb-2 block">نحوه تسویه *</label>
                <div className="flex gap-2 flex-wrap">
                  {['credit','cash','month1'].map(k => (
                    <button key={k} type="button" onClick={()=>setSettlement(k)}
                      className={`text-xs px-4 py-2 rounded-xl border transition-all ${settlement===k?'border-brand bg-brand/10 text-brand':'border-white/10 text-gray-steel hover:border-brand/50'}`}>
                      {SETTLEMENT_LABELS[k]}
                    </button>
                  ))}
                </div>
              </>
            )}
            {/* موعد تسویه تو حسابی — ثابت ۱۴ روزه، بدون انتخاب دستی */}
            {settlement==='credit' && (
              <div className="mt-3 text-xs text-gray-steel">
                📅 موعد تسویه: <b className="text-white">۱۴ روز بعد{dueDate ? ` (${jalaliText(dueDate)})` : ''}</b> — خودکار
                {dueDate && jalaliHolidayInfo(dueDate) && (
                  <span className="text-red-400 font-bold mr-1">⚠️ این روز {jalaliHolidayInfo(dueDate)} است!</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      {/* گیت مراحل — تا مشتری مشخص نشود اقلام نمایش داده نمی‌شود (ستون قیمت به نوع مشتری بستگی دارد) */}
      {!customer && !editing ? (
        <div className="card p-8 text-center">
          <div className="text-3xl mb-2">👤</div>
          <div className="text-sm text-gray-steel">اول مشتری را انتخاب کنید تا اقلام فاکتور فعال شوند</div>
        </div>
      ) : (
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">اقلام فاکتور</h3>
          {itemsEditable&&<button onClick={()=>setItems(i=>[...i,{variant_id:'',quantity:'',unit_price:'',discount_percent:'0'}])} className="text-xs text-brand">+ افزودن کالا</button>}
        </div>
        {!itemsEditable&&(
          <div className="text-[11px] text-yellow-400 bg-yellow-500/10 rounded-lg px-3 py-2 mb-3">
            آیتم‌ها فقط برای فاکتورهای دستی قابل ویرایش هستند
          </div>
        )}
        <div className="space-y-3">
          {items.map((item,idx)=>(
            <div key={idx} className="bg-white/5 rounded-xl p-3">
              <div className="grid grid-cols-5 gap-3">
                <div className="col-span-2"><label className="label text-[10px] mb-1 block">کالا *</label>{itemsEditable?(
                  <SearchSelect
                    options={(editing ? variants : variantsPricing).map(v => ({ value: v.id, label: v.product_name,
                      sub: (
                        <span dir="rtl" className="inline-flex flex-wrap items-center gap-1.5">
                          <span dir="ltr" className="text-gray-steel">{v.sku}</span>
                          <span className={`font-bold ${Number(v.stock_quantity || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            موجودی: {Number(v.stock_quantity || 0).toLocaleString('fa-IR')}
                          </span>
                          {(v.stocks || []).map(s => (
                            <span key={s.warehouse} className="bg-white/10 rounded px-1.5 py-0.5 text-[9px]">
                              {s.warehouse}: <b>{Number(s.quantity).toLocaleString('fa-IR')}</b>
                            </span>
                          ))}
                        </span>
                      ),
                    }))}
                    value={item.variant_id}
                    onChange={val => setItems(i => i.map((it,j) => j===idx
                      ? { ...it, variant_id: val, unit_price: String(priceDefault(variantById[String(val)]) || it.unit_price) }
                      : it))}
                    placeholder="جستجوی کالا (نام یا کد)..."
                    className="input text-xs" flow="si"
                  />
                ):(<div className="text-xs text-white py-2">{variants.find(v=>String(v.id)===String(item.variant_id))?.product_name||`#${item.variant_id}`}<span className="text-gray-steel"> [{variants.find(v=>String(v.id)===String(item.variant_id))?.sku||''}]</span></div>)}</div>
                <div><label className="label text-[10px] mb-1 block">تعداد *</label><AmountInput value={item.quantity} data-flow="si"
                  onChange={e=>setItems(i=>i.map((it,j)=>j===idx?{...it,quantity:e.target.value}:it))}
                  onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();advanceFlow('si',e.target)}}}
                  className="input text-xs" disabled={!itemsEditable} /></div>
                <div><label className="label text-[10px] mb-1 block">قیمت واحد *</label>
                  {itemsEditable ? (
                    <SalePriceField value={item.unit_price}
                      onChange={e=>setItems(i=>i.map((it,j)=>j===idx?{...it,unit_price:e.target.value}:it))}
                      onEnter={(e)=>{
                        if (idx === items.length - 1) {
                          setItems(i=>[...i,{variant_id:'',quantity:'',unit_price:'',discount_percent:'0'}])
                          setTimeout(()=>advanceFlow('si',e.target),60)
                        } else advanceFlow('si',e.target)
                      }}
                      customerId={customer?.id} variantId={item.variant_id} />
                  ) : (
                    <AmountInput value={item.unit_price} className="input text-xs" disabled />
                  )}
                </div>
                <div><label className="label text-[10px] mb-1 block">تخفیف %</label><AmountInput value={item.discount_percent} onChange={e=>setItems(i=>i.map((it,j)=>j===idx?{...it,discount_percent:e.target.value}:it))} className="input text-xs" disabled={!itemsEditable} /></div>
              </div>
              <div className="flex items-center justify-between mt-2">
                <div className="text-xs text-gray-steel">جمع: <span className="text-white font-bold">{fmt(Math.round((Number(item.quantity)||0)*(Number(item.unit_price)||0)*(1-(Number(item.discount_percent)||0)/100)))}</span> ریال</div>
                {itemsEditable&&items.length>1&&<button onClick={()=>setItems(i=>i.filter((_,j)=>j!==idx))} className="text-xs text-red-400">× حذف</button>}
              </div>
            </div>
          ))}
        </div>
      </div>
      )}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">تخفیف و هزینه‌های اضافی</h3>
        <div className="grid grid-cols-4 gap-4">
          <div><label className="label text-xs mb-1 block">تخفیف کل</label><AmountInput value={hdr.discount_amount} onChange={e=>setHdr(h=>({...h,discount_amount:e.target.value}))} className="input text-sm" /></div>
          <div><label className="label text-xs mb-1 block">هزینه ارسال</label><AmountInput value={hdr.shipping_cost} onChange={e=>setHdr(h=>({...h,shipping_cost:e.target.value}))} className="input text-sm" /></div>
          <div><label className="label text-xs mb-1 block">مالیات</label><AmountInput value={hdr.tax_amount} onChange={e=>setHdr(h=>({...h,tax_amount:e.target.value}))} className="input text-sm" /></div>
          {!editing&&<div><label className="label text-xs mb-1 block">وضعیت</label><select value={hdr.status} onChange={e=>setHdr(h=>({...h,status:e.target.value}))} className="input text-sm"><option value="draft">پیش‌نویس</option><option value="confirmed">تأیید شده</option></select></div>}
        </div>
        <div className="mt-3"><label className="label text-xs mb-1 block">توضیحات</label><input value={hdr.note} onChange={e=>setHdr(h=>({...h,note:e.target.value}))} className="input text-sm" /></div>
        <div className="mt-4 text-left"><div className="text-xs text-gray-steel">مبلغ نهایی:</div><div className="text-2xl font-bold text-brand">{fmt(total)} ریال</div></div>
      </div>
      {msg&&<div className={`rounded-lg px-4 py-3 text-sm ${msg.type==='success'?'bg-green-500/20 text-green-400':'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}
      <div className="flex gap-3">
        <button onClick={handleSubmit} disabled={createMut.isPending||editMut.isPending} className="btn-primary flex-1 py-3 disabled:opacity-50">{createMut.isPending||editMut.isPending?(editing?'در حال ذخیره...':'در حال صدور...'):editing?'ذخیره تغییرات فاکتور':'صدور فاکتور'}</button>
        <button onClick={onClose} className="btn-secondary px-6 py-3">انصراف</button>
      </div>
    </div>
  )
}

// ─── کارت گزارش کانال فروش — سهم فروش حضوری در برابر سایت ─────
function SalesChannelCard() {
  const { data } = useQuery({
    queryKey: ['sales-channels'],
    queryFn: () => api.get('/accounting/reports/sales-channels/').then(r => r.data),
    staleTime: 60000,
  })
  if (!data || !data.total_count) return null
  const manual = data.channels.find(c => c.key === 'manual') || {}
  const online = data.channels.find(c => c.key === 'order') || {}
  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-white">کانال فروش</span>
        <span className="text-[10px] text-gray-steel">{Number(data.total_count).toLocaleString('fa-IR')} فاکتور تأییدشده</span>
      </div>
      {/* نوار دوتکه — سهم مبلغی هر کانال */}
      <div className="flex h-2 rounded-full overflow-hidden bg-white/5 mb-3">
        <div style={{ width: `${manual.amount_percent || 0}%`, background: '#FBC02D' }} />
        <div style={{ width: `${online.amount_percent || 0}%`, background: '#0066FF' }} />
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: '#FBC02D' }} />
          <div>
            <div className="text-gray-steel">فروش حضوری</div>
            <div className="text-white font-bold">{fmt(manual.total_irr)} ریال <span className="text-brand">({Number(manual.amount_percent || 0).toLocaleString('fa-IR')}٪)</span></div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: '#0066FF' }} />
          <div>
            <div className="text-gray-steel">فروش سایت</div>
            <div className="text-white font-bold">{fmt(online.total_irr)} ریال <span className="text-brand">({Number(online.amount_percent || 0).toLocaleString('fa-IR')}٪)</span></div>
          </div>
        </div>
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
  const { can } = usePermissions()

  const { data: me } = useQuery({ queryKey:['me'], queryFn:()=>api.get('/users/me/').then(r=>r.data), staleTime:60000 })
  const isAdmin = me?.is_staff || false

  // فیلتر سررسید تسویه — لینک از بج منو با ?due=1
  const [searchParams] = useSearchParams()
  const [dueOnly, setDueOnly] = useState(searchParams.get('due') === '1')
  // پیش‌فرض فقط فاکتورهای باز — تسویه‌شده‌ها لیست را شلوغ نکنند
  const [statusFilter, setStatusFilter] = useState('open')
  // فیلتر بازه زمانی (روی تاریخ صدور) + جستجوی مشتری/شماره فاکتور
  const [invQ, setInvQ] = useState('')
  const [invQd, setInvQd] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  useEffect(() => { const t = setTimeout(() => setInvQd(invQ.trim()), 400); return () => clearTimeout(t) }, [invQ])
  const { data: badges } = useQuery({ queryKey:['admin-badges'], queryFn:()=>api.get('/users/admin-badges/').then(r=>r.data), staleTime:15000, refetchInterval:30000 })

  // صفحه‌بندی واقعی سمت سرور — با رشد تعداد فاکتورها لیست سنگین نمی‌شود
  const PAGE_SIZE = 50
  const [page, setPage] = useState(1)
  useEffect(() => setPage(1), [dueOnly, statusFilter, invQd, dateFrom, dateTo])
  const { data: invData, isLoading } = useQuery({
    queryKey:['sale-invoices', dueOnly, statusFilter, invQd, dateFrom, dateTo, page],
    queryFn:()=>{
      const params = { ...(dueOnly ? { due:'1' } : { status: statusFilter }), page, page_size: PAGE_SIZE }
      if (invQd) params.q = invQd
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      return api.get('/accounting/sale-invoices/', { params }).then(r=>r.data)
    },
    enabled:view==='list',
  })
  const invoices = invData?.results || []
  const invTotal = invData?.count || 0
  const pageCount = Math.max(1, Math.ceil(invTotal / PAGE_SIZE))
  const { data: pendingOrders=[] } = useQuery({ queryKey:['pending-orders'], queryFn:()=>api.get('/accounting/pending-orders/').then(r=>r.data), enabled:view==='list' })

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {view!=='list'&&<button onClick={()=>{setView('list');setPrefillOrder(null)}} className="text-gray-steel hover:text-white text-sm">← برگشت</button>}
          <h1 className="font-display font-bold text-2xl text-white">{view==='list'?'فاکتورهای فروش':view==='new'?'فاکتور جدید':view==='edit'?'ویرایش فاکتور':'جزئیات فاکتور'}</h1>
        </div>
        {view==='list'&&can('sale_create')&&<button onClick={()=>setView('new')} className="btn-primary text-sm px-4 py-2">+ فاکتور جدید</button>}
      </div>

      {view==='list'&&(
        <>
          <SalesChannelCard />
          {/* هشدار سررسید تسویه فاکتورهای تو حسابی */}
          {badges?.sales_due > 0 && (
            <button onClick={()=>setDueOnly(d=>!d)}
              className={`w-full text-right rounded-xl border p-3 mb-4 text-xs transition-all ${dueOnly ? 'border-red-400 bg-red-500/20 text-red-300' : 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20'}`}>
              ⚠️ <b>{Number(badges.sales_due).toLocaleString('fa-IR')}</b> فاکتور تو حسابی به موعد تسویه رسیده است
              {dueOnly ? ' — نمایش فیلترشده ✓ (برای نمایش همه کلیک کنید)' : ' — برای رسیدگی کلیک کنید'}
            </button>
          )}
          <div className="flex gap-2 mb-4 border-b border-white/10">
            {[['invoices',`فاکتورها (${invTotal.toLocaleString('fa-IR')})`],['pending',`سفارشات در انتظار (${pendingOrders.filter(o=>!o.has_invoice).length})`]].map(([k,v])=>(
              <button key={k} onClick={()=>setTab(k)} className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${tab===k?'border-brand text-white bg-brand/10':'border-transparent text-gray-steel hover:text-white'}`}>{v}</button>
            ))}
          </div>
          {tab==='invoices'&&(
            <div className="card p-5">
              {!dueOnly&&(
                <div className="flex gap-1 mb-4 bg-white/5 rounded-lg p-1 w-fit">
                  {[['open','باز'],['paid','تسویه‌شده'],['all','همه']].map(([k,v])=>(
                    <button key={k} onClick={()=>setStatusFilter(k)}
                      className={`text-xs px-4 py-1.5 rounded-md transition-all ${statusFilter===k?'bg-brand text-white':'text-gray-steel hover:text-white'}`}>{v}</button>
                  ))}
                </div>
              )}
              {/* فیلتر مشتری و بازه زمانی صدور — هر کدام خالی بماند اعمال نمی‌شود؛ برای یک روز خاص هر دو تاریخ را همان روز بگذارید */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
                <input value={invQ} onChange={e=>setInvQ(e.target.value)} className="input text-xs"
                  placeholder="جستجو: نام/موبایل مشتری یا شماره فاکتور..." />
                <div className="flex items-center gap-1">
                  <span className="text-[10px] text-gray-steel whitespace-nowrap">از</span>
                  <JalaliDateInput value={dateFrom} onChange={setDateFrom} className="input text-xs" />
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[10px] text-gray-steel whitespace-nowrap">تا</span>
                  <JalaliDateInput value={dateTo} onChange={setDateTo} className="input text-xs" />
                </div>
              </div>
              {isLoading?<div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>:invoices.length===0?(
                <div className="text-center py-12"><div className="text-4xl mb-3">🧾</div><div className="text-gray-steel text-sm mb-4">{statusFilter==='open'?'فاکتور بازی نیست':statusFilter==='paid'?'فاکتور تسویه‌شده‌ای نیست':'هنوز فاکتوری صادر نشده'}</div>{statusFilter==='open'&&can('sale_create')&&<button onClick={()=>setView('new')} className="btn-primary text-sm px-6 py-2">+ صدور فاکتور</button>}</div>
              ):(
                <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
                  <thead><tr style={{borderBottom:'0.5px solid rgba(255,255,255,0.1)'}}>{['شماره فاکتور','مشتری','تاریخ','وضعیت','مبلغ نهایی','پرداخت شده','مانده','تسویه','ثبت‌کننده',''].map(h=><th key={h} style={{padding:'8px 12px',textAlign:'right',color:'var(--color-text-secondary)',fontWeight:500,whiteSpace:'nowrap'}}>{h}</th>)}</tr></thead>
                  <tbody>
                    {invoices.map((inv,i)=>(
                      <tr key={inv.id} style={{borderBottom:'0.5px solid rgba(255,255,255,0.05)',background:i%2?'rgba(255,255,255,0.02)':'transparent'}}>
                        <td style={{padding:'10px 12px',fontWeight:600,color:'#0066FF'}}>{inv.invoice_number}</td>
                        <td style={{padding:'10px 12px'}}><div>{inv.customer_name}</div><div style={{fontSize:11,color:'var(--color-text-secondary)'}}>{inv.customer_phone}</div></td>
                        <td style={{padding:'10px 12px',color:'var(--color-text-secondary)',fontSize:11}}>{inv.issue_date ? jalaliText(inv.issue_date) : formatDate(inv.created_at, { withTime: true })}</td>
                        <td style={{padding:'10px 12px'}}><span style={{color:STATUS_COLORS[inv.status],background:STATUS_COLORS[inv.status]+'20',padding:'2px 8px',borderRadius:20,fontSize:11}}>{inv.status_display}</span></td>
                        <td style={{padding:'10px 12px',fontWeight:600}}>{fmt(inv.total_amount)} ریال</td>
                        <td style={{padding:'10px 12px',color:'#00C896'}}>{fmt(inv.paid_amount)} ریال</td>
                        <td style={{padding:'10px 12px',color:inv.remaining_amount>0?'#FF3B3B':'#00C896',fontWeight:inv.remaining_amount>0?700:400}}>{inv.remaining_amount>0?fmt(inv.remaining_amount)+' ریال':'✓ تسویه'}</td>
                        <td style={{padding:'10px 12px',whiteSpace:'nowrap',color:'var(--color-text-secondary)',fontSize:12}}>{inv.settlement_display}</td>
                        <td style={{padding:'10px 12px',whiteSpace:'nowrap'}}>
                          <UserStamp createdBy={inv.created_by} updatedBy={inv.updated_by} createdAt={inv.created_at} updatedAt={inv.updated_at} />
                        </td>
                        <td style={{padding:'10px 12px'}}><button onClick={()=>{setSelectedId(inv.id);setView('detail')}} className="text-xs text-brand hover:text-brand/80">مشاهده</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {pageCount>1&&(
                <div className="flex items-center justify-center gap-3 mt-4 text-xs">
                  <button disabled={page<=1} onClick={()=>setPage(p=>p-1)}
                    className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-40 transition-all">→ قبلی</button>
                  <span className="text-gray-steel">صفحه {page.toLocaleString('fa-IR')} از {pageCount.toLocaleString('fa-IR')} — {invTotal.toLocaleString('fa-IR')} فاکتور</span>
                  <button disabled={page>=pageCount} onClick={()=>setPage(p=>p+1)}
                    className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-40 transition-all">بعدی ←</button>
                </div>
              )}
            </div>
          )}
          {tab==='pending'&&(
            <div className="space-y-3">
              {pendingOrders.filter(o=>!o.has_invoice).length===0?<div className="card p-12 text-center text-gray-steel text-sm">سفارش در انتظاری وجود ندارد</div>
              :pendingOrders.filter(o=>!o.has_invoice).map(order=>(
                <div key={order.id} className="card p-4">
                  <div className="flex items-start justify-between">
                    <div><div className="flex items-center gap-3"><span className="font-bold text-white text-sm">{order.order_number}</span><span style={{color:'#FF9500',background:'#FF950020',padding:'2px 8px',borderRadius:20,fontSize:11}}>{order.status_display}</span></div><div className="text-xs text-gray-steel mt-1">{order.customer_name} | {order.customer_phone}</div></div>
                    <div className="text-left"><div className="text-sm font-bold text-white">{fmt(order.total_amount)} ریال</div>{can('sale_create')&&<button onClick={()=>{setPrefillOrder(order);setView('new')}} className="btn-primary text-xs px-4 py-2 mt-2">صدور فاکتور</button>}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {view==='new'&&<NewInvoiceForm onClose={()=>{setView('list');setPrefillOrder(null)}} onSuccess={newId=>{setPrefillOrder(null);if(newId){setSelectedId(newId);setView('detail')}else setView('list')}} prefillOrder={prefillOrder} />}
      {view==='edit'&&selectedId&&<NewInvoiceForm editing={selectedId} onClose={()=>setView('detail')} onSuccess={()=>setView('detail')} />}
      {view==='detail'&&selectedId&&<InvoiceDetail id={selectedId} onClose={()=>setView('list')} isAdmin={isAdmin} onEdit={()=>setView('edit')} />}
    </div>
  )
}
