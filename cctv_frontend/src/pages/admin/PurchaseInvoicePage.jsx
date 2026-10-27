import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import { formatDate, todayTehran } from '../../utils/date'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../../components/ui/AmountInput'
import SearchSelect, { advanceFlow } from '../../components/ui/SearchSelect'
import { printPurchaseInvoice } from '../../utils/purchasePrint'
import { UserStamp } from '../../components/ui'
import AddContactModal from '../../components/accounting/AddContactModal'
import JalaliDateInput from '../../components/ui/JalaliDateInput'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_COLORS = {
  ordered:   '#FF9500',
  received:  '#0066FF',
  paid:      '#00C896',
  cancelled: '#FF6B6B',
}

// ─── فیلد قیمت با راهنمای آخرین خرید (قیمت + تاریخ — با Enter محو می‌شود) ──
function PriceWithLast({ value, onChange, onEnter, supplierId, variantId, isCny, disabled, className = 'input text-xs' }) {
  const [done, setDone] = useState(false) // با Enter راهنما محو می‌شود؛ با عوض شدن کالا ریست
  useEffect(() => setDone(false), [variantId])
  const { data: last } = useQuery({
    queryKey: ['last-price', supplierId, variantId],
    queryFn: () => api.get('/accounting/purchase-invoices/last-price/', {
      params: { supplier_id: supplierId, variant_id: variantId },
    }).then(r => r.data),
    enabled: !!supplierId && !!variantId,
  })
  const price = isCny ? last?.unit_price_cny : last?.unit_price_irr
  return (
    <div>
      <AmountInput value={value} onChange={onChange} disabled={disabled}
        placeholder={last?.found ? String(price) : '0'}
        className={className}
        data-flow="pi"
        onKeyDown={e => {
          if (e.key === 'Enter') {
            e.preventDefault()
            setDone(true)
            onEnter ? onEnter(e) : advanceFlow('pi', e.target)
          }
        }} />
      {last?.found && !done && (
        <div className="text-base font-bold text-gold mt-1">
          آخرین خرید: {Number(price).toLocaleString('fa-IR')} {isCny ? 'یوان' : 'ریال'} — {formatDate(last.date)}
        </div>
      )}
    </div>
  )
}

const EXTRA_TYPES = [
  { value: 'rent',        label: 'اجاره' },
  { value: 'delivery',    label: 'پیک / ارسال' },
  { value: 'commission',  label: 'پورسانت' },
  { value: 'electricity', label: 'برق' },
  { value: 'insurance',   label: 'بیمه' },
  { value: 'other',       label: 'سایر' },
]

// انبارهای مرحله ۱ — معمولاً انبارهای «در راه»
const TRANSIT_TYPES = ['air_transit', 'sea_transit']

// ═══════════════════════════════════════════════════════════════
// InvoiceDetail
// ═══════════════════════════════════════════════════════════════
function InvoiceDetail({ id, onClose, onEdit }) {
  const { can } = usePermissions()
  const { data: inv, isLoading } = useQuery({
    queryKey: ['invoice-detail', id],
    queryFn: () => api.get(`/accounting/purchase-invoices/${id}/`).then(r => r.data),
  })
  const qc = useQueryClient()
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })

  const payMut = useMutation({
    mutationFn: (d) => api.post('/accounting/payments/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['invoice-detail', id])
      qc.invalidateQueries(['purchase-invoices'])
      setPayForm(f => ({ ...f, show: false, amount: '', reference: '', from_account_id: '' }))
    },
    onError: (e) => setPayForm(f => ({ ...f, error: e.response?.data?.error || 'خطا در ثبت پرداخت' })),
  })

  const [payForm, setPayForm] = useState({
    show: false, direction: 'out', payment_type: 'transfer',
    currency: 'IRR', amount: '', rate_irr: '', from_account_id: '', error: '',
    date: todayTehran(), reference: '',
  })
  useEffect(() => {
    if (inv?.id) {
      setPayForm(f => ({ ...f, currency: inv.purchase_type === 'foreign' ? 'CNY' : 'IRR' }))
    }
  }, [inv?.id])
  const [confirmDelete, setConfirmDelete] = useState(false)

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/accounting/purchase-invoices/${id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['purchase-invoices'])
      qc.invalidateQueries(['pending-receive'])
      qc.invalidateQueries(['variants-list'])
      onClose()
    },
    onError: (e) => {
      setConfirmDelete(false)
      alert(e.response?.data?.error || 'خطا در حذف فاکتور')
    },
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!inv) return null

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-bold text-white text-lg">فاکتور {inv.invoice_number || `#${inv.id}`}</h2>
            <div className="text-xs text-gray-steel mt-1">
              {inv.supplier?.name} | {formatDate(inv.date)}
              {inv.shipping_contact && <span> | شرکت حمل: {inv.shipping_contact.name}</span>}
            </div>
            {inv.warehouse && inv.warehouse_destination ? (
              <div className="text-[11px] text-blue-400 mt-1">
                {inv.warehouse.name} → {inv.warehouse_destination.name}
              </div>
            ) : inv.warehouse ? (
              <div className="text-[11px] text-orange-400 mt-1">
                در: {inv.warehouse.name} (هنوز نرسیده)
              </div>
            ) : null}
            {inv.received_at && (
              <div className="text-[10px] text-blue-400 mt-1">
                دریافت شده در: {new Date(inv.received_at).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}
              </div>
            )}
            {/* حسابرسی — ثبت و ویرایش توسط چه کسی و چه زمانی */}
            <div className="text-[10px] text-[var(--color-text-muted)] mt-2 pt-2 border-t border-white/5">
              📝 ثبت شده توسط <b className="text-gray-steel">{inv.created_by || '—'}</b> در {formatDate(inv.created_at, { withTime: true })}
              {inv.updated_by && (
                <> | ✏️ ویرایش شده توسط <b className="text-gray-steel">{inv.updated_by}</b> در {formatDate(inv.updated_at, { withTime: true })}</>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => printPurchaseInvoice(inv)} title="چاپ فاکتور"
              className="text-xs px-3 py-1.5 rounded-lg border border-white/20 text-gray-steel hover:text-gold hover:border-gold/40 transition-colors">
              🖨 پرینت
            </button>
            {inv.status !== 'cancelled' && can('purchase_edit') && (
              <button onClick={onEdit} className="btn-secondary text-xs px-3 py-1.5">✏️ ویرایش فاکتور</button>
            )}
            {/* حذف فاکتور — دو مرحله‌ای، با برگشت موجودی */}
            {can('purchase_edit') && (
              confirmDelete ? (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-red-400">فاکتور و موجودی‌اش برگردانده شود؟</span>
                  <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                    className="text-xs px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 disabled:opacity-50">
                    {deleteMut.isPending ? '...' : 'بله، حذف'}
                  </button>
                  <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-steel hover:text-white">خیر</button>
                </div>
              ) : (
                <button onClick={() => setConfirmDelete(true)}
                  className="text-xs px-3 py-1.5 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors">
                  🗑 حذف
                </button>
              )
            )}
            <span style={{
              color: STATUS_COLORS[inv.status] || '#888',
              background: (STATUS_COLORS[inv.status] || '#888') + '20',
            }} className="text-xs px-3 py-1 rounded-full">{inv.status_display}</span>
            {inv.purchase_type_display && (
              <span className={`text-xs px-3 py-1 rounded-full ${inv.purchase_type === 'domestic' ? 'bg-green-500/15 text-green-400' : 'bg-blue-500/15 text-blue-400'}`}>
                {inv.purchase_type_display}
              </span>
            )}
            <button onClick={onClose} className="text-gray-steel hover:text-white">✕</button>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-steel mb-1">نرخ خرید</div>
            <div className="text-sm font-bold text-white">{fmt(inv.rate_purchase_cny)}</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-steel mb-1">نرخ حمل</div>
            <div className="text-sm font-bold text-white">{inv.rate_shipping_cny ? fmt(inv.rate_shipping_cny) : '—'}</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-steel mb-1">جمع یوان</div>
            <div className="text-sm font-bold text-blue-400">{fmt(inv.total_cny)} ¥</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-steel mb-1">جمع ریال</div>
            <div className="text-sm font-bold text-green-400">{fmt(inv.total_irr)} ریال</div>
          </div>
        </div>
        {inv.inventory_applied && (
          <div className="mt-3 text-xs text-green-400 bg-green-500/10 px-3 py-2 rounded-lg">
            ✓ موجودی این فاکتور به انبار اضافه شده است
          </div>
        )}
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-3">
          اقلام فاکتور (وزن کل: {inv.total_weight || '—'} kg)
        </h3>
        <div className="overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['کالا', 'تعداد', 'کارتن', 'وزن(kg)', 'قیمت(¥)', 'جمع(¥)', 'سهم حمل', 'سهم ترخیص', 'بهای تمام شده'].map(h => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inv.items?.map((item, i) => (
                <tr key={item.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '8px 10px' }}>
                    <div className="text-xs text-white">{item.product_name}</div>
                    <div className="text-[10px] text-gray-steel">{item.variant_sku}</div>
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>{fmt(item.quantity)}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>{item.carton_count}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>{item.total_weight || '—'}</td>
                  <td style={{ padding: '8px 10px', color: '#0066FF' }}>{fmt(item.unit_price_cny)}</td>
                  <td style={{ padding: '8px 10px', color: '#0066FF' }}>{fmt(item.subtotal_cny)}</td>
                  <td style={{ padding: '8px 10px', color: '#FF9500', fontSize: 11 }}>{fmt(item.shipping_cost_irr)}</td>
                  <td style={{ padding: '8px 10px', color: '#FF6B6B', fontSize: 11 }}>{fmt(item.clearance_cost_irr)}</td>
                  <td style={{ padding: '8px 10px', fontWeight: 700, color: '#00C896' }}>{fmt(item.unit_cost_irr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">پرداخت‌ها</h3>
          <button onClick={() => setPayForm(f => ({ ...f, show: true }))}
            className="text-xs text-brand hover:text-brand/80">+ ثبت پرداخت</button>
        </div>
        {payForm.show && (
          <div className="bg-white/5 rounded-xl p-4 mb-4 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label text-xs mb-1 block">ارز</label>
                <select value={payForm.currency} onChange={e => setPayForm(f => ({ ...f, currency: e.target.value }))} className="input text-xs">
                  <option value="CNY">یوان</option>
                  <option value="IRR">ریال</option>
                </select>
              </div>
              <div>
                <label className="label text-xs mb-1 block">مبلغ</label>
                <AmountInput value={payForm.amount} onChange={e => setPayForm(f => ({ ...f, amount: e.target.value }))} className="input text-xs" />
              </div>
              {payForm.currency !== 'IRR' && (
                <div>
                  <label className="label text-xs mb-1 block">نرخ تبدیل (ریال)</label>
                  <AmountInput value={payForm.rate_irr} onChange={e => setPayForm(f => ({ ...f, rate_irr: e.target.value }))} className="input text-xs" />
                </div>
              )}
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <JalaliDateInput value={payForm.date} onChange={v => setPayForm(f => ({ ...f, date: v }))} className="input text-xs" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">نوع</label>
                <select value={payForm.payment_type} onChange={e => setPayForm(f => ({ ...f, payment_type: e.target.value }))} className="input text-xs">
                  <option value="transfer">حواله</option>
                  <option value="cash">نقد</option>
                  <option value="installment">قسط</option>
                </select>
              </div>
              <div>
                <label className="label text-xs mb-1 block">حساب مبدأ *</label>
                <select value={payForm.from_account_id}
                  onChange={e => setPayForm(f => ({ ...f, from_account_id: e.target.value }))}
                  className="input text-xs">
                  <option value="">انتخاب حساب</option>
                  {accounts.filter(a => a.currency === payForm.currency && (
                    payForm.payment_type === 'cash'
                      ? ['cash', 'petty'].includes(a.account_type)
                      : ['bank', 'virtual'].includes(a.account_type)
                  )).map(a => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
                </select>
              </div>
              <div>
                <label className="label text-xs mb-1 block">مرجع</label>
                <input value={payForm.reference} onChange={e => setPayForm(f => ({ ...f, reference: e.target.value }))} className="input text-xs" />
              </div>
            </div>
            {payForm.error && <div className="text-xs text-red-400">{payForm.error}</div>}
            <div className="flex gap-2">
              <button onClick={() => {
                if (!(Number(payForm.amount) > 0)) return setPayForm(f => ({ ...f, error: 'مبلغ معتبر را وارد کنید' }))
                if (!payForm.from_account_id) return setPayForm(f => ({ ...f, error: 'حساب مبدأ را انتخاب کنید' }))
                if (payForm.currency !== 'IRR' && !(Number(payForm.rate_irr) > 0)) {
                  return setPayForm(f => ({ ...f, error: 'نرخ تبدیل به ریال را وارد کنید' }))
                }
                setPayForm(f => ({ ...f, error: '' }))
                payMut.mutate({ contact_id: inv.supplier.id, invoice_id: id, direction: 'out', ...payForm })
              }} disabled={payMut.isPending} className="btn-primary text-xs px-4 py-2 disabled:opacity-50">
                {payMut.isPending ? 'در حال ثبت...' : 'ثبت'}
              </button>
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
                  <div className="text-xs text-white">{p.payment_type_display} | {formatDate(p.date)}</div>
                  {p.reference && <div className="text-[10px] text-gray-steel">{p.reference}</div>}
                </div>
                <div className="text-sm font-bold text-red-400">-{fmt(p.amount)} {p.currency}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// NewInvoiceForm — مرحله ۱: ثبت سفارش (با شرکت حمل و انبار در راه)
// با prop «editing» (شناسه فاکتور) به حالت ویرایش می‌رود
// ═══════════════════════════════════════════════════════════════
function NewInvoiceForm({ onClose, onSuccess, editing }) {
  const [ptype, setPtype] = useState('domestic') // نوع خرید — داخلی (رسید مستقیم) | خارجی (دو مرحله‌ای)
  const { creatableContactTypes } = usePermissions()
  // مودال ساخت سریع طرف حساب — 'supplier' (تامین‌کننده) یا 'shipper' (شرکت حمل)
  const [quickAdd, setQuickAdd] = useState(null)
  const canQuickAdd = (t) => creatableContactTypes === null || creatableContactTypes.includes(t)
  // نرخ یوان مرجع — پیش‌پر کردن «نرخ یوان خرید» در خرید خارجی
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })
  const { data: variants = [] } = useQuery({
    queryKey: ['variants-list'],
    queryFn: () => api.get('/catalog/variants/').then(r => r.data),
  })
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => api.get('/inventory/warehouses/').then(r => r.data),
  })
  const { data: editInv, isLoading: editLoading } = useQuery({
    queryKey: ['invoice-detail', editing],
    queryFn: () => api.get(`/accounting/purchase-invoices/${editing}/`).then(r => r.data),
    enabled: !!editing,
  })

  const [hdr, setHdr] = useState({
    supplier_id: '',
    invoice_number: '',
    date: todayTehran(),
    warehouse_id: '',
    warehouse_destination_id: '',
    shipping_contact_id: '',
    rate_purchase_cny: '',
    rate_shipping_cny: '',
    shipping_cost_cny: '',
    clearance_cost_irr: '',
    note: '',
  })
  const [items, setItems] = useState([{
    variant_id: '', quantity: '',
    unit_price_cny: '', unit_price_irr: '', note: '',
  }])
  const [extras, setExtras] = useState([])
  const [initialized, setInitialized] = useState(false)
  const [msg, setMsg] = useState(null)

  // پیش‌پر کردن نرخ یوان خرید با نرخ مرجع (فقط فاکتور جدید، اگر خالی است)
  useEffect(() => {
    if (!editing && rateData?.rate_cny_to_irt) {
      setHdr(h => h.rate_purchase_cny ? h : { ...h, rate_purchase_cny: String(rateData.rate_cny_to_irt) })
    }
  }, [rateData, editing])

  // پیش‌پر کردن فرم در حالت ویرایش
  if (editing && editInv && !initialized) {
    setInitialized(true)
    setPtype(editInv.purchase_type || 'foreign') // چیدمان فرم بر اساس نوع فاکتور
    setHdr({
      supplier_id: editInv.supplier?.id || '',
      invoice_number: editInv.invoice_number || '',
      date: editInv.date || '',
      warehouse_id: editInv.warehouse?.id || '',
      warehouse_destination_id: editInv.warehouse_destination?.id || '',
      shipping_contact_id: editInv.shipping_contact?.id || '',
      rate_purchase_cny: editInv.rate_purchase_cny || '',
      rate_shipping_cny: editInv.rate_shipping_cny || '',
      shipping_cost_cny: editInv.shipping_cost_cny || '',
      clearance_cost_irr: editInv.clearance_cost_irr || '',
      note: editInv.note || '',
    })
    setItems(editInv.items?.length ? editInv.items.map(it => ({
      variant_id: String(it.variant_id),
      quantity: String(it.quantity),
      carton_count: String(it.carton_count ?? 1),
      carton_weight: it.carton_weight ? String(it.carton_weight) : '',
      unit_price_cny: String(it.unit_price_cny ?? ''),
      unit_price_irr: String(it.unit_price_irr ?? ''),
      note: it.note || '',
    })) : [{ variant_id: '', quantity: '', unit_price_cny: '', unit_price_irr: '', note: '' }])
    setExtras((editInv.extra_costs || []).map(e => ({
      cost_type: e.cost_type,
      amount_irr: String(e.amount_irr ?? ''),
      description: e.description || '',
    })))
  }

  // آیتم‌ها و هزینه‌های جانبی فقط در وضعیت «سفارش داده شده» قابل ویرایش‌اند
  const itemsEditable = !editing || editInv?.status === 'ordered'

  const qc = useQueryClient()
  const createMut = useMutation({
    mutationFn: (d) => editing
      ? api.patch(`/accounting/purchase-invoices/${editing}/`, d).then(r => r.data)
      : api.post('/accounting/purchase-invoices/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['purchase-invoices'])
      qc.invalidateQueries(['pending-receive'])
      qc.invalidateQueries(['variants-list'])
      if (editing) {
        qc.invalidateQueries(['invoice-detail', editing])
        setMsg({ type: 'success', text: 'تغییرات فاکتور ذخیره شد' })
        setTimeout(() => onSuccess?.(), 800)
      } else {
        onSuccess?.()
      }
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || (editing ? 'خطا در ویرایش فاکتور' : 'خطا در ثبت سفارش') }),
  })

  // خرید ممکن است از هر طرف حسابی باشد (تامین‌کننده چینی، مشتری، همکار و...) — همه نمایش داده می‌شوند
  const suppliers = contacts
  const shippers = contacts.filter(c => ['clearance', 'shipping_co'].includes(c.contact_type))
  // انبارهای در راه را اول لیست بگذار
  const transitWarehouses = warehouses.filter(w => TRANSIT_TYPES.includes(w.warehouse_type))
  const otherWarehouses = warehouses.filter(w => !TRANSIT_TYPES.includes(w.warehouse_type))

  function addItem() { setItems(i => [...i, { variant_id: '', quantity: '', unit_price_cny: '', unit_price_irr: '', note: '' }]) }
  function removeItem(idx) { setItems(i => i.filter((_, j) => j !== idx)) }
  function updateItem(idx, key, val) {
    setItems(i => i.map((it, j) => j === idx ? { ...it, [key]: val } : it))
  }
  function addExtra() { setExtras(e => [...e, { cost_type: 'other', amount_irr: '', description: '' }]) }

  function handleSubmit() {
    if (!hdr.supplier_id) return setMsg({ type: 'error', text: 'تامین‌کننده الزامی است' })
    if (!hdr.date) return setMsg({ type: 'error', text: 'تاریخ سفارش الزامی است' })
    if (!hdr.warehouse_id) return setMsg({ type: 'error', text: ptype === 'domestic' ? 'انبار را انتخاب کنید' : 'انبار در راه را انتخاب کنید' })

    // خرید داخلی — فاکتور ساده ریالی، رسید مستقیم بدون «منتظر رسیدن»
    if (ptype === 'domestic' && !editing) {
      // ردیف‌های کاملاً خالی (مثل ردیف خودکار Enter) نادیده گرفته می‌شوند
      const filled = items.filter(it => it.variant_id || it.quantity || it.unit_price_irr)
      if (!filled.length) return setMsg({ type: 'error', text: 'حداقل یک قلم کالا وارد کنید' })
      if (filled.some(it => !it.variant_id || !it.quantity || !it.unit_price_irr)) {
        return setMsg({ type: 'error', text: 'تمام اقلام: کالا، تعداد و قیمت ریالی الزامی است' })
      }
      createMut.mutate({
        purchase_type: 'domestic',
        supplier_id: hdr.supplier_id,
        invoice_number: hdr.invoice_number,
        date: hdr.date,
        warehouse_id: hdr.warehouse_id,
        note: hdr.note,
        items: filled.map(it => ({
          variant_id: it.variant_id,
          quantity: it.quantity,
          unit_price_irr: it.unit_price_irr,
          note: it.note || '',
        })),
      })
      return
    }

    if (!hdr.rate_purchase_cny) return setMsg({ type: 'error', text: 'نرخ یوان خرید الزامی است' })

    if (!editing) {
      // ردیف‌های کاملاً خالی (مثل ردیف خودکار Enter) نادیده گرفته می‌شوند
      const filled = items.filter(it => it.variant_id || it.quantity || it.unit_price_cny)
      if (!filled.length) return setMsg({ type: 'error', text: 'حداقل یک قلم کالا وارد کنید' })
      if (filled.some(it => !it.variant_id || !it.quantity || !it.unit_price_cny)) {
        return setMsg({ type: 'error', text: 'تمام اقلام: کالا، تعداد و قیمت یوان الزامی است' })
      }
      createMut.mutate({
        supplier_id: hdr.supplier_id,
        invoice_number: hdr.invoice_number,
        date: hdr.date,
        warehouse_id: hdr.warehouse_id,
        shipping_contact_id: hdr.shipping_contact_id,
        rate_purchase_cny: hdr.rate_purchase_cny,
        note: hdr.note,
        items: filled,
      })
      return
    }

    const payload = {
      supplier_id: hdr.supplier_id,
      invoice_number: hdr.invoice_number,
      date: hdr.date,
      warehouse_id: hdr.warehouse_id,
      warehouse_destination_id: hdr.warehouse_destination_id || null,
      shipping_contact_id: hdr.shipping_contact_id || null,
      rate_purchase_cny: hdr.rate_purchase_cny,
      rate_shipping_cny: hdr.rate_shipping_cny || 0,
      shipping_cost_cny: hdr.shipping_cost_cny || 0,
      clearance_cost_irr: hdr.clearance_cost_irr || 0,
      note: hdr.note,
    }
    if (itemsEditable) {
      if (ptype === 'domestic') {
        if (items.some(it => !it.variant_id || !it.quantity || !it.unit_price_irr)) {
          return setMsg({ type: 'error', text: 'تمام اقلام: کالا، تعداد و قیمت ریالی الزامی است' })
        }
      } else if (items.some(it => !it.variant_id || !it.quantity || !it.unit_price_cny)) {
        return setMsg({ type: 'error', text: 'تمام اقلام: کالا، تعداد و قیمت یوان الزامی است' })
      }
      payload.items = items.map(it => ({
        variant_id: it.variant_id,
        quantity: it.quantity,
        carton_count: it.carton_count || 1,
        carton_weight: it.carton_weight || 0,
        unit_price_cny: it.unit_price_cny || 0,
        unit_price_irr: it.unit_price_irr || 0,
        note: it.note || '',
      }))
      payload.extra_costs = extras.filter(e => e.amount_irr)
    }
    createMut.mutate(payload)
  }

  if (editing && editLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>

  return (
    <div className="space-y-5">
      {/* ساخت سریع طرف حساب — تامین‌کننده / شرکت حمل (مثل فاکتور فروش) */}
      {quickAdd === 'supplier' && (
        <AddContactModal
          creatableTypes={['supplier_cn']}
          onClose={() => setQuickAdd(null)}
          onCreated={c => { qc.invalidateQueries(['contacts']); setHdr(h => ({ ...h, supplier_id: c.id })); setQuickAdd(null) }}
        />
      )}
      {quickAdd === 'shipper' && (
        <AddContactModal
          creatableTypes={['shipping_co']}
          onClose={() => setQuickAdd(null)}
          onCreated={c => { qc.invalidateQueries(['contacts']); setHdr(h => ({ ...h, shipping_contact_id: c.id })); setQuickAdd(null) }}
        />
      )}
      {editing ? (
        <div className="bg-brand/10 border border-brand/30 rounded-xl p-4">
          <div className="text-brand text-sm font-bold mb-1">✏️ ویرایش فاکتور {editInv?.invoice_number || `#${editing}`}</div>
          <div className="text-xs text-gray-steel">
            وضعیت فعلی: <span className="text-white">{editInv?.status_display}</span>
            {!itemsEditable && <> — آیتم‌ها فقط در وضعیت «سفارش داده شده» قابل ویرایش هستند</>}
          </div>
        </div>
      ) : (
        <div>
          {/* انتخاب نوع خرید — خارجی (دو مرحله‌ای با انبار در راه) | داخلی (رسید مستقیم) */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            {[
              ['domestic', '🇮🇷 خرید داخلی', 'رسید مستقیم به انبار — بدون منتظر رسیدن'],
              ['foreign', '🌏 خرید خارجی (چین)', 'دو مرحله‌ای: انبار در راه ← منتظر رسیدن'],
            ].map(([k, label, desc]) => (
              <button key={k} type="button" onClick={() => setPtype(k)}
                className={`text-right rounded-xl border p-3 transition-all ${
                  ptype === k ? 'border-brand bg-brand/10' : 'border-white/10 hover:border-white/30'
                }`}>
                <div className={`text-xs font-bold ${ptype === k ? 'text-brand' : 'text-white'}`}>{label}</div>
                <div className="text-[10px] text-gray-steel mt-0.5">{desc}</div>
              </button>
            ))}
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
            {ptype === 'foreign' ? (
              <div className="text-xs text-gray-steel leading-6">
                <span className="text-yellow-400 font-bold">📦 مرحله ۱: ثبت سفارش</span> — اطلاعات خرید و شرکت حمل را وارد کنید. موجودی به انبار «در راه» اضافه می‌شود.
                هزینه حمل/ترخیص و وزن دقیق کارتن‌ها وقتی کالا رسید وارد می‌شود.
              </div>
            ) : (
              <div className="text-xs text-gray-steel leading-6">
                <span className="text-yellow-400 font-bold">🇮🇷 خرید داخلی</span> — قیمت‌ها به ریال است. با ثبت فاکتور، موجودی <b>بلافاصله</b> به انبار اضافه می‌شود و فاکتور «رسیده» می‌شود.
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">اطلاعات سفارش</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label text-xs block">تامین‌کننده *</label>
              {canQuickAdd('supplier_cn') && (
                <button type="button" onClick={() => setQuickAdd('supplier')}
                  className="text-xs text-brand hover:text-brand/80 font-semibold">+ طرف حساب جدید</button>
              )}
            </div>
            <SearchSelect
              options={suppliers.map(c => ({ value: c.id, label: c.name, sub: [c.contact_type_display, c.phone].filter(Boolean).join(' — ') }))}
              value={hdr.supplier_id}
              onChange={v => setHdr(h => ({ ...h, supplier_id: v }))}
              placeholder="جستجو و انتخاب طرف حساب..."
              flow="pi"
            />
          </div>
          {ptype === 'foreign' && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="label text-xs block">شرکت حمل</label>
                {canQuickAdd('shipping_co') && (
                  <button type="button" onClick={() => setQuickAdd('shipper')}
                    className="text-xs text-brand hover:text-brand/80 font-semibold">+ طرف حساب جدید</button>
                )}
              </div>
              <SearchSelect
                options={shippers.map(c => ({ value: c.id, label: c.name, sub: c.phone }))}
                value={hdr.shipping_contact_id}
                onChange={v => setHdr(h => ({ ...h, shipping_contact_id: v }))}
                placeholder="جستجو (اختیاری)..."
                flow="pi"
              />
            </div>
          )}
          <div>
            <label className="label text-xs mb-1 block">تاریخ سفارش *</label>
            <JalaliDateInput value={hdr.date}
              onChange={v => setHdr(h => ({ ...h, date: v }))} />
          </div>
          {ptype === 'foreign' && (
            <div>
              <label className="label text-xs mb-1 block">نرخ یوان خرید (ریال) *</label>
              <AmountInput value={hdr.rate_purchase_cny} onChange={e => setHdr(h => ({ ...h, rate_purchase_cny: e.target.value }))}
                className="input text-sm" placeholder="مثلاً 27000"
                data-flow="pi"
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); advanceFlow('pi', e.target) } }} />
            </div>
          )}
          {editing && (
            <>
              <div>
                <label className="label text-xs mb-1 block">نرخ یوان حمل (ریال)</label>
                <AmountInput value={hdr.rate_shipping_cny} onChange={e => setHdr(h => ({ ...h, rate_shipping_cny: e.target.value }))} className="input text-sm" placeholder="مثلاً 28000" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">هزینه حمل کل (یوان)</label>
                <AmountInput value={hdr.shipping_cost_cny} onChange={e => setHdr(h => ({ ...h, shipping_cost_cny: e.target.value }))} className="input text-sm" placeholder="0" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">هزینه ترخیص کل (ریال)</label>
                <AmountInput value={hdr.clearance_cost_irr} onChange={e => setHdr(h => ({ ...h, clearance_cost_irr: e.target.value }))} className="input text-sm" placeholder="0" />
              </div>
            </>
          )}
          <div>
            <label className="label text-xs mb-1 block">{ptype === 'domestic' ? 'انبار *' : 'انبار در راه *'}</label>
            <select value={hdr.warehouse_id} data-flow="pi"
              onChange={e => { setHdr(h => ({ ...h, warehouse_id: e.target.value })); advanceFlow('pi', e.target) }}
              className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {ptype === 'foreign' && transitWarehouses.length > 0 && (
                <optgroup label="در راه">
                  {transitWarehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </optgroup>
              )}
              {otherWarehouses.length > 0 && (
                <optgroup label={ptype === 'domestic' ? 'انبارها' : 'سایر انبارها'}>
                  {otherWarehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </optgroup>
              )}
            </select>
          </div>
          {editing && (
            <div>
              <label className="label text-xs mb-1 block">انبار مقصد</label>
              <select value={hdr.warehouse_destination_id} onChange={e => setHdr(h => ({ ...h, warehouse_destination_id: e.target.value }))} className="input text-sm">
                <option value="">انتخاب کنید (اختیاری)...</option>
                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="label text-xs mb-1 block">شماره فاکتور</label>
            <input value={hdr.invoice_number} onChange={e => setHdr(h => ({ ...h, invoice_number: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div className="col-span-1 md:col-span-3">
            <label className="label text-xs mb-1 block">توضیحات</label>
            <input value={hdr.note} onChange={e => setHdr(h => ({ ...h, note: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">اقلام سفارش</h3>
          {itemsEditable && <button onClick={addItem} className="text-xs text-brand hover:text-brand/80">+ افزودن کالا</button>}
        </div>
        {!itemsEditable && (
          <div className="text-[11px] text-yellow-400 bg-yellow-500/10 rounded-lg px-3 py-2 mb-3">
            آیتم‌ها فقط در وضعیت «سفارش داده شده» قابل ویرایش هستند
          </div>
        )}
        <div className="space-y-3">
          {items.map((item, idx) => (
            <div key={idx} className="bg-white/5 rounded-xl p-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-2">
                <div className="col-span-2 md:col-span-2">
                  <label className="label text-[10px] mb-1 block">کالا *</label>
                  {itemsEditable ? (
                    <SearchSelect
                      options={variants.map(v => ({ value: v.id, label: v.product_name, sub: v.sku }))}
                      value={item.variant_id}
                      onChange={val => updateItem(idx, 'variant_id', val)}
                      placeholder="جستجوی کالا (نام یا کد)..."
                      className="input text-xs"
                      flow="pi"
                    />
                  ) : (
                    <div className="text-xs text-white py-2">
                      {variants.find(v => String(v.id) === String(item.variant_id))?.product_name || `#${item.variant_id}`}
                      <span className="text-gray-steel"> [{variants.find(v => String(v.id) === String(item.variant_id))?.sku || ''}]</span>
                    </div>
                  )}
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">تعداد کل *</label>
                  <AmountInput value={item.quantity} data-flow="pi"
                    onChange={e => updateItem(idx, 'quantity', e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); advanceFlow('pi', e.target) } }}
                    className="input text-xs" disabled={!itemsEditable} />
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">{ptype === 'domestic' ? 'قیمت واحد (ریال) *' : 'قیمت واحد (¥) *'}</label>
                  <PriceWithLast
                    value={ptype === 'domestic' ? (item.unit_price_irr || '') : item.unit_price_cny}
                    onChange={e => updateItem(idx, ptype === 'domestic' ? 'unit_price_irr' : 'unit_price_cny', e.target.value)}
                    onEnter={(e) => {
                      // Enter روی قیمت آخرین ردیف ← ردیف جدید برای قلم بعدی ساخته می‌شود
                      if (itemsEditable && idx === items.length - 1) {
                        addItem()
                        setTimeout(() => advanceFlow('pi', e.target), 60)
                      } else {
                        advanceFlow('pi', e.target)
                      }
                    }}
                    supplierId={hdr.supplier_id}
                    variantId={item.variant_id}
                    isCny={ptype !== 'domestic'}
                    disabled={!itemsEditable}
                  />
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">قیمت کل</label>
                  <div className="input text-xs bg-brand/10 text-gold font-bold flex items-center justify-center min-h-[38px]">
                    {fmt((Number(item.quantity) || 0) * (Number(ptype === 'domestic' ? item.unit_price_irr : item.unit_price_cny) || 0))} {ptype === 'domestic' ? 'ریال' : '¥'}
                  </div>
                </div>
              </div>
              {itemsEditable && items.length > 1 && (
                <div className="flex justify-end">
                  <button onClick={() => removeItem(idx)} className="text-xs text-red-400 hover:text-red-300">× حذف</button>
                </div>
              )}
            </div>
          ))}
        </div>
        {(() => {
          const itemsTotal = items.reduce((s, it) =>
            s + (Number(it.quantity) || 0) * (Number(ptype === 'domestic' ? it.unit_price_irr : it.unit_price_cny) || 0), 0)
          const extrasTotal = extras.reduce((s, e) => s + (Number(e.amount_irr) || 0), 0)
          const rate = Number(hdr.rate_purchase_cny) || 0
          return (
            <div className="mt-4 pt-3 border-t border-white/10 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">جمع کل</span>
                <span className="text-gold font-bold text-base">
                  {fmt(itemsTotal)} {ptype === 'domestic' ? 'ریال' : '¥'}
                </span>
              </div>
              {ptype === 'foreign' && rate > 0 && itemsTotal > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-steel">معادل ریالی (نرخ {fmt(rate)})</span>
                  <span className="text-xs text-white">{fmt(itemsTotal * rate)} ریال</span>
                </div>
              )}
              {ptype === 'domestic' && extrasTotal > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-steel">جمع با هزینه‌های جانبی</span>
                  <span className="text-xs text-white">{fmt(itemsTotal + extrasTotal)} ریال</span>
                </div>
              )}
            </div>
          )
        })()}
      </div>

      {editing && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">هزینه‌های جانبی</h3>
            {itemsEditable && <button onClick={addExtra} className="text-xs text-brand hover:text-brand/80">+ افزودن</button>}
          </div>
          {!itemsEditable && (
            <div className="text-[11px] text-yellow-400 bg-yellow-500/10 rounded-lg px-3 py-2 mb-3">
              آیتم‌ها فقط در وضعیت «سفارش داده شده» قابل ویرایش هستند
            </div>
          )}
          {extras.length === 0 ? (
            <div className="text-center py-4 text-gray-steel text-xs">هزینه جانبی ثبت نشده</div>
          ) : (
            <div className="space-y-2">
              {extras.map((e, idx) => (
                <div key={idx} className="grid grid-cols-4 gap-3 bg-white/5 rounded-lg p-3">
                  <select value={e.cost_type} disabled={!itemsEditable}
                    onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, cost_type: ev.target.value } : x))} className="input text-xs">
                    {EXTRA_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                  <AmountInput value={e.amount_irr} disabled={!itemsEditable}
                    onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, amount_irr: ev.target.value } : x))}
                    className="input text-xs" placeholder="مبلغ (ریال)" />
                  <input value={e.description} disabled={!itemsEditable}
                    onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, description: ev.target.value } : x))}
                    className="input text-xs" placeholder="توضیح" />
                  {itemsEditable ? (
                    <button onClick={() => setExtras(ex => ex.filter((_, i) => i !== idx))} className="text-red-400 text-xs">× حذف</button>
                  ) : <span />}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {msg && <div className={`rounded-lg px-4 py-3 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}

      <div className="flex flex-col md:flex-row gap-3">
        <button onClick={handleSubmit} disabled={createMut.isPending} className="btn-primary flex-1 py-3 disabled:opacity-50">
          {createMut.isPending ? 'در حال ثبت...' : editing ? 'ذخیره تغییرات فاکتور' : ptype === 'domestic' ? 'ثبت فاکتور خرید داخلی' : 'ثبت سفارش خرید'}
        </button>
        <button onClick={onClose} className="btn-secondary px-6 py-3">انصراف</button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// ReceiveForm — مرحله ۲: تأیید رسیدن + انتخاب انبار مقصد
// ═══════════════════════════════════════════════════════════════
function ReceiveForm({ invoiceId, onClose, onSuccess }) {
  const { data: inv, isLoading } = useQuery({
    queryKey: ['invoice-detail', invoiceId],
    queryFn: () => api.get(`/accounting/purchase-invoices/${invoiceId}/`).then(r => r.data),
  })
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => api.get('/inventory/warehouses/').then(r => r.data),
  })
  // نرخ یوان مرجع — پیش‌پر کردن «نرخ یوان حمل»
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })

  const [hdr, setHdr] = useState({
    destination_warehouse_id: '',
    rate_shipping_cny: '',
    shipping_cost_cny: '',
    clearance_cost_irr: '',
  })
  const [itemWeights, setItemWeights] = useState({})
  const [extras, setExtras] = useState([])
  const [msg, setMsg] = useState(null)

  // وقتی نرخ مرجع رسید، نرخ یوان حمل را با آن پر کن (اگر خالی است)
  useEffect(() => {
    if (rateData?.rate_cny_to_irt) {
      setHdr(h => h.rate_shipping_cny ? h : { ...h, rate_shipping_cny: String(rateData.rate_cny_to_irt) })
    }
  }, [rateData])

  const qc = useQueryClient()
  const receiveMut = useMutation({
    mutationFn: (d) => api.post(`/accounting/purchase-invoices/${invoiceId}/receive/`, d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['purchase-invoices'])
      qc.invalidateQueries(['pending-receive'])
      qc.invalidateQueries(['variants-list'])
      onSuccess?.()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در تأیید رسیدن کالا' }),
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!inv) return null

  // انبارهای مقصد — هر چیزی غیر از انبار در راه فعلی
  const destinationWarehouses = warehouses.filter(w =>
    w.id !== inv.warehouse?.id && !TRANSIT_TYPES.includes(w.warehouse_type)
  )

  function updateItemWeight(itemId, key, val) {
    setItemWeights(w => ({ ...w, [itemId]: { ...w[itemId], [key]: val } }))
  }
  function addExtra() {
    setExtras(e => [...e, { cost_type: 'other', amount_irr: '', description: '' }])
  }

  // ── محاسبه زنده بهای تمام‌شده هر قلم — همان فرمول بک‌اند (سهم وزنی) ──
  const cartonOf = (it) => {
    const w = itemWeights[it.id] || {}
    const cw = w.carton_weight !== undefined ? Number(w.carton_weight || 0) : Number(it.carton_weight || 0)
    const cc = w.carton_count !== undefined ? Number(w.carton_count || 0) : Number(it.carton_count || 0)
    return cw * cc
  }
  const totalW = inv ? inv.items.reduce((s, it) => s + cartonOf(it), 0) : 0
  const extrasTotal = extras.reduce((s, e) => s + Number(e.amount_irr || 0), 0)
  // هزینه واحد — سهم حمل/ترخیص/جانبی به‌ازای هر واحد کالا (بدون قیمت خرید)
  const itemSideCost = (it) => {
    const ratio = totalW > 0 ? cartonOf(it) / totalW : 0
    const qty = it.quantity || 1
    const ship = (Number(hdr.shipping_cost_cny || 0) * Number(hdr.rate_shipping_cny || 0) * ratio) / qty
    const clear = (Number(hdr.clearance_cost_irr || 0) * ratio) / qty
    const extra = (extrasTotal * ratio) / qty
    return Math.round(ship + clear + extra)
  }
  const itemUnitCost = (it) =>
    Math.round(Number(it.unit_price_cny) * Number(inv.rate_purchase_cny || 0)) + itemSideCost(it)

  function handleSubmit() {
    if (!hdr.destination_warehouse_id) {
      return setMsg({ type: 'error', text: 'انبار مقصد را انتخاب کنید' })
    }
    if (!hdr.rate_shipping_cny) {
      return setMsg({ type: 'error', text: 'نرخ یوان حمل الزامی است' })
    }
    const itemsPayload = inv.items.map(it => {
      const w = itemWeights[it.id] || {}
      return {
        id: it.id,
        carton_count: w.carton_count || it.carton_count || 1,
        carton_weight: w.carton_weight !== undefined ? w.carton_weight : (it.carton_weight || 0),
      }
    })
    if (itemsPayload.some(it => !it.carton_weight || Number(it.carton_weight) <= 0)) {
      return setMsg({ type: 'error', text: 'وزن کارتن همه اقلام باید وارد شود' })
    }
    receiveMut.mutate({
      ...hdr,
      items: itemsPayload,
      extra_costs: extras.filter(e => e.amount_irr),
    })
  }

  return (
    <div className="space-y-5">
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
        <div className="text-blue-400 text-sm font-bold mb-2">📥 مرحله ۲: تأیید رسیدن کالا</div>
        <div className="text-xs text-gray-steel leading-6">
          فاکتور <span className="text-white font-bold">{inv.invoice_number || `#${inv.id}`}</span> از{' '}
          <span className="text-white">{inv.supplier?.name}</span>.
          {inv.warehouse && (
            <> در حال حاضر در: <span className="text-orange-400">{inv.warehouse.name}</span></>
          )}
          <br/>کالا را به انبار مقصد منتقل می‌کنیم و اطلاعات حمل را تکمیل می‌کنیم.
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">انبار مقصد و اطلاعات حمل</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">📦 انبار مقصد (کالا به کجا منتقل شود؟) *</label>
            <select value={hdr.destination_warehouse_id} onChange={e => setHdr(h => ({ ...h, destination_warehouse_id: e.target.value }))} className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {destinationWarehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">نرخ یوان حمل (ریال) *</label>
            <AmountInput value={hdr.rate_shipping_cny} onChange={e => setHdr(h => ({ ...h, rate_shipping_cny: e.target.value }))} className="input text-sm" placeholder="مثلاً 28000" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">هزینه حمل کل (یوان)</label>
            <AmountInput value={hdr.shipping_cost_cny} onChange={e => setHdr(h => ({ ...h, shipping_cost_cny: e.target.value }))} className="input text-sm" placeholder="0" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">هزینه ترخیص کل (ریال)</label>
            <AmountInput value={hdr.clearance_cost_irr} onChange={e => setHdr(h => ({ ...h, clearance_cost_irr: e.target.value }))} className="input text-sm" placeholder="0" />
          </div>
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">وزن نهایی کارتن‌ها *</h3>
        <div className="space-y-3">
          {inv.items.map(item => {
            const w = itemWeights[item.id] || {}
            return (
              <div key={item.id} className="bg-white/5 rounded-xl p-4">
                <div className="grid grid-cols-5 gap-3 items-center">
                  <div className="col-span-2 md:col-span-1">
                    <div className="text-xs text-white">{item.product_name}</div>
                    <div className="text-[10px] text-gray-steel">{item.variant_sku}</div>
                    <div className="text-[10px] text-gray-steel mt-0.5">
                      تعداد: <span className="text-white">{fmt(item.quantity)}</span>
                      {' | '}قیمت خرید: <span className="text-white">{fmt(item.unit_price_cny)} ¥</span>
                    </div>
                  </div>
                  <div>
                    <label className="label text-[10px] mb-1 block">تعداد کارتن</label>
                    <AmountInput
                      value={w.carton_count !== undefined ? w.carton_count : String(item.carton_count ?? '')}
                      onChange={e => updateItemWeight(item.id, 'carton_count', e.target.value)}
                      className="input text-xs" />
                  </div>
                  <div>
                    <label className="label text-[10px] mb-1 block">وزن هر کارتن (kg) *</label>
                    <AmountInput
                      value={w.carton_weight !== undefined ? w.carton_weight : String(item.carton_weight || '')}
                      onChange={e => updateItemWeight(item.id, 'carton_weight', e.target.value)}
                      className="input text-xs" placeholder="0.000" />
                  </div>
                  {/* هزینه واحد — سهم حمل/ترخیص/جانبی هر واحد */}
                  <div>
                    <label className="label text-[10px] mb-1 block">هزینه واحد</label>
                    <div className="input text-xs bg-white/5 text-blue-300 font-bold flex items-center justify-center min-h-[38px]">
                      {itemSideCost(item).toLocaleString('fa-IR')}
                    </div>
                  </div>
                  {/* قیمت تمام‌شده واحد */}
                  <div>
                    <label className="label text-[10px] mb-1 block">تمام‌شده واحد</label>
                    <div className="input text-xs bg-brand/10 text-gold font-bold flex items-center justify-center min-h-[38px]">
                      {itemUnitCost(item).toLocaleString('fa-IR')}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">هزینه‌های جانبی</h3>
          <button onClick={addExtra} className="text-xs text-brand hover:text-brand/80">+ افزودن</button>
        </div>
        {extras.length === 0 ? (
          <div className="text-center py-4 text-gray-steel text-xs">اختیاری</div>
        ) : (
          <div className="space-y-2">
            {extras.map((e, idx) => (
              <div key={idx} className="grid grid-cols-4 gap-3 bg-white/5 rounded-lg p-3">
                <select value={e.cost_type} onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, cost_type: ev.target.value } : x))} className="input text-xs">
                  {EXTRA_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <AmountInput value={e.amount_irr}
                  onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, amount_irr: ev.target.value } : x))}
                  className="input text-xs" placeholder="مبلغ (ریال)" />
                <input value={e.description}
                  onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, description: ev.target.value } : x))}
                  className="input text-xs" placeholder="توضیح" />
                <button onClick={() => setExtras(ex => ex.filter((_, i) => i !== idx))} className="text-red-400 text-xs">× حذف</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {msg && <div className={`rounded-lg px-4 py-3 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}

      <div className="flex gap-3">
        <button onClick={handleSubmit} disabled={receiveMut.isPending} className="btn-primary flex-1 py-3 disabled:opacity-50">
          {receiveMut.isPending ? 'در حال ثبت...' : '✓ تأیید رسیدن کالا و انتقال به انبار'}
        </button>
        <button onClick={onClose} className="btn-secondary px-6 py-3">انصراف</button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// PendingReceiveList
// ═══════════════════════════════════════════════════════════════
function PendingReceiveList({ onSelect }) {
  const { can } = usePermissions()
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['pending-receive'],
    queryFn: () => api.get('/accounting/purchase-invoices/pending-receive/').then(r => r.data),
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>

  if (items.length === 0) {
    return (
      <div className="card p-5 text-center py-12">
        <div className="text-4xl mb-3">✅</div>
        <div className="text-gray-steel text-sm">هیچ سفارشی در راه نیست</div>
      </div>
    )
  }

  return (
    <div className="card p-5">
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
            {['شماره', 'تامین‌کننده', 'شرکت حمل', 'انبار در راه', 'تاریخ', 'روزها', 'اقلام', 'جمع یوان', 'ثبت‌کننده', ''].map(h => (
              <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((inv, i) => (
            <tr key={inv.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
              <td style={{ padding: '10px 12px' }}>{inv.invoice_number || `#${inv.id}`}</td>
              <td style={{ padding: '10px 12px' }}>{inv.supplier_name}</td>
              <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{inv.shipping_contact_name}</td>
              <td style={{ padding: '10px 12px', color: '#FF9500', fontSize: 11 }}>{inv.warehouse_name}</td>
              <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{formatDate(inv.date)}</td>
              <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                <span style={{
                  color: inv.days_pending > 30 ? '#FF6B6B' : '#FF9500',
                  background: (inv.days_pending > 30 ? '#FF6B6B' : '#FF9500') + '20',
                  padding: '2px 8px', borderRadius: 12, fontSize: 11
                }}>{inv.days_pending} روز</span>
              </td>
              <td style={{ padding: '10px 12px', textAlign: 'center' }}>{inv.items_count}</td>
              <td style={{ padding: '10px 12px', color: '#0066FF' }}>{fmt(inv.total_cny)} ¥</td>
              <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                <UserStamp createdBy={inv.created_by} createdAt={inv.created_at} />
              </td>
              <td style={{ padding: '10px 12px' }}>
                {can('purchase_edit') && (
                  <button onClick={() => onSelect(inv.id)} className="btn-primary text-[11px] px-3 py-1">
                    📥 تأیید رسیدن
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// PurchaseInvoicePage — صفحه اصلی
// ═══════════════════════════════════════════════════════════════
export default function PurchaseInvoicePage() {
  const [view, setView] = useState('list')
  const [selectedId, setSelectedId] = useState(null)
  const { can } = usePermissions()

  // با هر تغییر نما (ورود/خروج از فرم) به بالای صفحه برگرد
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [view])

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['purchase-invoices'],
    queryFn: () => api.get('/accounting/purchase-invoices/').then(r => r.data),
    enabled: view === 'list',
  })

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          {view !== 'list' && view !== 'pending' && (
            <button onClick={() => setView('list')} className="text-gray-steel hover:text-white text-sm">← برگشت</button>
          )}
          <h1 className="font-display font-bold text-xl md:text-2xl text-white">
            {view === 'list' ? 'فاکتورهای خرید'
              : view === 'pending' ? 'منتظر رسیدن کالا'
              : view === 'new' ? 'سفارش خرید جدید'
              : view === 'receive' ? 'تأیید رسیدن کالا'
              : view === 'edit' ? 'ویرایش فاکتور'
              : 'جزئیات فاکتور'}
          </h1>
        </div>

        {(view === 'list' || view === 'pending') && (
          <div className="flex items-center gap-2">
            <button onClick={() => setView(view === 'list' ? 'pending' : 'list')}
              className="btn-secondary text-sm px-3 py-2 flex-1 md:flex-none">
              {view === 'list' ? '📥 منتظر رسیدن' : '📋 همه فاکتورها'}
            </button>
            {can('purchase_create') && (
              <button onClick={() => setView('new')} className="btn-primary text-sm px-4 py-2 flex-1 md:flex-none">+ سفارش جدید</button>
            )}
          </div>
        )}
      </div>

      {view === 'list' && (
        <div className="card p-5">
          {isLoading ? (
            <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
          ) : invoices.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-3">📦</div>
              <div className="text-gray-steel text-sm mb-4">هنوز فاکتوری ثبت نشده</div>
              {can('purchase_create') && (
                <button onClick={() => setView('new')} className="btn-primary text-sm px-6 py-2">+ ثبت اولین سفارش</button>
              )}
            </div>
          ) : (
            <>
              {/* ─── Desktop: Table ─── */}
              <div className="hidden md:block">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['شماره', 'تامین‌کننده', 'انبار', 'تاریخ', 'وضعیت', 'اقلام', 'جمع یوان', 'جمع ریال', 'ثبت‌کننده', ''].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv, i) => (
                      <tr key={inv.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                        <td style={{ padding: '10px 12px' }}>{inv.invoice_number || `#${inv.id}`}</td>
                        <td style={{ padding: '10px 12px' }}>{inv.supplier_name}</td>
                        <td style={{ padding: '10px 12px', fontSize: 11 }}>
                          <div className="text-orange-400">{inv.warehouse_name}</div>
                          {inv.status === 'received' && inv.warehouse_destination_name !== '—' && (
                            <div className="text-green-400 text-[10px]">→ {inv.warehouse_destination_name}</div>
                          )}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{formatDate(inv.date)}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{
                            color: STATUS_COLORS[inv.status] || '#888',
                            background: (STATUS_COLORS[inv.status] || '#888') + '20',
                            padding: '2px 8px', borderRadius: 20, fontSize: 11
                          }}>{inv.status_display}</span>
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>{inv.items_count}</td>
                        <td style={{ padding: '10px 12px', color: '#0066FF' }}>{fmt(inv.total_cny)} ¥</td>
                        <td style={{ padding: '10px 12px', color: '#00C896' }}>{fmt(inv.total_irr)} ریال</td>
                        <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                          <UserStamp createdBy={inv.created_by} updatedBy={inv.updated_by} createdAt={inv.created_at} updatedAt={inv.updated_at} />
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <div className="flex gap-2">
                            <button onClick={() => { setSelectedId(inv.id); setView('detail') }}
                              className="text-xs text-brand hover:text-brand/80">مشاهده</button>
                            {inv.status === 'ordered' && can('purchase_edit') && (
                              <button onClick={() => { setSelectedId(inv.id); setView('receive') }}
                                className="text-xs text-orange-400 hover:text-orange-300">تأیید رسیدن</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* ─── Mobile: Card List ─── */}
              <div className="md:hidden space-y-3">
                {invoices.map((inv) => (
                  <div key={inv.id} className="rounded-xl p-4" style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{inv.invoice_number || `#${inv.id}`}</span>
                        <span style={{
                          color: STATUS_COLORS[inv.status] || '#888',
                          background: (STATUS_COLORS[inv.status] || '#888') + '20',
                          padding: '1px 8px', borderRadius: 20, fontSize: 10
                        }}>{inv.status_display}</span>
                      </div>
                      <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{formatDate(inv.date)}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs mb-3" style={{ color: 'var(--color-text-secondary)' }}>
                      <div>🏢 {inv.supplier_name}</div>
                      <div>📦 {inv.warehouse_name}</div>
                      <div>💰 <span style={{ color: '#0066FF' }}>{fmt(inv.total_cny)} ¥</span></div>
                      <div>💵 <span style={{ color: '#00C896' }}>{fmt(inv.total_irr)} ریال</span></div>
                    </div>
                    <div className="flex items-center justify-between pt-2" style={{ borderTop: '1px solid var(--color-border)' }}>
                      <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{inv.items_count} قلم</span>
                      <div className="flex gap-2">
                        <button onClick={() => { setSelectedId(inv.id); setView('detail') }}
                          className="text-xs px-3 py-1.5 rounded-lg" style={{ background: 'rgba(34,211,238,0.15)', color: 'var(--color-brand)' }}>مشاهده</button>
                        {inv.status === 'ordered' && can('purchase_edit') && (
                          <button onClick={() => { setSelectedId(inv.id); setView('receive') }}
                            className="text-xs px-3 py-1.5 rounded-lg" style={{ background: 'rgba(255,165,0,0.15)', color: '#ffa500' }}>تأیید رسیدن</button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {view === 'pending' && (
        <PendingReceiveList onSelect={(id) => { setSelectedId(id); setView('receive') }} />
      )}

      {view === 'new' && (
        <NewInvoiceForm
          onClose={() => setView('list')}
          onSuccess={() => setView('list')}
        />
      )}

      {view === 'receive' && selectedId && (
        <ReceiveForm
          invoiceId={selectedId}
          onClose={() => setView('pending')}
          onSuccess={() => setView('list')}
        />
      )}

      {view === 'edit' && selectedId && (
        <NewInvoiceForm
          editing={selectedId}
          onClose={() => setView('detail')}
          onSuccess={() => setView('detail')}
        />
      )}

      {view === 'detail' && selectedId && (
        <InvoiceDetail id={selectedId} onClose={() => setView('list')} onEdit={() => setView('edit')} />
      )}
    </div>
  )
}
