import { useState, Fragment } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import { formatDate } from '../../utils/date'
import { mediaUrl } from '../../utils/media'
import AmountInput, { parseAmount } from '../../components/ui/AmountInput'
import usePermissions from '../../hooks/usePermissions'
import AddContactModal from '../../components/accounting/AddContactModal'
import { PROVINCES } from '../../constants/provinces'

const TYPE_LABELS = {
  supplier_cn: 'تامین‌کننده چینی',
  clearance: 'ترخیص‌کار',
  shipping_co: 'شرکت حمل',
  staff: 'کارمند / فروشنده',
  customer: 'مشتری',
  partner: 'همکار',
  other: 'سایر',
}
const TYPE_COLORS = {
  supplier_cn: '#0066FF',
  clearance: '#FF9500',
  shipping_co: '#00C896',
  staff: '#8B5CF6',
  customer: '#4FC3F7',
  partner: '#FFD54F',
  other: '#888',
}

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// تبدیل ارقام فارسی/عربی به لاتین — برای جستجوی شماره موبایل با هر نوع صفحه‌کلید
const toEnDigits = (s) => String(s || '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))

// ─── تب تراز کلی ───────────────────────────────────────────────
function BalanceTab() {
  const [filter, setFilter] = useState('')
  const { data, isLoading } = useQuery({
    queryKey: ['balance-report'],
    queryFn: () => api.get('/accounting/reports/balance/').then(r => r.data),
  })
  const contacts = (data?.contacts || []).filter(c =>
    !filter || c.name.includes(filter) || c.contact_type_display.includes(filter)
  )
  const totalDebtIrr = contacts.filter(c => c.balance_irr > 0).reduce((s, c) => s + c.balance_irr, 0)
  const totalCreditIrr = contacts.filter(c => c.balance_irr < 0).reduce((s, c) => s + Math.abs(c.balance_irr), 0)
  const totalDebtCny = contacts.filter(c => c.balance_cny > 0).reduce((s, c) => s + c.balance_cny, 0)
  const totalCreditCny = contacts.filter(c => c.balance_cny < 0).reduce((s, c) => s + Math.abs(c.balance_cny), 0)

  return (
    <div>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'بدهکاران (ریال)', value: fmt(totalDebtIrr) + ' ت', color: '#FF3B3B' },
          { label: 'بستانکاران (ریال)', value: fmt(totalCreditIrr) + ' ت', color: '#00C896' },
          { label: 'بدهکاران (یوان)', value: fmt(totalDebtCny) + ' ¥', color: '#FF3B3B' },
          { label: 'بستانکاران (یوان)', value: fmt(totalCreditCny) + ' ¥', color: '#00C896' },
        ].map(item => (
          <div key={item.label} className="card p-4 text-center">
            <div className="text-xs text-gray-steel mb-1">{item.label}</div>
            <div className="text-lg font-bold" style={{ color: item.color }}>{item.value}</div>
          </div>
        ))}
      </div>
      <div className="mb-4">
        <input value={filter} onChange={e => setFilter(e.target.value)}
          className="input text-sm max-w-xs" placeholder="جستجو نام یا نوع..." />
      </div>
      <div className="card p-5">
        {isLoading ? <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
          : contacts.length === 0 ? <div className="text-center py-12 text-gray-steel">تراکنشی یافت نشد</div>
          : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['طرف حساب', 'نوع', 'مانده ریال', 'وضعیت', 'مانده یوان', 'وضعیت'].map((h, hi) => (
                  <th key={h + hi} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contacts.map((c, i) => (
                <tr key={c.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 600 }}>{c.name}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: TYPE_COLORS[c.contact_type] || '#888', background: (TYPE_COLORS[c.contact_type] || '#888') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>{c.contact_type_display}</span>
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896' }}>{fmt(Math.abs(c.balance_irr))} ریال</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896', background: (c.balance_irr > 0 ? '#FF3B3B' : '#00C896') + '20', padding: '2px 10px', borderRadius: 20, fontSize: 11 }}>
                      {c.balance_irr > 0 ? 'بدهکار' : 'بستانکار'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896' }}>
                    {c.has_fx === false ? '—' : (c.balance_cny !== 0 ? `${fmt(Math.abs(c.balance_cny))} ¥` : '—')}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {c.has_fx !== false && c.balance_cny !== 0 && (
                      <span style={{ color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896', background: (c.balance_cny > 0 ? '#FF3B3B' : '#00C896') + '20', padding: '2px 10px', borderRadius: 20, fontSize: 11 }}>
                        {c.balance_cny > 0 ? 'بدهکار' : 'بستانکار'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ─── نمای ریز اقلام کاردکس — همان جدول سندها + اقلام باز زیر هر فاکتور ──
// hasFx — فعال بودن ستون‌های یوانی برای طرف حساب انتخاب‌شده (عملیات ارزی)
function KardexItemsView({ timeline, hasFx = true }) {
  const tdS = { padding: '8px 10px' }
  return (
    <div className="overflow-x-auto">
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
            {['تاریخ', 'نوع سند', 'موعد تسویه', 'شرح', 'بدهکار ریال', 'بدهکار یوان', 'بستانکار ریال', 'بستانکار یوان', 'مانده ریال', 'مانده یوان'].map(h => (
              <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap', fontSize: 11 }}>{!hasFx && h.includes('یوان') ? '—' : h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {timeline.map((item, i) => (
            <Fragment key={i}>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(item.date)}</td>
                <td style={tdS}>
                  <span style={{ color: item.type === 'invoice' ? '#0066FF' : '#00C896', background: (item.type === 'invoice' ? '#0066FF' : '#00C896') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap' }}>
                    {item.type_label}
                  </span>
                  {item.doc && <div style={{ fontSize: 9, color: 'var(--color-text-muted)', marginTop: 2 }}>{item.doc}</div>}
                </td>
                <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>
                  {item.due_date ? formatDate(item.due_date) : '—'}
                </td>
                <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11 }}>{item.description}</td>
                <td style={{ ...tdS, color: '#FF3B3B', fontWeight: item.debit_irr ? 600 : 400 }}>
                  {item.debit_irr ? fmt(item.debit_irr) : '—'}
                </td>
                <td style={{ ...tdS, color: '#FF9500', fontWeight: item.debit_cny ? 600 : 400 }}>
                  {hasFx && item.debit_cny ? fmt(item.debit_cny) + ' ¥' : '—'}
                </td>
                <td style={{ ...tdS, color: '#00C896', fontWeight: item.credit_irr ? 600 : 400 }}>
                  {item.credit_irr ? fmt(item.credit_irr) : '—'}
                </td>
                <td style={{ ...tdS, color: '#00C896', fontWeight: item.credit_cny ? 600 : 400 }}>
                  {hasFx && item.credit_cny ? fmt(item.credit_cny) + ' ¥' : '—'}
                </td>
                <td style={{ ...tdS, fontWeight: 700, whiteSpace: 'nowrap', color: item.bal_irr > 0 ? '#FF3B3B' : item.bal_irr < 0 ? '#00C896' : '#888' }}>
                  {item.bal_irr !== 0 ? <>{fmt(Math.abs(item.bal_irr))} <span style={{ fontSize: 10 }}>{item.bal_irr > 0 ? 'بد' : 'بس'}</span></> : '✓'}
                </td>
                <td style={{ ...tdS, fontWeight: 700, whiteSpace: 'nowrap', color: item.bal_cny > 0 ? '#FF3B3B' : item.bal_cny < 0 ? '#00C896' : '#888' }}>
                  {hasFx && item.bal_cny !== 0 ? <>{fmt(Math.abs(item.bal_cny))} ¥ <span style={{ fontSize: 10 }}>{item.bal_cny > 0 ? 'بد' : 'بس'}</span></> : '—'}
                </td>
              </tr>
              {/* زیرشاخه اقلام فاکتور — همیشه باز */}
              {item.inv_items.map((it, j) => (
                <tr key={`${i}-${j}`} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.04)', background: 'rgba(251,192,45,0.03)' }}>
                  <td style={{ padding: '4px 10px', color: 'var(--color-text-muted)', fontSize: 10, whiteSpace: 'nowrap' }}>{formatDate(item.date)}</td>
                  <td style={{ padding: '4px 10px' }} />
                  <td style={{ padding: '4px 10px' }} />
                  <td style={{ padding: '4px 10px 4px 26px', color: 'var(--color-text-secondary)', fontSize: 11, textAlign: 'right' }}>
                    <span className="text-gray-steel ml-1">↳</span>
                    {it.product_name}
                    <span className="text-gray-steel text-[10px]" dir="ltr"> [{it.sku}]</span>
                    <span className="text-gray-steel text-[10px]"> × {fmt(it.quantity)}</span>
                  </td>
                  <td style={{ padding: '4px 10px' }} />
                  <td style={{ padding: '4px 10px' }} />
                  <td style={{ padding: '4px 10px', color: '#00C896', fontSize: 11 }}>
                    {item.purchase_type === 'domestic' ? `${fmt(it.unit_price_irr)} ریال` : ''}
                  </td>
                  <td style={{ padding: '4px 10px', color: '#00C896', fontSize: 11 }}>
                    {item.purchase_type !== 'domestic' ? `${fmt(it.unit_price_cny)} ¥` : ''}
                  </td>
                  <td colSpan={2} style={{ padding: '4px 10px' }} />
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── تب کاردکس اشخاص ───────────────────────────────────────────
function ContactKardexTab({ selectedId, setSelectedId, selectedName, setSelectedName, showEdit, setShowEdit }) {
  const { can } = usePermissions()
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [kardexView, setKardexView] = useState('docs')   // docs = سندها | items = ریز اقلام
  const [expandedInv, setExpandedInv] = useState(null)   // فاکتور بازشده برای نمایش ریز

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    // همه مشتریان (ثبت‌نامی سایت + طرف حساب‌های دستی) در کاردکس اشخاص دیده می‌شوند
    queryFn: () => api.get('/accounting/contacts/', { params: { include_registered: '1', registered_filter: 'all' } }).then(r => r.data),
  })

  const { data: detail, isLoading } = useQuery({
    queryKey: ['contact-kardex', selectedId],
    queryFn: () => api.get(`/accounting/contacts/${selectedId}/`).then(r => r.data),
    enabled: !!selectedId,
  })

  // نرخ یوان روز — برای «مانده کل» به ریال
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  const dayRate = Number(rateData?.rate_cny_to_irt || 0)

  const q = toEnDigits(search)
  const filtered = contacts.filter(c =>
    !q || c.name.includes(search) || c.contact_type_display.includes(search) || toEnDigits(c.phone).includes(q)
  ).slice(0, 15)

  // ساخت timeline — دیدگاه دفاتر ما (استاندارد کاردکس اشخاص):
  // ستون بدهکار = طرف حساب بدهکار ما شد (فروش به او / پرداخت ما به او)
  // ستون بستانکار = طرف حساب بستانکار ما شد (خرید از او / دریافت پول از او)
  // مانده = بدهکار − بستانکار → مثبت = طرف حساب به ما بدهکار است
  const buildTimeline = (detail) => {
    if (!detail) return []
    const items = []

    // فاکتورهای فروش (کاربران ثبت‌نامی) — مشتری جنس برده و بدهکار ما شده → ستون بدهکار
    for (const inv of (detail.sale_invoices || [])) {
      items.push({
        date: inv.date,
        type: 'invoice',
        type_label: inv.settlement_display ? `فاکتور فروش — ${inv.settlement_display}` : 'فاکتور فروش',
        due_date: inv.settlement_due || '',
        description: `فاکتور فروش ${inv.invoice_number || inv.id} | ${inv.status_display}`,
        doc: `فاکتور ${inv.invoice_number || inv.id}`,
        inv_id: inv.id,
        inv_number: inv.invoice_number,
        purchase_type: inv.currency === 'CNY' ? 'foreign' : 'domestic',
        inv_items: (inv.items || []).map(it => ({
          product_name: it.product_name, sku: it.sku, quantity: it.quantity,
          unit_price_irr: it.unit_price, unit_price_cny: it.unit_price,
        })),
        debit_irr: inv.currency === 'CNY' ? 0 : (inv.total_amount || 0),
        debit_cny: inv.currency === 'CNY' ? (inv.total_amount || 0) : 0,
        credit_irr: 0,
        credit_cny: 0,
        created_by_name: inv.created_by_name || '',
      })
    }

    // پرداخت‌های مشتری (تسویه فاکتور) — بدهی‌اش کم شد → ستون بستانکار
    for (const p of (detail.sale_payments || [])) {
      items.push({
        date: p.date,
        type: 'payment',
        type_label: `دریافت — ${p.method_display || ''}`,
        description: ['دریافت', p.account_name && `در ${p.account_name}`, p.reference].filter(Boolean).join(' | '),
        doc: `دریافت فروش #${p.id}`,
        inv_items: [],
        debit_irr: 0,
        debit_cny: 0,
        credit_irr: p.currency === 'CNY' ? 0 : Number(p.amount),
        credit_cny: p.currency === 'CNY' ? Number(p.amount) : 0,
        created_by_name: p.created_by_name || '',
      })
    }

    for (const inv of (detail.invoices || [])) {
      items.push({
        date: inv.date,
        type: 'invoice',
        type_label: inv.role === 'shipper' ? 'فاکتور حمل' : 'فاکتور خرید',
        description: inv.description,
        doc: inv.invoice_number ? `فاکتور ${inv.invoice_number}` : `سند #${inv.id}`,
        inv_id: inv.id,
        inv_number: inv.invoice_number,
        purchase_type: inv.purchase_type,
        inv_items: inv.items || [],
        // فاکتور = طرف حساب طلبکار → بستانکار
        debit_irr: 0,
        debit_cny: 0,
        credit_irr: inv.amount_irr || 0,
        credit_cny: inv.amount_cny || 0,
        created_by_name: inv.created_by_name || '',
      })
    }

    for (const p of (detail.payments || [])) {
      if (p.direction === 'out') {
        items.push({
          date: p.date,
          type: 'payment',
          type_label: p.payment_type_display || 'پرداخت',
          description: [p.payment_type_display, p.from_account_name && `از ${p.from_account_name}`, p.rate_irr > 0 && `نرخ ${Number(p.rate_irr).toLocaleString('fa-IR')}`, p.reference, p.note]
            .filter(Boolean).join(' | '),
          doc: `سند #${p.id}`,
          inv_items: [],
          // پرداخت = ما پول دادیم → بدهکار
          debit_irr: p.currency === 'IRR' ? Number(p.amount) : 0,
          debit_cny: p.currency === 'CNY' ? Number(p.amount) : 0,
          credit_irr: 0,
          credit_cny: 0,
          created_by_name: p.created_by_name || '',
        })
      } else {
        items.push({
          date: p.date,
          type: 'payment',
          type_label: `دریافت — ${p.payment_type_display || ''}`,
          description: ['دریافت', p.to_account_name && `در ${p.to_account_name}`, p.rate_irr > 0 && `نرخ ${Number(p.rate_irr).toLocaleString('fa-IR')}`, p.reference, p.note]
            .filter(Boolean).join(' | '),
          doc: `سند #${p.id}`,
          inv_items: [],
          // دریافت از طرف حساب = بدهی‌اش کم شد → بستانکار
          debit_irr: 0,
          debit_cny: 0,
          credit_irr: p.currency === 'IRR' ? Number(p.amount) : 0,
          credit_cny: p.currency === 'CNY' ? Number(p.amount) : 0,
          created_by_name: p.created_by_name || '',
        })
      }
    }

    items.sort((a, b) => new Date(a.date) - new Date(b.date))

    let balIrr = 0, balCny = 0
    return items.map(item => {
      // مانده = بدهکار − بستانکار — مثبت = طرف حساب به ما بدهکار است (هم‌جهت با balance_irr بک‌اند)
      balIrr += item.debit_irr - item.credit_irr
      balCny += item.debit_cny - item.credit_cny
      return { ...item, bal_irr: balIrr, bal_cny: balCny }
    }).reverse()
  }

  const timeline = buildTimeline(detail)
  // ستون‌های یوانی فقط برای طرف حساب‌های دارای «عملیات ارزی» نمایش داده می‌شوند
  const showFx = detail?.has_fx !== false

  return (
    <div>
      <div className="card p-5 mb-6">
        <div className="max-w-md">
          <label className="label text-xs mb-1 block">جستجو و انتخاب طرف حساب</label>
          <div className="relative">
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-steel pointer-events-none">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input value={search}
              onChange={e => { setSearch(e.target.value); setShowDropdown(true) }}
              onFocus={() => setShowDropdown(true)}
              onKeyDown={e => { if (e.key === 'Escape') setShowDropdown(false) }}
              placeholder="نام، نوع یا موبایل طرف حساب..."
              className="input text-sm"
              style={{ paddingRight: '2.4rem', paddingLeft: '2.4rem' }} />
            {(search || selectedId) && (
              <button type="button" title="پاک کردن"
                onClick={() => { setSearch(''); setSelectedId(null); setSelectedName(''); setShowDropdown(false) }}
                className="absolute left-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded-lg flex items-center justify-center text-gray-steel hover:text-white hover:bg-white/10 transition-colors">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          {showDropdown && (
            <div className="absolute z-50 top-full right-0 left-0 mt-1.5 bg-navy border border-white/10 rounded-xl shadow-2xl overflow-hidden">
              <div className="max-h-72 overflow-y-auto">
                {filtered.length === 0 ? (
                  <div className="px-4 py-6 text-center text-xs text-gray-steel">🔍 موردی با این مشخصات یافت نشد</div>
                ) : filtered.map(c => (
                  <button key={c.id}
                    className={`w-full text-right px-3 py-2.5 hover:bg-white/5 border-b border-white/5 last:border-0 flex items-center gap-3 transition-colors ${selectedId === c.id ? 'bg-brand/10' : ''}`}
                    onClick={() => { setSelectedId(c.id); setSelectedName(c.name); setSearch(c.name); setShowDropdown(false) }}>
                    <span className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0"
                      style={{ color: TYPE_COLORS[c.contact_type] || '#888', background: (TYPE_COLORS[c.contact_type] || '#888') + '20' }}>
                      {c.name?.[0] || '؟'}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="flex items-center gap-1.5">
                        <span className="text-sm text-white truncate">{c.title_display ? `${c.title_display} ${c.name}` : c.name}</span>
                        {c.is_registered && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-white/5 text-gray-steel flex-shrink-0">🌐 سایت</span>
                        )}
                        {selectedId === c.id && <span className="text-brand text-xs flex-shrink-0 font-bold">✓</span>}
                      </span>
                      <span className="flex gap-2 mt-1 flex-wrap items-center">
                        <span className="text-[10px] px-1.5 py-0.5 rounded-md"
                          style={{ color: TYPE_COLORS[c.contact_type] || '#888', background: (TYPE_COLORS[c.contact_type] || '#888') + '20' }}>
                          {c.contact_type_display}
                        </span>
                        {c.partner_tier_display && (
                          <span className="text-[10px] text-gold">{c.partner_tier_display}</span>
                        )}
                        {c.phone && <span className="text-[10px] text-gray-steel" dir="ltr">{c.phone}</span>}
                        {c.is_registered ? (
                          <>
                            {/* مانده کاربر ثبت‌نامی — همیشه نمایش داده می‌شود (حتی تسویه) تا با سطرهای دیگر یکدست باشد */}
                            <span className={`text-[10px] font-bold ${c.sale_debt > 0 ? 'text-red-400' : c.sale_debt < 0 ? 'text-green-400' : 'text-gray-steel'}`}>
                              {c.sale_debt > 0 ? 'بدهکار' : c.sale_debt < 0 ? 'بستانکار' : 'تسویه'}: {fmt(Math.abs(c.sale_debt || 0))} ریال
                            </span>
                            {c.has_fx !== false && c.sale_debt_cny !== 0 && (
                              <span className={`text-[10px] font-bold ${c.sale_debt_cny > 0 ? 'text-red-400' : 'text-green-400'}`}>
                                {c.sale_debt_cny > 0 ? 'بدهکار' : 'بستانکار'}: {fmt(Math.abs(c.sale_debt_cny))} ¥
                              </span>
                            )}
                          </>
                        ) : (
                          (() => {
                            // مانده کل = مانده حساب + مانده خالص فاکتورهای فروش (علامت‌دار —
                            // مازاد پرداخت فاکتورهای دیگر لحاظ می‌شود، مطابق مانده نهایی کاردکس)
                            const totalIrr = (c.balance_irr || 0) + (c.sale_debt || 0)
                            const totalCny = (c.balance_cny || 0) + (c.sale_debt_cny || 0)
                            return (
                              <>
                                <span className={`text-[10px] font-bold ${totalIrr > 0 ? 'text-red-400' : totalIrr < 0 ? 'text-green-400' : 'text-gray-steel'}`}>
                                  {totalIrr > 0 ? 'بدهکار' : totalIrr < 0 ? 'بستانکار' : 'تسویه'}: {fmt(Math.abs(totalIrr))} ریال
                                </span>
                                {c.has_fx !== false && totalCny !== 0 && (
                                  <span className={`text-[10px] font-bold ${totalCny > 0 ? 'text-red-400' : 'text-green-400'}`}>
                                    {totalCny > 0 ? 'بدهکار' : 'بستانکار'}: {fmt(Math.abs(totalCny))} ¥
                                  </span>
                                )}
                              </>
                            )
                          })()
                        )}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {showDropdown && <div className="fixed inset-0 z-40" onClick={() => setShowDropdown(false)} />}
          </div>

          {detail && (
            <div className="mt-2 flex gap-4 flex-wrap">
              {detail.is_registered ? (
                <>
                  <span className={`text-sm font-bold ${detail.sale_debt > 0 ? 'text-red-400' : 'text-green-400'}`}>
                    بدهی فاکتور: {detail.sale_debt > 0 ? `${fmt(detail.sale_debt)} ریال` : 'تسویه ✓'}
                  </span>
                  {detail.has_fx !== false && detail.sale_debt_cny > 0 && (
                    <span className="text-sm font-bold text-red-400">
                      بدهی فاکتور یوانی: {fmt(detail.sale_debt_cny)} ¥
                    </span>
                  )}
                </>
              ) : (
                <>
                  <span className={`text-sm font-bold ${detail.balance_irr > 0 ? 'text-red-400' : detail.balance_irr < 0 ? 'text-green-400' : 'text-gray-steel'}`}>
                    مانده ریال: {detail.balance_irr === 0 ? 'تسویه ✓' : `${detail.balance_irr > 0 ? 'بدهکار' : 'بستانکار'} ${fmt(Math.abs(detail.balance_irr))} ریال`}
                  </span>
                  {detail.has_fx !== false && (
                    <span className={`text-sm font-bold ${detail.balance_cny > 0 ? 'text-red-400' : detail.balance_cny < 0 ? 'text-green-400' : 'text-gray-steel'}`}>
                      مانده یوان: {detail.balance_cny === 0 ? 'تسویه ✓' : `${detail.balance_cny > 0 ? 'بدهکار' : 'بستانکار'} ${fmt(Math.abs(detail.balance_cny))} ¥`}
                    </span>
                  )}
                  {/* مانده کل به ریال با نرخ روز یوان */}
                  {detail.has_fx !== false && (() => {
                    const total = Number(detail.balance_irr || 0) + Number(detail.balance_cny || 0) * dayRate
                    return (
                      <span className={`text-sm font-bold ${total > 0 ? 'text-red-400' : total < 0 ? 'text-green-400' : 'text-gray-steel'}`}>
                        | مانده کل (با نرخ روز): {total === 0 ? 'تسویه ✓' : `${total > 0 ? 'بدهکار' : 'بستانکار'} ${fmt(Math.abs(total))} ریال`}
                      </span>
                    )
                  })()}
                </>
              )}
            </div>
          )}

          {/* مانده اول دوره — دستی با پرمیشن contacts_edit */}
          {detail && !detail.is_registered && can('contacts_edit') && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/10 flex-wrap gap-2">
              <div className="text-xs text-gray-steel">
                مانده اول دوره:
                <span className="text-white mr-1">{fmt(detail.opening_balance_irr)} ریال</span>
                {detail.has_fx !== false && Number(detail.opening_balance_cny) !== 0 && (
                  <span className="text-white mr-2">| {fmt(detail.opening_balance_cny)} یوان</span>
                )}
              </div>
            </div>
          )}

        </div>
      </div>

      {selectedId && (
        isLoading ? <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div> : (
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <h3 className="text-sm font-semibold text-white">کاردکس {selectedName}</h3>
              {/* سوییچ دو حالت نمایش */}
              <div className="flex gap-1 bg-white/5 rounded-lg p-1">
                {[['docs', '📑 سندها'], ['items', '🧾 ریز اقلام']].map(([k, label]) => (
                  <button key={k} onClick={() => setKardexView(k)}
                    className={`text-xs px-3 py-1.5 rounded-md transition-all ${kardexView === k ? 'bg-brand/20 text-brand' : 'text-gray-steel hover:text-white'}`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {timeline.length === 0 ? (
              <div className="text-center py-8 text-gray-steel text-sm">هیچ تراکنشی ثبت نشده</div>
            ) : kardexView === 'items' ? (
              /* ── حالت ریز اقلام — همان جدول سندها با اقلام باز زیر هر فاکتور ── */
              <KardexItemsView timeline={timeline} hasFx={showFx} />
            ) : (
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['تاریخ', 'نوع سند', 'موعد تسویه', 'شرح', 'ثبت‌کننده', 'بدهکار ریال', 'بدهکار یوان', 'بستانکار ریال', 'بستانکار یوان', 'مانده ریال', 'مانده یوان'].map(h => (
                        <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap', fontSize: 11 }}>{!showFx && h.includes('یوان') ? '—' : h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {timeline.map((item, i) => (
                      <Fragment key={i}>
                        <tr
                          onClick={item.type === 'invoice' && item.inv_items.length > 0
                            ? () => setExpandedInv(expandedInv === i ? null : i) : undefined}
                          style={{
                            borderBottom: expandedInv === i ? 'none' : '0.5px solid rgba(255,255,255,0.05)',
                            background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent',
                            cursor: item.type === 'invoice' && item.inv_items.length > 0 ? 'pointer' : 'default',
                          }}>
                          <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(item.date)}</td>
                          <td style={{ padding: '8px 10px' }}>
                            <span style={{ color: item.type === 'invoice' ? '#0066FF' : '#00C896', background: (item.type === 'invoice' ? '#0066FF' : '#00C896') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap' }}>
                              {item.type_label}
                            </span>
                            {item.doc && <div style={{ fontSize: 9, color: 'var(--color-text-muted)', marginTop: 2 }}>{item.doc}</div>}
                          </td>
                          <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>
                            {item.due_date ? formatDate(item.due_date) : '—'}
                          </td>
                          <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)', fontSize: 11 }}>
                            {item.type === 'invoice' && item.inv_items.length > 0 && (
                              <span className="text-brand ml-1">{expandedInv === i ? '▼' : '◀'}</span>
                            )}
                            {item.description}
                          </td>
                          <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>
                            {item.created_by_name || '—'}
                          </td>
                          <td style={{ padding: '8px 10px', color: '#FF3B3B', fontWeight: item.debit_irr ? 600 : 400 }}>
                            {item.debit_irr ? fmt(item.debit_irr) : '—'}
                          </td>
                          <td style={{ padding: '8px 10px', color: '#FF9500', fontWeight: item.debit_cny ? 600 : 400 }}>
                            {showFx && item.debit_cny ? fmt(item.debit_cny) + ' ¥' : '—'}
                          </td>
                          <td style={{ padding: '8px 10px', color: '#00C896', fontWeight: item.credit_irr ? 600 : 400 }}>
                            {item.credit_irr ? fmt(item.credit_irr) : '—'}
                          </td>
                          <td style={{ padding: '8px 10px', color: '#00C896', fontWeight: item.credit_cny ? 600 : 400 }}>
                            {showFx && item.credit_cny ? fmt(item.credit_cny) + ' ¥' : '—'}
                          </td>
                          <td style={{ padding: '8px 10px', fontWeight: 700, whiteSpace: 'nowrap', color: item.bal_irr > 0 ? '#FF3B3B' : item.bal_irr < 0 ? '#00C896' : '#888' }}>
                            {item.bal_irr !== 0 ? <>{fmt(Math.abs(item.bal_irr))} <span style={{ fontSize: 10 }}>{item.bal_irr > 0 ? 'بد' : 'بس'}</span></> : '✓'}
                          </td>
                          <td style={{ padding: '8px 10px', fontWeight: 700, whiteSpace: 'nowrap', color: item.bal_cny > 0 ? '#FF3B3B' : item.bal_cny < 0 ? '#00C896' : '#888' }}>
                            {showFx && item.bal_cny !== 0 ? <>{fmt(Math.abs(item.bal_cny))} ¥ <span style={{ fontSize: 10 }}>{item.bal_cny > 0 ? 'بد' : 'بس'}</span></> : '—'}
                          </td>
                        </tr>
                        {/* ریز اقلام فاکتور — با کلیک روی سند */}
                        {expandedInv === i && (
                          <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: 'rgba(251,192,45,0.04)' }}>
                            <td colSpan={11} style={{ padding: '6px 24px 12px' }}>
                              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                                <thead>
                                  <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.08)' }}>
                                    {['کالا', 'تعداد', 'قیمت واحد', 'جمع'].map(h => (
                                      <th key={h} style={{ padding: '4px 8px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 10 }}>{h}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {item.inv_items.map((it, j) => (
                                    <tr key={j}>
                                      <td style={{ padding: '5px 8px', textAlign: 'right' }}>
                                        {it.product_name}
                                        <span className="text-gray-steel text-[10px]" dir="ltr"> [{it.sku}]</span>
                                      </td>
                                      <td style={{ padding: '5px 8px' }}>{fmt(it.quantity)}</td>
                                      <td style={{ padding: '5px 8px' }}>
                                        {item.purchase_type === 'domestic' ? `${fmt(it.unit_price_irr)} ریال` : `${fmt(it.unit_price_cny)} ¥`}
                                      </td>
                                      <td style={{ padding: '5px 8px', fontWeight: 600 }}>
                                        {item.purchase_type === 'domestic'
                                          ? `${fmt((it.unit_price_irr || 0) * it.quantity)} ریال`
                                          : `${fmt(it.unit_price_cny * it.quantity)} ¥`}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )
      )}

      {!selectedId && (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">👤</div>
          <div className="text-gray-steel text-sm">نام طرف حساب را جستجو کنید</div>
        </div>
      )}

      {showEdit && detail && (
        <EditContactModal detail={detail} onClose={() => setShowEdit(false)}
          onDeleted={() => { setSelectedId(null); setSelectedName(''); setSearch('') }} />
      )}
    </div>
  )
}

// ─── استان‌های ایران — از constants/provinces ایمپورت می‌شود ────

const CONTACT_TYPE_OPTIONS = [
  ['supplier_cn', 'تامین‌کننده چینی'],
  ['clearance', 'ترخیص‌کار'],
  ['shipping_co', 'شرکت حمل'],
  ['staff', 'کارمند / فروشنده'],
  ['customer', 'مشتری'],
  ['partner', 'همکار'],
  ['other', 'سایر'],
]

// ─── مودال ویرایش کامل اطلاعات طرف حساب (همه انواع) ────────────
function EditContactModal({ detail, onClose, onDeleted }) {
  const qc = useQueryClient()
  const isReg = !!detail.is_registered
  // فرم یکپارچه — اتحاد فیلدهای هر دو نوع طرف حساب؛ سقف اعتبار با کلید خنثی credit_limit
  // (هنگام ذخیره برای طرف حساب دستی به credit_limit_irr تبدیل می‌شود)
  const [form, setForm] = useState({
    title: detail.title || 'mr',
    first_name: detail.first_name || '',
    last_name: detail.last_name || '',
    name: detail.name || '',
    contact_type: detail.contact_type || 'other',
    currency: detail.currency || 'CNY',
    phone: detail.phone || '',
    email: detail.email || '',
    company_name: detail.company_name || '',
    wechat: detail.wechat || '',
    province: detail.province || '',
    address: detail.address || '',
    note: detail.note || '',
    partner_tier: detail.partner_tier || '',
    opening_balance_irr: detail.opening_balance_irr ?? '',
    opening_balance_cny: detail.opening_balance_cny ?? '',
    legacy_purchase_total: detail.legacy_purchase_total ?? '',
    credit_limit: detail.credit_limit_irr ?? detail.credit_limit ?? '',
    restriction_override: !!detail.restriction_override,
    partner_approved: !!detail.partner_approved,
    has_fx: !!detail.has_fx,
  })
  const [msg, setMsg] = useState(null)
  const [docFile, setDocFile] = useState(null)
  const [docMsg, setDocMsg] = useState(null)
  // آپلود مدرک همکاری (تصویر) روی پروفایل کاربر لینک‌شده — multipart PATCH
  const uploadDocMut = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('document', docFile)
      return api.patch(`/accounting/contacts/${detail.id}/`, fd).then(r => r.data)
    },
    onSuccess: () => {
      setDocFile(null)
      setDocMsg({ type: 'success', text: 'مدرک همکاری ذخیره شد' })
      qc.invalidateQueries(['contact-kardex', detail.id])
      setTimeout(() => setDocMsg(null), 2500)
    },
    onError: (e) => setDocMsg({ type: 'error', text: e.response?.data?.error || 'خطا در آپلود مدرک' }),
  })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [pwMsg, setPwMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  // فعال‌سازی/تعیین رمز حساب کاربری سایت برای طرف حساب حضوری
  const activateMut = useMutation({
    mutationFn: () => api.post(`/accounting/contacts/${detail.id}/activate-user/`, { password: newPassword }).then(r => r.data),
    onSuccess: (r) => {
      setPwMsg({ type: 'success', text: r.message || 'حساب فعال شد' })
      setNewPassword('')
      qc.invalidateQueries(['contact-kardex', detail.id])
    },
    onError: (e) => setPwMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/accounting/contacts/${detail.id}/`).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['contacts-all'])
      onDeleted?.()
      onClose()
      if (r.deactivated) alert('طرف حساب سند داشت و به‌جای حذف، غیرفعال شد')
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در حذف' }),
  })

  const saveMut = useMutation({
    mutationFn: () => {
      const base = {
        title: form.title,
        phone: form.phone,
        province: form.province,
        address: form.address,
        opening_balance_irr: Number(form.opening_balance_irr) || 0,
        opening_balance_cny: Number(form.opening_balance_cny) || 0,
        legacy_purchase_total: Number(form.legacy_purchase_total) || 0,
        partner_tier: form.partner_tier,
        restriction_override: !!form.restriction_override,
        has_fx: !!form.has_fx,
      }
      // هر شاخه بک‌اند کلید سقف اعتبار مخصوص خودش را می‌گیرد — نه هر دو را
      const payload = isReg ? {
        ...base,
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        company_name: form.company_name,
        credit_limit: Number(form.credit_limit) || 0,
        partner_approved: !!form.partner_approved,
      } : {
        ...base,
        name: form.name,
        contact_type: form.contact_type,
        currency: form.currency,
        wechat: form.wechat,
        note: form.note,
        credit_limit_irr: Number(form.credit_limit) || 0,
      }
      return api.patch(`/accounting/contacts/${detail.id}/`, payload).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['contacts-all'])
      qc.invalidateQueries(['contact-kardex', detail.id])
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ذخیره' }),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h2 className="font-bold text-white text-base mb-4">ویرایش اطلاعات {detail.name}</h2>
        {/* مدارک/مشخصات همکاری کاربر لینک‌شده — حتی اگر از لیست ۵۰تایی «تازه تأیید شده» بیرون رفته باشد */}
        {detail.linked_partner && (
          <div className="rounded-xl border border-brand/20 bg-brand/5 p-3 mb-4 space-y-1.5">
            <div className="text-[11px] font-bold text-gray-steel mb-1">🤝 اطلاعات همکاری (حساب کاربری سایت)</div>
            <div className="flex items-center gap-2 flex-wrap">
              {signupBadgeOf({ signup_source: detail.linked_partner.signup_source }) && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${signupBadgeOf({ signup_source: detail.linked_partner.signup_source }).cls}`}>
                  {signupBadgeOf({ signup_source: detail.linked_partner.signup_source }).label}
                </span>
              )}
              {detail.linked_partner.partner_tier && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">
                  {(TIER_BADGE[detail.linked_partner.partner_tier] || {}).label || detail.linked_partner.partner_tier}
                </span>
              )}
              {detail.linked_partner.user_type === 'partner' ? (
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${detail.linked_partner.is_approved ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                  {detail.linked_partner.is_approved ? '✅ همکار تأییدشده' : '⏳ در انتظار تأیید'}
                </span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400">
                  مشتری عمومی
                </span>
              )}
            </div>
            <div className="flex gap-3 flex-wrap items-center">
              {detail.linked_partner.document_url && (
                <a href={mediaUrl(detail.linked_partner.document_url)} target="_blank" rel="noreferrer"
                  className="text-[11px] text-brand dark:text-cyan hover:underline">
                  🖼 مشاهده مدرک (کارت ویزیت / ادمین پیج)
                </a>
              )}
              {detail.linked_partner.social_url && (
                <a href={/^https?:\/\//i.test(detail.linked_partner.social_url) ? detail.linked_partner.social_url : `https://${detail.linked_partner.social_url}`}
                  target="_blank" rel="noreferrer"
                  className="text-[11px] text-brand dark:text-cyan hover:underline" dir="ltr">
                  🔗 {detail.linked_partner.social_url}
                </a>
              )}
              {!detail.linked_partner.document_url && !detail.linked_partner.social_url && (
                <span className="text-[11px] text-gray-steel">مدرک یا لینک شبکه اجتماعی ثبت نشده است</span>
              )}
            </div>
            {/* بارگذاری مدرک توسط ادمین — همکاران بعد از تأیید معمولاً چیزی اضافه نمی‌کنند */}
            <div className="flex items-center gap-2 pt-1">
              <input type="file" accept="image/*" className="hidden" id="admin-partner-doc"
                onChange={e => setDocFile(e.target.files?.[0] || null)} />
              <label htmlFor="admin-partner-doc"
                className="text-[11px] text-gray-steel cursor-pointer border border-dashed border-white/15 rounded-lg px-3 py-1.5 hover:border-brand/40 transition-all truncate max-w-[220px]">
                {docFile ? `📷 ${docFile.name}` : '⬆ بارگذاری مدرک همکاری'}
              </label>
              {docFile && (
                <button type="button" onClick={() => uploadDocMut.mutate()} disabled={uploadDocMut.isPending}
                  className="text-[11px] px-3 py-1.5 rounded-lg bg-brand text-white hover:bg-brand-light disabled:opacity-50">
                  {uploadDocMut.isPending ? '...' : '✓ آپلود'}
                </button>
              )}
            </div>
            {docMsg && (
              <div className={`text-[11px] rounded-lg px-3 py-1.5 ${docMsg.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                {docMsg.text}
              </div>
            )}
          </div>
        )}
        {msg && (
          <div className="rounded-lg px-4 py-2 text-xs mb-3 bg-red-500/20 text-red-400">{msg.text}</div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-gray-steel col-span-2">عنوان
            <select value={form.title} onChange={e => set('title', e.target.value)} className="input text-sm mt-1">
              <option value="">— بدون عنوان —</option>
              <option value="mr">آقای</option>
              <option value="mrs">خانم</option>
              <option value="company">شرکت</option>
              <option value="shop">فروشگاه</option>
            </select>
          </label>
          {isReg ? (
            <>
              <label className="text-xs text-gray-steel">نام
                <input value={form.first_name} onChange={e => set('first_name', e.target.value)} className="input text-sm mt-1" />
              </label>
              <label className="text-xs text-gray-steel">نام خانوادگی
                <input value={form.last_name} onChange={e => set('last_name', e.target.value)} className="input text-sm mt-1" />
              </label>
            </>
          ) : (
            <label className="text-xs text-gray-steel col-span-2">نام طرف حساب
              <input value={form.name} onChange={e => set('name', e.target.value)} className="input text-sm mt-1" />
            </label>
          )}
          <label className="text-xs text-gray-steel">موبایل
            <input value={form.phone} onChange={e => set('phone', e.target.value)} dir="ltr" className="input text-sm mt-1" />
          </label>
          {isReg ? (
            <label className="text-xs text-gray-steel">ایمیل
              <input value={form.email} onChange={e => set('email', e.target.value)} dir="ltr" className="input text-sm mt-1" />
            </label>
          ) : (
            <label className="text-xs text-gray-steel">وی‌چت / واتساپ / تلفن
              <input value={form.wechat} onChange={e => set('wechat', e.target.value)} dir="ltr" className="input text-sm mt-1" />
            </label>
          )}
          {isReg && (
            <label className="text-xs text-gray-steel col-span-2">نام شرکت / برند
              <input value={form.company_name} onChange={e => set('company_name', e.target.value)} className="input text-sm mt-1" />
            </label>
          )}
          {!isReg && (
            <>
              <label className="text-xs text-gray-steel">نوع
                <select value={form.contact_type} onChange={e => set('contact_type', e.target.value)} className="input text-sm mt-1">
                  {CONTACT_TYPE_OPTIONS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                </select>
              </label>
              <label className="text-xs text-gray-steel">ارز پیش‌فرض
                <select value={form.currency} onChange={e => set('currency', e.target.value)} className="input text-sm mt-1">
                  {form.has_fx && <option value="CNY">یوان چین</option>}
                  <option value="IRR">ریال ایران</option>
                  <option value="USD">دلار</option>
                </select>
              </label>
            </>
          )}
          {/* عملیات ارزی — فعال بودن فیلدها و ستون‌های یوانی برای این طرف حساب (هر دو نوع) */}
          <label className="flex items-start gap-2 text-xs text-gray-steel cursor-pointer col-span-2">
            <input type="checkbox" checked={!!form.has_fx}
              onChange={e => { set('has_fx', e.target.checked); if (!e.target.checked && form.currency === 'CNY') set('currency', 'IRR') }}
              className="accent-[#FBC02D] mt-0.5" />
            <span>💱 عملیات ارزی<span className="block text-[10px] text-gray-steel mt-0.5">این شخص کارکرد یوانی دارد — ستون‌ها و فیلدهای ارزی برایش نمایش داده می‌شود</span></span>
          </label>
          <label className="text-xs text-gray-steel">استان
            <input value={form.province} onChange={e => set('province', e.target.value)}
              list="province-options" className="input text-sm mt-1" placeholder="جستجو یا انتخاب استان..." />
            <datalist id="province-options">
              {PROVINCES.map(p => <option key={p} value={p} />)}
            </datalist>
          </label>
          <label className="text-xs text-gray-steel col-span-2">آدرس
            <textarea value={form.address} onChange={e => set('address', e.target.value)} rows={2} className="input text-sm mt-1" />
          </label>
          {!isReg && (
            <label className="text-xs text-gray-steel col-span-2">توضیحات
              <textarea value={form.note} onChange={e => set('note', e.target.value)} rows={2} className="input text-sm mt-1" />
            </label>
          )}
          <label className="text-xs text-gray-steel">مانده اول دوره (ریال)
            <AmountInput value={form.opening_balance_irr}
              onChange={e => set('opening_balance_irr', e.target.value)}
              className="input text-sm mt-1" placeholder="0" />
          </label>
          {/* مانده اول دوره (یوان) — فقط برای طرف حساب‌های دارای «عملیات ارزی» یا کاربران ثبت‌نامی */}
          {(isReg || form.has_fx) && (
            <label className="text-xs text-gray-steel">مانده اول دوره (یوان)
              <AmountInput value={form.opening_balance_cny}
                onChange={e => set('opening_balance_cny', e.target.value)}
                className="input text-sm mt-1" placeholder="0" />
            </label>
          )}
          <div className="col-span-2 text-[10px] text-gray-steel">مثبت = طرف حساب به ما بدهکار | منفی = ما به او بدهکاریم</div>
          {/* سقف اعتبار — شامل هر نوع بدهی: حساب باز، چک وصول‌نشده، ردیف‌های تسویه باز */}
          <label className="text-xs text-gray-steel col-span-2">سقف اعتبار (ریال) — ۰ یعنی نامحدود
            <AmountInput value={form.credit_limit}
              onChange={e => set('credit_limit', e.target.value)}
              className="input text-sm mt-1" placeholder="0" />
          </label>
          {(() => {
            const limit = Number(parseAmount(form.credit_limit)) || 0
            const debt = Number(detail.sale_debt) || 0
            if (!limit) return (
              <div className="col-span-2 text-[10px] text-gray-steel -mt-2">
                شامل انواع بدهی می‌شود: حساب باز، چک وصول‌نشده و هر بدهی تسویه‌نشده — اگر مجموع بدهی از سقف بگذرد، فروش اعتباری جدید بسته می‌شود
              </div>
            )
            const remaining = limit - debt
            return (
              <div className="col-span-2 text-[10px] -mt-2">
                <span className="text-gray-steel">بدهی فعلی: {debt.toLocaleString('fa-IR')} ریال</span>
                {' — '}
                <span className={remaining >= 0 ? 'text-green-400' : 'text-red-400'}>
                  مانده اعتبار: {remaining.toLocaleString('fa-IR')} ریال
                </span>
              </div>
            )
          })()}
          <label className="text-xs text-gray-steel col-span-2">مجموع سابقه خرید قبلی خارج از سایت (ریال)
            <AmountInput value={form.legacy_purchase_total}
              onChange={e => set('legacy_purchase_total', e.target.value)}
              className="input text-sm mt-1" placeholder="0" />
          </label>
          <div className="col-span-2 text-[10px] text-gray-steel -mt-2">
            این مبلغ با خریدهای آنلاین سایت جمع می‌شود و ملاک ارتقای خودکار سطح همکار (باشگاه همکاران) است
          </div>
        </div>
        {(isReg || form.contact_type === 'partner') && (
          <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
            {isReg && (
              <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
                <input type="checkbox" checked={form.partner_approved}
                  onChange={e => set('partner_approved', e.target.checked)} className="accent-[#FBC02D]" />
                همکار تأییدشده
              </label>
            )}
            {(isReg ? form.partner_approved : form.contact_type === 'partner') && (
              <select value={form.partner_tier} onChange={e => set('partner_tier', e.target.value)} className="input text-xs">
                {TIER_OPTIONS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
            )}
          </div>
        )}
        {/* وضعیت محدودیت معوقات + باز کردن دستی — برای همه طرف حساب‌ها */}
        <div className="mt-4 pt-4 border-t border-white/10 space-y-2">
          {detail.restriction_level && detail.restriction_level !== 'warning' && !form.restriction_override && (
            <div className={`rounded-lg px-3 py-2 text-[11px] leading-5 ${
              detail.restriction_level === 'blocked' ? 'bg-red-500/15 text-red-400' : 'bg-yellow-500/10 text-yellow-400'
            }`}>
              {detail.restriction_level === 'blocked'
                ? '⛔ این حساب به دلیل معوقات تسویه‌نشده مسدود است و نمی‌تواند سفارش ثبت کند.'
                : '⚠️ این حساب در مرحله «فقط نقدی» است — خرید اعتباری برایش بسته شده.'}
            </div>
          )}
          {Number(detail.payment_credit_irr) > 0 && (
            <div className="text-[11px] text-green-400">
              💰 بستانکاری نقدی: {Number(detail.payment_credit_irr).toLocaleString('fa-IR')} ریال (به بدهی‌های بعدی تخصیص می‌یابد)
            </div>
          )}
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={form.restriction_override}
              onChange={e => set('restriction_override', e.target.checked)} className="accent-[#FBC02D]" />
            باز کردن دستی محدودیت حساب (معوقات نادیده گرفته شود)
          </label>
        </div>
        {/* تضامین و اعتبارسنجی (فروش اعتباری) — برای همه طرف حساب‌ها */}
        <GuaranteeSection baseUrl={isReg
          ? `/users/admin/partners/${detail.user_id}/guarantees/`
          : `/users/admin/contacts/${String(detail.id).replace(/^c_/, '')}/guarantees/`} />
        {/* حساب کاربری سایت — فقط طرف حساب‌های حضوری؛ مشتری با موبایل + این رمز لاگین می‌کند */}
        {!isReg && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="text-xs font-bold text-white mb-1">🌐 حساب کاربری سایت</div>
            <div className="text-[11px] text-gray-steel mb-2">
              {detail.linked_user_phone
                ? <>موبایل حساب: <b className="text-white" dir="ltr">{detail.linked_user_phone}</b> — وضعیت: {detail.linked_user_active
                    ? <span className="text-green-400">فعال</span>
                    : <span className="text-yellow-400">بدون رمز (غیرفعال)</span>}</>
                : 'هنوز حسابی لینک نشده — با تعیین رمز، حساب با موبایل همین طرف حساب ساخته/لینک می‌شود.'}
            </div>
            <div className="flex gap-2">
              <input type="text" value={newPassword} onChange={e => setNewPassword(e.target.value)}
                dir="ltr" placeholder="رمز عبور جدید (حداقل ۸ کاراکتر)"
                className="input text-sm flex-1" autoComplete="off" />
              <button type="button" disabled={newPassword.length < 8 || activateMut.isPending}
                onClick={() => activateMut.mutate()}
                className="btn-primary text-xs px-4 disabled:opacity-50">
                {activateMut.isPending ? '...' : detail.linked_user_active ? 'تغییر رمز' : 'فعال‌سازی'}
              </button>
            </div>
            {pwMsg && (
              <div className={`text-[11px] mt-2 rounded-lg px-3 py-2 ${pwMsg.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                {pwMsg.text}
              </div>
            )}
          </div>
        )}
        <div className="flex gap-2 mt-5">
          {confirmDelete ? (
            <>
              <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                className="flex-1 text-sm py-2.5 rounded-xl bg-red-500/20 text-red-400 border border-red-500/40 disabled:opacity-50">
                {deleteMut.isPending ? '...' : 'بله، حذف شود'}
              </button>
              <button onClick={() => setConfirmDelete(false)} className="btn-secondary text-sm py-2.5 px-5">خیر</button>
            </>
          ) : (
            <button onClick={() => setConfirmDelete(true)}
              className="text-xs px-3 py-2.5 rounded-xl text-red-400 border border-red-500/30 hover:bg-red-500/10">
              🗑 حذف
            </button>
          )}
          <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? '...' : 'ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary text-sm py-2.5 px-5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── بخش تضامین و اعتبارسنجی (فروش اعتباری) ────────────────────
const GUARANTEE_TYPES = [
  ['check', 'چک'],
  ['promissory', 'سفته'],
  ['id_card', 'کارت ملی'],
  ['property_deed', 'سند ملکی'],
  ['introduction', 'معرفی‌نامه کسبه'],
  ['other', 'سایر'],
]

function GuaranteeSection({ baseUrl }) {
  const qc = useQueryClient()
  const [gForm, setGForm] = useState({ guarantee_type: 'check', amount_rials: '', description: '' })
  const [gFile, setGFile] = useState(null)
  const [gMsg, setGMsg] = useState(null)

  const { data: guarantees = [], isLoading } = useQuery({
    queryKey: ['guarantees', baseUrl],
    queryFn: () => api.get(baseUrl).then(r => r.data),
  })

  const addMut = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('guarantee_type', gForm.guarantee_type)
      fd.append('amount_rials', String(parseAmount(gForm.amount_rials) || 0))
      fd.append('description', gForm.description)
      if (gFile) fd.append('document', gFile)
      return api.post(baseUrl, fd).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['guarantees', baseUrl])
      setGForm({ guarantee_type: 'check', amount_rials: '', description: '' })
      setGFile(null)
      setGMsg({ type: 'success', text: 'تضمین ثبت شد' })
      setTimeout(() => setGMsg(null), 1500)
    },
    onError: (e) => setGMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت تضمین' }),
  })

  const delMut = useMutation({
    mutationFn: (gid) => api.delete(`${baseUrl}${gid}/`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(['guarantees', baseUrl]),
    onError: () => setGMsg({ type: 'error', text: 'خطا در حذف' }),
  })

  const total = guarantees.reduce((s, g) => s + (Number(g.amount_rials) || 0), 0)

  return (
    <div className="mt-4 pt-4 border-t border-white/10">
      <div className="text-xs font-bold text-white mb-2">🛡 تضامین و اعتبارسنجی (فروش اعتباری)</div>

      {isLoading ? (
        <div className="text-[11px] text-gray-steel">در حال بارگذاری...</div>
      ) : guarantees.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {guarantees.map(g => (
            <div key={g.id} className="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-2 text-[11px]">
              <span className="text-white font-semibold">{g.guarantee_type_display}</span>
              {Number(g.amount_rials) > 0 && (
                <span className="text-gray-steel">{Number(g.amount_rials).toLocaleString('fa-IR')} ریال</span>
              )}
              {g.document_url && (
                <a href={mediaUrl(g.document_url)} target="_blank" rel="noreferrer"
                  className="text-brand dark:text-cyan hover:underline">🖼 مدرک</a>
              )}
              <span className="text-gray-steel mr-auto">{formatDate(g.created_at)}</span>
              <button type="button" onClick={() => delMut.mutate(g.id)} disabled={delMut.isPending}
                className="text-red-400 hover:bg-red-500/10 rounded px-1">✕</button>
            </div>
          ))}
          {total > 0 && (
            <div className="text-[11px] text-gray-steel px-1">
              مجموع تضامین نقدی: <span className="text-white">{total.toLocaleString('fa-IR')} ریال</span>
            </div>
          )}
        </div>
      )}

      {/* فرم ثبت تضمین جدید */}
      <div className="grid grid-cols-2 gap-2">
        <select value={gForm.guarantee_type}
          onChange={e => setGForm(f => ({ ...f, guarantee_type: e.target.value }))}
          className="input text-xs">
          {GUARANTEE_TYPES.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
        <AmountInput value={gForm.amount_rials}
          onChange={e => setGForm(f => ({ ...f, amount_rials: e.target.value }))}
          className="input text-xs" placeholder="مبلغ (ریال) — اختیاری" />
        <input value={gForm.description}
          onChange={e => setGForm(f => ({ ...f, description: e.target.value }))}
          className="input text-xs col-span-2" placeholder="توضیحات (شماره چک، تاریخ، بانک...)" />
        <div className="col-span-2 flex items-center gap-2">
          <label className="flex-1 border border-dashed border-white/15 hover:border-brand/40 rounded-lg px-3 py-2 text-[11px] text-gray-steel cursor-pointer text-center transition-all">
            <input type="file" accept="image/*" className="hidden"
              onChange={e => setGFile(e.target.files?.[0] || null)} />
            {gFile ? `📎 ${gFile.name}` : '📷 تصویر مدرک (اختیاری)'}
          </label>
          <button type="button" onClick={() => addMut.mutate()} disabled={addMut.isPending}
            className="btn-primary text-xs px-4 py-2 disabled:opacity-50">
            {addMut.isPending ? '...' : '+ ثبت تضمین'}
          </button>
        </div>
      </div>
      {gMsg && (
        <div className={`text-[11px] mt-2 rounded-lg px-3 py-2 ${gMsg.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          {gMsg.text}
        </div>
      )}
    </div>
  )
}

// ─── تب درخواست‌های همکاری (رسیدگی و تأیید) ─────────────────────
const TIER_OPTIONS = [
  ['',        'مشتری عمومی — قیمت عمومی'],
  ['silver',  'همکار سیلور — قیمت یکماهه'],
  ['gold',    'همکار گلد — قیمت تو حسابی'],
  ['platinum','همکار پلاتینیوم — تو حسابی + گزینه‌ها'],
]

function PartnerRequestsTab() {
  const qc = useQueryClient()
  const [approving, setApproving] = useState(null)  // درخواست در حال تأیید (انتخاب سطح)
  const [tier, setTier] = useState('silver')
  const [msg, setMsg] = useState(null)

  const { data: requests = [], isLoading } = useQuery({
    queryKey: ['partner-requests'],
    queryFn: () => api.get('/users/admin/partners/', { params: { pending: 'true' } }).then(r => r.data),
  })

  const actMut = useMutation({
    mutationFn: ({ userId, payload }) => api.post(`/users/admin/partners/${userId}/approve/`, payload).then(r => r.data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries(['partner-requests'])
      qc.invalidateQueries(['admin-badges'])
      qc.invalidateQueries(['contacts-all'])
      setMsg({ type: 'success', text: vars.payload.is_approved ? 'همکار تأیید شد' : 'درخواست رد شد' })
      setApproving(null)
      setTimeout(() => setMsg(null), 1500)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel text-sm">در حال بارگذاری...</div>

  return (
    <div>
      {msg && (
        <div className={`rounded-lg px-4 py-2 text-xs mb-4 ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          {msg.text}
        </div>
      )}
      {requests.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">🤝</div>
          <div className="text-gray-steel text-sm">درخواست همکاری در انتظاری نیست</div>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map(r => (
            <div key={r.user_id} className="card p-4 flex items-center gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-white text-sm">{r.full_name || r.phone}</span>
                  {signupBadgeOf(r) && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${signupBadgeOf(r).cls}`}>{signupBadgeOf(r).label}</span>
                  )}
                </div>
                <div className="text-[11px] text-gray-steel mt-1 flex gap-3 flex-wrap">
                  <span dir="ltr">{r.phone}</span>
                  {r.company_name && <span>🏢 {r.company_name}</span>}
                  <span>📅 {formatDate(r.created_at)}</span>
                </div>
                {r.address && <div className="text-[11px] text-gray-steel mt-1">📍 {r.address}</div>}
                {/* مدارک احراز — لینک شبکه اجتماعی و مدرک تصویری */}
                <div className="flex gap-3 mt-2 flex-wrap items-center">
                  {r.social_url && (
                    <a href={/^https?:\/\//i.test(r.social_url) ? r.social_url : `https://${r.social_url}`}
                      target="_blank" rel="noreferrer"
                      className="text-[11px] text-brand dark:text-cyan hover:underline" dir="ltr">
                      🔗 {r.social_url}
                    </a>
                  )}
                  {r.document_url && (
                    <a href={mediaUrl(r.document_url)} target="_blank" rel="noreferrer"
                      className="text-[11px] text-brand dark:text-cyan hover:underline">
                      🖼 مشاهده مدرک (کارت ویزیت / ادمین پیج)
                    </a>
                  )}
                  {r.national_id && <span className="text-[11px] text-gray-steel" dir="ltr">🪪 {r.national_id}</span>}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { setApproving(r); setTier('silver') }}
                  disabled={actMut.isPending}
                  className="btn-primary text-xs px-4 py-2 disabled:opacity-50">
                  ✓ تأیید همکار
                </button>
                <button
                  onClick={() => actMut.mutate({ userId: r.user_id, payload: { is_approved: false } })}
                  disabled={actMut.isPending}
                  className="text-xs px-4 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 disabled:opacity-50">
                  ✕ رد
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* مودال انتخاب سطح همکار قبل از تأیید نهایی */}
      {approving && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="card p-6 w-full max-w-sm">
            <h2 className="font-bold text-white text-base mb-1">تأیید همکاری {approving.full_name || approving.phone}</h2>
            <div className="text-xs text-gray-steel mb-4">کدام نوع همکار باشد؟</div>
            <div className="space-y-2 mb-5">
              {TIER_OPTIONS.map(([k, label]) => (
                <label key={k} className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 cursor-pointer text-xs transition-all ${
                  tier === k ? 'border-brand bg-brand/10 text-white' : 'border-white/10 text-gray-steel hover:border-white/30'
                }`}>
                  <input type="radio" name="tier" checked={tier === k} onChange={() => setTier(k)}
                    className="accent-[#FBC02D]" />
                  {label}
                </label>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => actMut.mutate({ userId: approving.user_id, payload: { is_approved: true, partner_tier: tier } })}
                disabled={actMut.isPending}
                className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
                {actMut.isPending ? '...' : '✓ تأیید نهایی'}
              </button>
              <button onClick={() => setApproving(null)} className="btn-secondary text-sm py-2.5 px-5">انصراف</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── تب «تازه تأیید شده» — ۵۰ تأیید اخیر درخواست همکاری (فقط مشاهده) ──
const TIER_BADGE = {
  silver:   { label: 'همکار سیلور',   cls: 'bg-gray-500/20 text-gray-300' },
  gold:     { label: 'همکار گلد',     cls: 'bg-yellow-500/20 text-yellow-400' },
  platinum: { label: 'همکار پلاتینیوم', cls: 'bg-purple-500/20 text-purple-400' },
  '':       { label: 'همکار',         cls: 'bg-brand/20 text-brand dark:text-cyan' },
}

// محل ثبت‌نام: خود مشتری از سایت | ثبت‌شده توسط ما از پنل (کاربر سایه)
const SIGNUP_BADGE = {
  self:  { label: '🌐 ثبت‌نام خود مشتری', cls: 'bg-green-500/20 text-green-400' },
  admin: { label: '🛠 ثبت‌شده توسط ما',  cls: 'bg-blue-500/20 text-blue-400' },
}

function signupBadgeOf(r) {
  return SIGNUP_BADGE[r.signup_source] || null
}

function ApprovedPartnersTab() {
  const { data: approved = [], isLoading } = useQuery({
    queryKey: ['partner-approved'],
    queryFn: () => api.get('/users/admin/partners/', { params: { approved: 'true' } }).then(r => r.data),
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel text-sm">در حال بارگذاری...</div>

  const rows = approved.slice(0, 50)
  return (
    <div>
      {rows.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">✅</div>
          <div className="text-gray-steel text-sm">هنوز درخواست همکاری تأییدشده‌ای نیست</div>
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map(r => {
            const tier = TIER_BADGE[r.partner_tier] || TIER_BADGE['']
            const signup = signupBadgeOf(r)
            return (
              <div key={r.user_id} className="card p-4 flex items-center gap-4 flex-wrap">
                <div className="flex-1 min-w-[200px]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-white text-sm">{r.full_name || r.phone}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${tier.cls}`}>{tier.label}</span>
                    {signup && <span className={`text-[10px] px-2 py-0.5 rounded-full ${signup.cls}`}>{signup.label}</span>}
                  </div>
                  <div className="text-[11px] text-gray-steel mt-1 flex gap-3 flex-wrap">
                    <span dir="ltr">{r.phone}</span>
                    {r.company_name && <span>🏢 {r.company_name}</span>}
                    {/* updated_at = زمان تأیید */}
                    <span>✅ تأیید: {formatDate(r.updated_at)}</span>
                  </div>
                  {r.address && <div className="text-[11px] text-gray-steel mt-1">📍 {r.address}</div>}
                  {/* مدارک احراز — لینک شبکه اجتماعی و مدرک تصویری */}
                  <div className="flex gap-3 mt-2 flex-wrap items-center">
                    {r.social_url && (
                      <a href={/^https?:\/\//i.test(r.social_url) ? r.social_url : `https://${r.social_url}`}
                        target="_blank" rel="noreferrer"
                        className="text-[11px] text-brand dark:text-cyan hover:underline" dir="ltr">
                        🔗 {r.social_url}
                      </a>
                    )}
                    {r.document_url && (
                      <a href={mediaUrl(r.document_url)} target="_blank" rel="noreferrer"
                        className="text-[11px] text-brand dark:text-cyan hover:underline">
                        🖼 مشاهده مدرک (کارت ویزیت / ادمین پیج)
                      </a>
                    )}
                    {r.national_id && <span className="text-[11px] text-gray-steel" dir="ltr">🪪 {r.national_id}</span>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── صفحه طرف حساب‌ها — تب‌دار: کاردکس اشخاص + تراز کلی ───────
export default function ContactsPage() {
  const { can, creatableContactTypes } = usePermissions()
  const [tab, setTab] = useState('kardex')
  const [showAdd, setShowAdd] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedName, setSelectedName] = useState('')
  const [showEdit, setShowEdit] = useState(false)

  const tabs = [
    ...(can('partner_approve') ? [{ key: 'partners', label: '🤝 درخواست‌های همکاری' }] : []),
    ...(can('partner_approve') ? [{ key: 'partners-approved', label: '✅ تازه تأیید شده' }] : []),
    { key: 'kardex',  label: '👤 کاردکس اشخاص' },
    { key: 'balance', label: '📊 تراز کلی' },
  ]
  const activeTab = tabs.some(t => t.key === tab) ? tab : tabs[0].key
  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">طرف حساب‌ها</h1>
        <div className="flex items-center gap-2">
          {activeTab === 'kardex' && selectedId && can('contacts_edit') && (
            <button onClick={() => setShowEdit(true)} className="btn-secondary text-sm px-4 py-2">
              ✏️ ویرایش اطلاعات
            </button>
          )}
          {can('contacts_create') && (creatableContactTypes === null || creatableContactTypes.length > 0) && (
            <button onClick={() => setShowAdd(true)} className="btn-primary text-sm px-4 py-2">+ افزودن طرف حساب</button>
          )}
        </div>
      </div>
      <div className="flex gap-2 mb-6 border-b border-white/10">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${activeTab === t.key ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      {activeTab === 'partners' && <PartnerRequestsTab />}
      {activeTab === 'partners-approved' && <ApprovedPartnersTab />}
      {activeTab === 'kardex' && (
        <ContactKardexTab
          selectedId={selectedId} setSelectedId={setSelectedId}
          selectedName={selectedName} setSelectedName={setSelectedName}
          showEdit={showEdit} setShowEdit={setShowEdit} />
      )}
      {activeTab === 'balance' && <BalanceTab />}

      {showAdd && <AddContactModal creatableTypes={creatableContactTypes} onClose={() => setShowAdd(false)} />}
    </div>
  )
}
