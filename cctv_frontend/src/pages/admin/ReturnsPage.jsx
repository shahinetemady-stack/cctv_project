import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import { formatDate } from '../../utils/date'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../../components/ui/AmountInput'
import SearchSelect from '../../components/ui/SearchSelect'
import { UserStamp } from '../../components/ui'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_COLORS = {
  confirmed: '#00C896',
  cancelled: '#FF6B6B',
}

const TYPE_COLORS = {
  sale: '#0066FF',
  purchase: '#FF9500',
}

const TABS = [
  { key: '', label: 'همه' },
  { key: 'sale', label: 'برگشت از فروش' },
  { key: 'purchase', label: 'برگشت از خرید' },
]

// ─── جزئیات سند برگشت ─────────────────────────────────────────
function ReturnDetail({ id, onBack }) {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const [confirmCancel, setConfirmCancel] = useState(false)

  const { data: inv, isLoading } = useQuery({
    queryKey: ['return-detail', id],
    queryFn: () => api.get(`/accounting/returns/${id}/`).then(r => r.data),
  })

  const cancelMut = useMutation({
    mutationFn: () => api.post(`/accounting/returns/${id}/cancel/`).then(r => r.data),
    onSuccess: () => {
      toast.success('سند برگشت لغو و موجودی برگردانده شد')
      qc.invalidateQueries(['returns'])
      qc.invalidateQueries(['return-detail', id])
      qc.invalidateQueries(['variants-list'])
      setConfirmCancel(false)
    },
    onError: (e) => {
      toast.error(e.response?.data?.error || 'خطا در لغو سند')
      setConfirmCancel(false)
    },
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!inv) return null

  const sourceLabel = inv.return_type === 'sale'
    ? (inv.sale_invoice_number ? `فاکتور فروش ${inv.sale_invoice_number}` : '—')
    : (inv.purchase_invoice_number ? `فاکتور خرید ${inv.purchase_invoice_number}` : '—')

  return (
    <div className="card p-5">
      {/* سربرگ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5 text-sm">
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">شماره سند</div>
          <div className="text-white font-semibold">{inv.invoice_number}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">نوع</div>
          <span style={{
            color: TYPE_COLORS[inv.return_type], background: TYPE_COLORS[inv.return_type] + '20',
            padding: '2px 8px', borderRadius: 20, fontSize: 11,
          }}>{inv.return_type_display}</span>
        </div>
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">سند مبدأ</div>
          <div className="text-white">{sourceLabel}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">انبار</div>
          <div className="text-white">{inv.warehouse_name}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">تاریخ</div>
          <div className="text-white">{formatDate(inv.date)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">وضعیت</div>
          <span style={{
            color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20',
            padding: '2px 8px', borderRadius: 20, fontSize: 11,
          }}>{inv.status_display}</span>
        </div>
        <div>
          <div className="text-[10px] text-gray-steel mb-0.5">ثبت‌کننده</div>
          <div className="text-white text-xs">{inv.created_by || '—'}</div>
        </div>
        {inv.note && (
          <div className="col-span-2">
            <div className="text-[10px] text-gray-steel mb-0.5">یادداشت</div>
            <div className="text-white text-xs">{inv.note}</div>
          </div>
        )}
      </div>

      {/* آیتم‌ها */}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
            {['کالا', 'SKU', 'تعداد', 'فی (ریال)', 'جمع (ریال)'].map(h => (
              <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(inv.items || []).map((it, i) => (
            <tr key={it.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
              <td style={{ padding: '10px 12px' }}>{it.product_name} {it.variant_name && <span className="text-gray-steel text-[11px]">({it.variant_name})</span>}</td>
              <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-secondary)' }}>{it.sku}</td>
              <td style={{ padding: '10px 12px', textAlign: 'center' }}>{fmt(it.quantity)}</td>
              <td style={{ padding: '10px 12px' }}>{fmt(it.unit_price)}</td>
              <td style={{ padding: '10px 12px', color: '#00C896' }}>{fmt(it.subtotal)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex items-center justify-between mt-4 pt-4" style={{ borderTop: '0.5px solid rgba(255,255,255,0.1)' }}>
        <div className="text-sm">
          <span className="text-gray-steel ml-2">جمع سند:</span>
          <span className="text-white font-bold">{fmt(inv.total_amount)} ریال</span>
        </div>
        {inv.status === 'confirmed' && can('return_edit') && (
          confirmCancel ? (
            <span className="flex items-center gap-2 text-xs">
              <span className="text-orange-400">موجودی معکوس می‌شود. مطمئنید؟</span>
              <button onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}
                className="text-red-400 hover:text-red-300">بله، لغو شود</button>
              <button onClick={() => setConfirmCancel(false)} className="text-gray-steel hover:text-white">خیر</button>
            </span>
          ) : (
            <button onClick={() => setConfirmCancel(true)} className="text-xs text-red-400 hover:text-red-300">
              لغو سند برگشت
            </button>
          )
        )}
      </div>
    </div>
  )
}

// ─── فرم صدور سند برگشت ────────────────────────────────────────
function NewReturnForm({ onSuccess }) {
  const qc = useQueryClient()
  const [returnType, setReturnType] = useState('sale')
  const [hdr, setHdr] = useState({
    source_invoice_id: '',
    warehouse_id: '',
    date: new Date().toISOString().split('T')[0],
    note: '',
  })
  const [items, setItems] = useState([{ variant_id: '', quantity: '', unit_price: '' }])
  const [msg, setMsg] = useState(null)

  const { data: variants = [] } = useQuery({
    queryKey: ['variants-list'],
    queryFn: () => api.get('/catalog/variants/').then(r => r.data),
  })
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => api.get('/inventory/warehouses/').then(r => r.data),
  })
  // فاکتورهای مبدأ بر اساس نوع برگشت
  const { data: sourceInvoices = [] } = useQuery({
    queryKey: ['return-source-invoices', returnType],
    queryFn: () => api.get(returnType === 'sale'
      ? '/accounting/sale-invoices/'
      : '/accounting/purchase-invoices/').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/accounting/returns/', d).then(r => r.data),
    onSuccess: (r) => {
      toast.success(r.message || 'سند برگشت صادر شد')
      qc.invalidateQueries(['returns'])
      qc.invalidateQueries(['variants-list'])
      onSuccess?.()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در صدور سند برگشت' }),
  })

  // با انتخاب فاکتور مبدأ، آیتم‌ها از همان فاکتور پیش‌پر می‌شوند
  async function handleSourceChange(invoiceId) {
    setHdr(h => ({ ...h, source_invoice_id: invoiceId }))
    if (!invoiceId) return
    try {
      const url = returnType === 'sale'
        ? `/accounting/sale-invoices/${invoiceId}/`
        : `/accounting/purchase-invoices/${invoiceId}/`
      const inv = await api.get(url).then(r => r.data)
      if (inv.items?.length) {
        setItems(inv.items.map(it => ({
          variant_id: String(it.variant_id),
          quantity: String(it.quantity),
          unit_price: String(
            returnType === 'sale'
              ? it.unit_price
              : (it.unit_cost_irr || it.unit_price_irr || it.unit_price || 0)
          ),
        })))
      }
    } catch { /* پیش‌پر کردن اختیاری است */ }
  }

  function changeType(t) {
    setReturnType(t)
    setHdr(h => ({ ...h, source_invoice_id: '' }))
    setItems([{ variant_id: '', quantity: '', unit_price: '' }])
    setMsg(null)
  }

  function addItem() { setItems(i => [...i, { variant_id: '', quantity: '', unit_price: '' }]) }
  function removeItem(idx) { setItems(i => i.filter((_, j) => j !== idx)) }
  function updateItem(idx, key, val) {
    setItems(i => i.map((it, j) => j === idx ? { ...it, [key]: val } : it))
  }

  const total = items.reduce((s, it) => s + (Number(it.quantity) || 0) * (Number(it.unit_price) || 0), 0)

  function handleSubmit() {
    if (!hdr.warehouse_id) return setMsg({ type: 'error', text: 'انبار را انتخاب کنید' })
    if (!hdr.date) return setMsg({ type: 'error', text: 'تاریخ الزامی است' })
    const validItems = items.filter(it => it.variant_id && Number(it.quantity) > 0)
    if (!validItems.length) return setMsg({ type: 'error', text: 'حداقل یک آیتم با تعداد معتبر لازم است' })

    createMut.mutate({
      return_type: returnType,
      sale_invoice_id: returnType === 'sale' ? (hdr.source_invoice_id || null) : null,
      purchase_invoice_id: returnType === 'purchase' ? (hdr.source_invoice_id || null) : null,
      warehouse_id: hdr.warehouse_id,
      date: hdr.date,
      note: hdr.note,
      items: validItems.map(it => ({
        variant_id: it.variant_id,
        quantity: Number(it.quantity),
        unit_price: Number(it.unit_price) || 0,
      })),
    })
  }

  return (
    <div className="card p-5">
      {/* نوع برگشت */}
      <div className="flex gap-2 mb-5">
        {[['sale', 'برگشت از فروش (ورود کالا از مشتری)'], ['purchase', 'برگشت از خرید (خروج کالا به تأمین‌کننده)']].map(([val, label]) => (
          <button key={val} onClick={() => changeType(val)}
            className="flex-1 text-xs px-3 py-2.5 rounded-xl transition-all"
            style={{
              background: returnType === val ? TYPE_COLORS[val] + '25' : 'rgba(255,255,255,0.03)',
              color: returnType === val ? TYPE_COLORS[val] : 'var(--color-text-secondary)',
              border: `1px solid ${returnType === val ? TYPE_COLORS[val] : 'var(--color-border)'}`,
            }}>
            {label}
          </button>
        ))}
      </div>

      {/* سربرگ */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
        <div>
          <label className="label text-xs mb-1 block">فاکتور مبدأ (اختیاری — آیتم‌ها پیش‌پر می‌شوند)</label>
          <SearchSelect
            options={sourceInvoices.map(inv => ({
              value: inv.id,
              label: returnType === 'sale'
                ? `${inv.invoice_number} — ${inv.customer_name}`
                : `${inv.invoice_number || '#' + inv.id} — ${inv.supplier_name}`,
            }))}
            value={hdr.source_invoice_id}
            onChange={handleSourceChange}
            placeholder="جستجوی شماره فاکتور..."
          />
        </div>
        <div>
          <label className="label text-xs mb-1 block">انبار *</label>
          <select value={hdr.warehouse_id} onChange={e => setHdr(h => ({ ...h, warehouse_id: e.target.value }))} className="input text-sm">
            <option value="">انتخاب کنید...</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label text-xs mb-1 block">تاریخ *</label>
          <input type="date" value={hdr.date} onChange={e => setHdr(h => ({ ...h, date: e.target.value }))} className="input text-sm" />
        </div>
      </div>

      {/* آیتم‌ها */}
      <div className="text-xs font-semibold text-white mb-2">اقلام برگشتی</div>
      <div className="space-y-2 mb-3">
        {items.map((item, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-2 items-end bg-white/5 rounded-lg p-3">
            <div className="col-span-12 md:col-span-5">
              <label className="label text-[10px] mb-1 block">کالا *</label>
              <SearchSelect
                options={variants.map(v => ({ value: v.id, label: v.product_name, sub: v.sku }))}
                value={item.variant_id}
                onChange={val => updateItem(idx, 'variant_id', val)}
                placeholder="جستجوی کالا (نام یا کد)..."
              />
            </div>
            <div className="col-span-4 md:col-span-2">
              <label className="label text-[10px] mb-1 block">تعداد *</label>
              <input type="number" min="1" value={item.quantity}
                onChange={e => updateItem(idx, 'quantity', e.target.value)} className="input text-xs" />
            </div>
            <div className="col-span-6 md:col-span-3">
              <label className="label text-[10px] mb-1 block">فی (ریال)</label>
              <AmountInput value={item.unit_price}
                onChange={e => updateItem(idx, 'unit_price', e.target.value)} className="input text-xs" />
            </div>
            <div className="col-span-2 md:col-span-2 flex items-center justify-between">
              <span className="text-[10px] text-gray-steel">{fmt((Number(item.quantity) || 0) * (Number(item.unit_price) || 0))}</span>
              {items.length > 1 && (
                <button onClick={() => removeItem(idx)} className="text-red-400 hover:text-red-300 text-xs">✕</button>
              )}
            </div>
          </div>
        ))}
      </div>
      <button onClick={addItem} className="btn-secondary text-xs px-3 py-1.5 mb-4">+ افزودن قلم</button>

      <div className="mb-4">
        <label className="label text-xs mb-1 block">یادداشت</label>
        <textarea value={hdr.note} onChange={e => setHdr(h => ({ ...h, note: e.target.value }))}
          rows={2} className="input text-sm w-full" placeholder="علت برگشت، وضعیت کالا و..." />
      </div>

      {msg && (
        <div className={`text-xs mb-3 px-3 py-2 rounded-lg ${msg.type === 'error' ? 'text-red-400 bg-red-400/10' : 'text-green-400 bg-green-400/10'}`}>
          {msg.text}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="text-sm">
          <span className="text-gray-steel ml-2">جمع سند:</span>
          <span className="text-white font-bold">{fmt(total)} ریال</span>
        </div>
        <button onClick={handleSubmit} disabled={createMut.isPending} className="btn-primary text-sm px-6 py-2">
          {createMut.isPending ? 'در حال ثبت...' : 'صدور سند برگشت'}
        </button>
      </div>
    </div>
  )
}

// ─── صفحه اصلی ─────────────────────────────────────────────────
export default function ReturnsPage() {
  const [view, setView] = useState('list') // list | new | detail
  const [selectedId, setSelectedId] = useState(null)
  const [tab, setTab] = useState('')
  const { can } = usePermissions()

  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [view])

  const { data: returns = [], isLoading } = useQuery({
    queryKey: ['returns', tab],
    queryFn: () => api.get(`/accounting/returns/${tab ? `?type=${tab}` : ''}`).then(r => r.data),
    enabled: view === 'list',
  })

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          {view !== 'list' && (
            <button onClick={() => setView('list')} className="text-gray-steel hover:text-white text-sm">← برگشت</button>
          )}
          <h1 className="font-display font-bold text-xl md:text-2xl text-white">
            {view === 'list' ? 'برگشت از فروش و خرید' : view === 'new' ? 'صدور سند برگشت' : 'جزئیات سند برگشت'}
          </h1>
        </div>
        {view === 'list' && can('return_create') && (
          <button onClick={() => setView('new')} className="btn-primary text-sm px-4 py-2">+ سند برگشت جدید</button>
        )}
      </div>

      {view === 'new' && <NewReturnForm onSuccess={() => setView('list')} />}
      {view === 'detail' && <ReturnDetail id={selectedId} onBack={() => setView('list')} />}

      {view === 'list' && (
        <div className="card p-5">
          {/* تب‌های نوع */}
          <div className="flex gap-2 mb-4">
            {TABS.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className="text-xs px-3 py-1.5 rounded-full transition-all"
                style={{
                  background: tab === t.key ? 'rgba(251,192,45,0.15)' : 'rgba(255,255,255,0.03)',
                  color: tab === t.key ? 'var(--color-brand)' : 'var(--color-text-secondary)',
                  border: `1px solid ${tab === t.key ? 'var(--color-brand)' : 'var(--color-border)'}`,
                }}>
                {t.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
          ) : returns.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-3">↩️</div>
              <div className="text-gray-steel text-sm mb-4">هنوز سند برگشتی ثبت نشده</div>
              {can('return_create') && (
                <button onClick={() => setView('new')} className="btn-primary text-sm px-6 py-2">+ صدور اولین سند</button>
              )}
            </div>
          ) : (
            <>
              {/* ─── Desktop: Table ─── */}
              <div className="hidden md:block">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['شماره', 'نوع', 'سند مبدأ', 'انبار', 'تاریخ', 'اقلام', 'جمع (ریال)', 'وضعیت', 'ثبت‌کننده', ''].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {returns.map((inv, i) => (
                      <tr key={inv.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                        <td style={{ padding: '10px 12px' }}>{inv.invoice_number}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{
                            color: TYPE_COLORS[inv.return_type], background: TYPE_COLORS[inv.return_type] + '20',
                            padding: '2px 8px', borderRadius: 20, fontSize: 11,
                          }}>{inv.return_type_display}</span>
                        </td>
                        <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-secondary)' }}>
                          {inv.return_type === 'sale' ? inv.sale_invoice_number : inv.purchase_invoice_number || '—'}
                        </td>
                        <td style={{ padding: '10px 12px', fontSize: 11 }}>{inv.warehouse_name}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{formatDate(inv.date)}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>{inv.items_count}</td>
                        <td style={{ padding: '10px 12px', color: '#00C896' }}>{fmt(inv.total_amount)}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{
                            color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20',
                            padding: '2px 8px', borderRadius: 20, fontSize: 11,
                          }}>{inv.status_display}</span>
                        </td>
                        <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                          <UserStamp createdBy={inv.created_by} updatedBy={inv.updated_by} createdAt={inv.created_at} updatedAt={inv.updated_at} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <button onClick={() => { setSelectedId(inv.id); setView('detail') }}
                            className="text-xs text-brand hover:text-brand/80">مشاهده</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* ─── Mobile: Card List ─── */}
              <div className="md:hidden space-y-3">
                {returns.map((inv) => (
                  <div key={inv.id} className="rounded-xl p-4"
                    style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}
                    onClick={() => { setSelectedId(inv.id); setView('detail') }}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-white">{inv.invoice_number}</span>
                      <span style={{
                        color: TYPE_COLORS[inv.return_type], background: TYPE_COLORS[inv.return_type] + '20',
                        padding: '1px 8px', borderRadius: 20, fontSize: 10,
                      }}>{inv.return_type_display}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-gray-steel">
                      <span>{inv.warehouse_name} • {formatDate(inv.date)}</span>
                      <span className="text-white font-semibold">{fmt(inv.total_amount)} ریال</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
