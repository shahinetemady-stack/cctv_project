import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const TYPE_COLORS = {
  supplier_cn: '#0066FF', clearance: '#FF9500',
  shipping_co: '#00C896', staff: '#8B5CF6', other: '#888',
}

// ─── تب تراز کلی ────────────────────────────────────────────
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
      {/* خلاصه */}
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

      {/* جستجو */}
      <div className="mb-4">
        <input value={filter} onChange={e => setFilter(e.target.value)}
          className="input text-sm max-w-xs" placeholder="جستجو نام یا نوع..." />
      </div>

      {/* جدول */}
      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-12 text-gray-steel">تراکنشی یافت نشد</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['طرف حساب', 'نوع', 'مانده ریال', 'وضعیت', 'مانده یوان', 'وضعیت'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contacts.map((c, i) => (
                <tr key={c.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 600 }}>{c.name}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: TYPE_COLORS[c.contact_type] || '#888', background: (TYPE_COLORS[c.contact_type] || '#888') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                      {c.contact_type_display}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896' }}>
                    {fmt(Math.abs(c.balance_irr))} ت
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896', background: (c.balance_irr > 0 ? '#FF3B3B' : '#00C896') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                      {c.balance_irr > 0 ? 'بدهکار' : 'بستانکار'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896' }}>
                    {c.balance_cny !== 0 ? `${fmt(Math.abs(c.balance_cny))} ¥` : '—'}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {c.balance_cny !== 0 && (
                      <span style={{ color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896', background: (c.balance_cny > 0 ? '#FF3B3B' : '#00C896') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
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

// ─── تب کاردکس اشخاص ────────────────────────────────────────
function ContactKardexTab() {
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedName, setSelectedName] = useState('')

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const { data: detail, isLoading } = useQuery({
    queryKey: ['contact-kardex', selectedId],
    queryFn: () => api.get(`/accounting/contacts/${selectedId}/`).then(r => r.data),
    enabled: !!selectedId,
  })

  const filtered = contacts.filter(c =>
    !search || c.name.includes(search) || c.contact_type_display.includes(search)
  ).slice(0, 15)

  // ترکیب فاکتورها و پرداخت‌ها در یک تایم‌لاین
  const timeline = []
  if (detail) {
    detail.invoices?.forEach(inv => timeline.push({ ...inv, _type: 'invoice', _date: inv.date }))
    detail.payments?.forEach(p => timeline.push({ ...p, _type: 'payment', _date: p.date }))
    timeline.sort((a, b) => new Date(b._date) - new Date(a._date))
  }

  // محاسبه مانده تجمعی
  let runningBalance = 0
  const timelineWithBalance = [...timeline].reverse().map(item => {
    if (item._type === 'invoice') runningBalance += item.total_irr || 0
    else if (item._type === 'payment') runningBalance -= item.amount_irr || 0
    return { ...item, _balance: runningBalance }
  }).reverse()

  return (
    <div>
      {/* جستجوی شخص */}
      <div className="card p-5 mb-6">
        <div className="relative max-w-md">
          <label className="label text-xs mb-1 block">جستجو و انتخاب طرف حساب</label>
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setShowDropdown(true) }}
            onFocus={() => setShowDropdown(true)}
            placeholder="نام طرف حساب را جستجو کنید..."
            className="input text-sm"
          />
          {showDropdown && filtered.length > 0 && (
            <div className="absolute z-50 top-full right-0 left-0 mt-1 bg-navy border border-white/10 rounded-xl shadow-xl overflow-hidden max-h-60 overflow-y-auto">
              {filtered.map(c => (
                <button key={c.id}
                  className="w-full text-right px-4 py-3 hover:bg-white/5 border-b border-white/5 last:border-0"
                  onClick={() => { setSelectedId(c.id); setSelectedName(c.name); setSearch(c.name); setShowDropdown(false) }}>
                  <div className="text-sm text-white">{c.name}</div>
                  <div className="flex gap-3 mt-0.5">
                    <span className="text-[10px] text-gray-steel">{c.contact_type_display}</span>
                    <span className={`text-[10px] font-bold ${c.balance_irr > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {c.balance_irr > 0 ? 'بدهکار' : 'بستانکار'}: {fmt(Math.abs(c.balance_irr))} ت
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
          {showDropdown && <div className="fixed inset-0 z-40" onClick={() => setShowDropdown(false)} />}
          {detail && (
            <div className="mt-2 flex gap-4">
              <span className={`text-sm font-bold ${detail.balance_irr > 0 ? 'text-red-400' : 'text-green-400'}`}>
                مانده ریال: {detail.balance_irr > 0 ? 'بدهکار' : 'بستانکار'} {fmt(Math.abs(detail.balance_irr))} ت
              </span>
              {detail.balance_cny !== 0 && (
                <span className={`text-sm font-bold ${detail.balance_cny > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  مانده یوان: {fmt(Math.abs(detail.balance_cny))} ¥
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {selectedId && (
        isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">کاردکس {selectedName}</h3>
            {timelineWithBalance.length === 0 ? (
              <div className="text-center py-8 text-gray-steel text-sm">هیچ تراکنشی ثبت نشده</div>
            ) : (
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['تاریخ', 'نوع سند', 'شرح', 'بدهکار (ریال)', 'بستانکار (ریال)', 'مانده (ریال)'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {timelineWithBalance.map((item, i) => {
                      const isInvoice = item._type === 'invoice'
                      const debit = isInvoice ? item.total_irr : (item.direction === 'in' ? item.amount_irr : 0)
                      const credit = !isInvoice && item.direction === 'out' ? item.amount_irr : 0
                      const desc = isInvoice
                        ? `فاکتور خرید ${item.invoice_number || '#' + item.id}`
                        : `${item.payment_type_display || 'پرداخت'} ${item.reference ? '| ' + item.reference : ''}`
                      return (
                        <tr key={i} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                          <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{item._date}</td>
                          <td style={{ padding: '10px 12px' }}>
                            <span style={{
                              color: isInvoice ? '#0066FF' : '#00C896',
                              background: (isInvoice ? '#0066FF' : '#00C896') + '20',
                              padding: '2px 8px', borderRadius: 20, fontSize: 11
                            }}>
                              {isInvoice ? 'فاکتور خرید' : 'پرداخت'}
                            </span>
                          </td>
                          <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{desc}</td>
                          <td style={{ padding: '10px 12px', color: '#FF3B3B', fontWeight: debit ? 600 : 400 }}>
                            {debit ? fmt(debit) : '—'}
                          </td>
                          <td style={{ padding: '10px 12px', color: '#00C896', fontWeight: credit ? 600 : 400 }}>
                            {credit ? fmt(credit) : '—'}
                          </td>
                          <td style={{ padding: '10px 12px', fontWeight: 700, color: item._balance > 0 ? '#FF3B3B' : '#00C896' }}>
                            {fmt(Math.abs(item._balance))}
                            <span className="text-[10px] mr-1">{item._balance > 0 ? 'بد' : 'بس'}</span>
                          </td>
                        </tr>
                      )
                    })}
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
    </div>
  )
}

// ─── صفحه اصلی گزارشات ──────────────────────────────────────
export default function ReportsPage() {
  const [tab, setTab] = useState('balance')

  const tabs = [
    { key: 'balance', label: '📊 تراز کلی' },
    { key: 'contact', label: '👤 کاردکس اشخاص' },
  ]

  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">گزارشات مالی</h1>

      {/* تب‌ها */}
      <div className="flex gap-2 mb-6 border-b border-white/10 pb-0">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${
              tab === t.key
                ? 'border-brand text-white bg-brand/10'
                : 'border-transparent text-gray-steel hover:text-white'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'balance' && <BalanceTab />}
      {tab === 'contact' && <ContactKardexTab />}
    </div>
  )
}
