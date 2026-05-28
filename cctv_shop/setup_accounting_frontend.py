"""
python setup_accounting_frontend.py
ساخت همه فایل‌های فرانت‌اند accounting
اجرا در پوشه cctv_shop
"""
import os

FRONTEND = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "cctv_frontend", "src"
)

pages_admin = os.path.join(FRONTEND, "pages", "admin")
os.makedirs(pages_admin, exist_ok=True)

# ─── 1. ContactsPage.jsx ─────────────────────────────────────
contacts_jsx = r"""import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

const TYPE_LABELS = {
  supplier_cn: 'تامین‌کننده چینی',
  clearance: 'ترخیص‌کار',
  shipping_co: 'شرکت حمل',
  staff: 'کارمند / فروشنده',
  other: 'سایر',
}
const TYPE_COLORS = {
  supplier_cn: '#0066FF',
  clearance: '#FF9500',
  shipping_co: '#00C896',
  staff: '#8B5CF6',
  other: '#888',
}

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function ContactsPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [selected, setSelected] = useState(null)
  const [filterType, setFilterType] = useState('')
  const [form, setForm] = useState({ name: '', contact_type: 'supplier_cn', currency: 'CNY', phone: '', wechat: '', note: '' })
  const [msg, setMsg] = useState(null)

  const { data: contacts = [], isLoading } = useQuery({
    queryKey: ['contacts', filterType],
    queryFn: () => api.get('/accounting/contacts/', { params: filterType ? { type: filterType } : {} }).then(r => r.data),
  })

  const { data: detail } = useQuery({
    queryKey: ['contact-detail', selected],
    queryFn: () => api.get(`/accounting/contacts/${selected}/`).then(r => r.data),
    enabled: !!selected,
  })

  const createMut = useMutation({
    mutationFn: (d) => api.post('/accounting/contacts/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['contacts'])
      setMsg({ type: 'success', text: 'طرف حساب اضافه شد' })
      setForm({ name: '', contact_type: 'supplier_cn', currency: 'CNY', phone: '', wechat: '', note: '' })
      setTimeout(() => { setMsg(null); setShowForm(false) }, 1500)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const filtered = filterType ? contacts.filter(c => c.contact_type === filterType) : contacts

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">طرف حساب‌ها</h1>
        <button onClick={() => setShowForm(true)} className="btn-primary text-sm px-4 py-2">+ افزودن طرف حساب</button>
      </div>

      {/* فیلتر نوع */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {[['', 'همه'], ...Object.entries(TYPE_LABELS)].map(([k, v]) => (
          <button key={k} onClick={() => setFilterType(k)}
            className={`text-xs px-4 py-2 rounded-full border transition-all ${filterType === k ? 'bg-brand border-brand text-white' : 'border-white/10 text-gray-steel hover:border-white/30'}`}>
            {v}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* لیست */}
        <div className="col-span-1 space-y-2">
          {isLoading && <div className="text-gray-steel text-sm text-center py-8">در حال بارگذاری...</div>}
          {filtered.map(c => (
            <div key={c.id} onClick={() => setSelected(c.id)}
              className={`card p-4 cursor-pointer transition-all ${selected === c.id ? 'border border-brand/40 bg-brand/10' : 'hover:bg-white/5'}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="font-semibold text-sm text-white">{c.name}</div>
                <span style={{ color: TYPE_COLORS[c.contact_type], background: TYPE_COLORS[c.contact_type] + '20' }}
                  className="text-[10px] px-2 py-0.5 rounded-full">{c.contact_type_display}</span>
              </div>
              <div className="flex gap-4 mt-2">
                <div className={`text-xs ${c.balance_irr > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  {c.balance_irr > 0 ? 'بدهکار: ' : 'بستانکار: '}{fmt(Math.abs(c.balance_irr))} ت
                </div>
                {c.balance_cny !== 0 && (
                  <div className={`text-xs ${c.balance_cny > 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {fmt(Math.abs(c.balance_cny))} ¥
                  </div>
                )}
              </div>
            </div>
          ))}
          {!isLoading && filtered.length === 0 && (
            <div className="text-center py-12 text-gray-steel text-sm">طرف حسابی یافت نشد</div>
          )}
        </div>

        {/* جزئیات */}
        <div className="col-span-2">
          {selected && detail ? (
            <div className="space-y-4">
              <div className="card p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-bold text-white text-lg">{detail.name}</h2>
                    <div className="text-xs text-gray-steel mt-1">{detail.contact_type_display} | ارز: {detail.currency}</div>
                    {detail.phone && <div className="text-xs text-gray-steel mt-1">📞 {detail.phone}</div>}
                    {detail.wechat && <div className="text-xs text-gray-steel mt-0.5">💬 {detail.wechat}</div>}
                  </div>
                  <div className="text-left">
                    <div className={`text-lg font-bold ${detail.balance_irr > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {detail.balance_irr > 0 ? 'بدهکار' : 'بستانکار'}
                    </div>
                    <div className="text-sm text-white">{fmt(Math.abs(detail.balance_irr))} ریال</div>
                    {detail.balance_cny !== 0 && (
                      <div className="text-xs text-gray-steel">{fmt(Math.abs(detail.balance_cny))} یوان</div>
                    )}
                  </div>
                </div>
              </div>

              {/* فاکتورها */}
              {detail.invoices?.length > 0 && (
                <div className="card p-4">
                  <h3 className="text-sm font-semibold text-white mb-3">فاکتورهای خرید</h3>
                  <div className="space-y-2">
                    {detail.invoices.map(inv => (
                      <div key={inv.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
                        <div>
                          <div className="text-xs text-white">{inv.invoice_number || `#${inv.id}`}</div>
                          <div className="text-[10px] text-gray-steel">{inv.date}</div>
                        </div>
                        <div className="text-left">
                          <div className="text-xs text-white">{fmt(inv.total_irr)} ت</div>
                          <span className="text-[10px] text-gray-steel">{inv.status_display}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* پرداخت‌ها */}
              {detail.payments?.length > 0 && (
                <div className="card p-4">
                  <h3 className="text-sm font-semibold text-white mb-3">تاریخچه پرداخت‌ها</h3>
                  <div className="space-y-2">
                    {detail.payments.map(p => (
                      <div key={p.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
                        <div>
                          <div className="text-xs text-white">{p.payment_type_display}</div>
                          <div className="text-[10px] text-gray-steel">{p.date} {p.reference && `| ${p.reference}`}</div>
                        </div>
                        <div className={`text-sm font-bold ${p.direction === 'out' ? 'text-red-400' : 'text-green-400'}`}>
                          {p.direction === 'out' ? '-' : '+'}{fmt(p.amount)} {p.currency}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card p-12 text-center">
              <div className="text-4xl mb-3">👤</div>
              <div className="text-gray-steel text-sm">یک طرف حساب را انتخاب کنید</div>
            </div>
          )}
        </div>
      </div>

      {/* مودال افزودن */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="card p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-white text-lg">افزودن طرف حساب</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-steel hover:text-white text-2xl">×</button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="label text-xs mb-1 block">نام *</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="input text-sm" placeholder="نام طرف حساب" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">نوع *</label>
                <select value={form.contact_type} onChange={e => setForm(f => ({ ...f, contact_type: e.target.value }))} className="input text-sm">
                  {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="label text-xs mb-1 block">ارز پیش‌فرض</label>
                <select value={form.currency} onChange={e => setForm(f => ({ ...f, currency: e.target.value }))} className="input text-sm">
                  <option value="CNY">یوان چین (CNY)</option>
                  <option value="IRR">ریال ایران (IRR)</option>
                  <option value="USD">دلار (USD)</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label text-xs mb-1 block">تلفن</label>
                  <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                    className="input text-sm" placeholder="اختیاری" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">وی‌چت / واتساپ</label>
                  <input value={form.wechat} onChange={e => setForm(f => ({ ...f, wechat: e.target.value }))}
                    className="input text-sm" placeholder="اختیاری" />
                </div>
              </div>
              <div>
                <label className="label text-xs mb-1 block">توضیحات</label>
                <textarea value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                  className="input text-sm resize-none" rows={2} />
              </div>
            </div>
            {msg && (
              <div className={`mt-3 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                {msg.text}
              </div>
            )}
            <div className="flex gap-3 mt-5">
              <button onClick={() => createMut.mutate(form)} disabled={!form.name || createMut.isPending}
                className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
                {createMut.isPending ? 'در حال ذخیره...' : 'ذخیره'}
              </button>
              <button onClick={() => setShowForm(false)} className="btn-secondary text-sm py-2.5 px-5">انصراف</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
"""

# ─── 2. PurchaseInvoicePage.jsx ──────────────────────────────
invoice_jsx = r"""import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_COLORS = {
  draft: '#888', confirmed: '#0066FF', received: '#FF9500', paid: '#00C896',
}
const EXTRA_TYPES = [
  { value: 'rent', label: 'اجاره' },
  { value: 'delivery', label: 'پیک / ارسال' },
  { value: 'commission', label: 'پورسانت' },
  { value: 'electricity', label: 'برق' },
  { value: 'insurance', label: 'بیمه' },
  { value: 'other', label: 'سایر' },
]

function InvoiceDetail({ id, onClose }) {
  const { data: inv, isLoading } = useQuery({
    queryKey: ['invoice-detail', id],
    queryFn: () => api.get(`/accounting/invoices/${id}/`).then(r => r.data),
  })
  const qc = useQueryClient()

  const payMut = useMutation({
    mutationFn: (d) => api.post('/accounting/payments/', d).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(['invoice-detail', id]); qc.invalidateQueries(['invoices']) },
  })

  const [payForm, setPayForm] = useState({ show: false, direction: 'out', payment_type: 'transfer', currency: 'CNY', amount: '', rate_irr: '', date: new Date().toISOString().split('T')[0], reference: '' })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!inv) return null

  return (
    <div className="space-y-4">
      {/* هدر */}
      <div className="card p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-bold text-white text-lg">فاکتور {inv.invoice_number || `#${inv.id}`}</h2>
            <div className="text-xs text-gray-steel mt-1">{inv.supplier?.name} | {inv.date}</div>
          </div>
          <div className="flex items-center gap-3">
            <span style={{ color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20' }}
              className="text-xs px-3 py-1 rounded-full">{inv.status_display}</span>
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
            <div className="text-sm font-bold text-white">{fmt(inv.rate_shipping_cny)}</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-steel mb-1">جمع یوان</div>
            <div className="text-sm font-bold text-blue-400">{fmt(inv.total_cny)} ¥</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-steel mb-1">جمع ریال</div>
            <div className="text-sm font-bold text-green-400">{fmt(inv.total_irr)} ت</div>
          </div>
        </div>
      </div>

      {/* آیتم‌ها */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-3">اقلام فاکتور (وزن کل: {inv.total_weight} kg)</h3>
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
                  <td style={{ padding: '8px 10px', textAlign: 'center' }}>{item.total_weight}</td>
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

      {/* پرداخت‌ها */}
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
                <input type="number" value={payForm.amount} onChange={e => setPayForm(f => ({ ...f, amount: e.target.value }))} className="input text-xs" />
              </div>
              {payForm.currency !== 'IRR' && (
                <div>
                  <label className="label text-xs mb-1 block">نرخ تبدیل (ریال)</label>
                  <input type="number" value={payForm.rate_irr} onChange={e => setPayForm(f => ({ ...f, rate_irr: e.target.value }))} className="input text-xs" />
                </div>
              )}
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <input type="date" value={payForm.date} onChange={e => setPayForm(f => ({ ...f, date: e.target.value }))} className="input text-xs" />
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
                <label className="label text-xs mb-1 block">مرجع / شماره حواله</label>
                <input value={payForm.reference} onChange={e => setPayForm(f => ({ ...f, reference: e.target.value }))} className="input text-xs" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => {
                payMut.mutate({ contact_id: inv.supplier.id, invoice_id: id, direction: 'out', ...payForm })
                setPayForm(f => ({ ...f, show: false, amount: '', reference: '' }))
              }} className="btn-primary text-xs px-4 py-2">ثبت</button>
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
                  <div className="text-xs text-white">{p.payment_type_display} | {p.date}</div>
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

function NewInvoiceForm({ onClose, onSuccess }) {
  const { data: contacts = [] } = useQuery({ queryKey: ['contacts'], queryFn: () => api.get('/accounting/contacts/').then(r => r.data) })
  const { data: variants = [] } = useQuery({ queryKey: ['variants-list'], queryFn: () => api.get('/catalog/variants/').then(r => r.data) })
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: () => api.get('/inventory/warehouses/').then(r => r.data) })

  const [hdr, setHdr] = useState({
    supplier_id: '', invoice_number: '', date: new Date().toISOString().split('T')[0],
    warehouse_id: '', rate_purchase_cny: '', rate_shipping_cny: '',
    shipping_contact_id: '', shipping_cost_cny: '', clearance_cost_irr: '', note: '',
  })
  const [items, setItems] = useState([{ variant_id: '', quantity: '', carton_count: '', carton_weight: '', unit_price_cny: '', note: '' }])
  const [extras, setExtras] = useState([])
  const [msg, setMsg] = useState(null)
  const [varSearch, setVarSearch] = useState({})

  const qc = useQueryClient()
  const createMut = useMutation({
    mutationFn: (d) => api.post('/accounting/invoices/', d).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(['invoices']); onSuccess?.() },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت' }),
  })

  const suppliers = contacts.filter(c => ['supplier_cn', 'other'].includes(c.contact_type))
  const shippers = contacts.filter(c => ['clearance', 'shipping_co'].includes(c.contact_type))

  function addItem() { setItems(i => [...i, { variant_id: '', quantity: '', carton_count: '', carton_weight: '', unit_price_cny: '', note: '' }]) }
  function removeItem(idx) { setItems(i => i.filter((_, j) => j !== idx)) }
  function updateItem(idx, key, val) { setItems(i => i.map((it, j) => j === idx ? { ...it, [key]: val } : it)) }
  function addExtra() { setExtras(e => [...e, { cost_type: 'other', contact_id: '', amount_irr: '', description: '' }]) }

  // محاسبه زنده بهای تمام شده
  function calcCost(item) {
    const qty = Number(item.quantity) || 0
    const boxes = Number(item.carton_count) || 0
    const boxW = Number(item.carton_weight) || 0
    const price = Number(item.unit_price_cny) || 0
    const rateP = Number(hdr.rate_purchase_cny) || 0
    const rateS = Number(hdr.rate_shipping_cny) || 0
    const shipCny = Number(hdr.shipping_cost_cny) || 0
    const clearIrr = Number(hdr.clearance_cost_irr) || 0

    const totalW = items.reduce((s, it) => s + (Number(it.carton_count) || 0) * (Number(it.carton_weight) || 0), 0)
    const myW = boxes * boxW
    const ratio = totalW > 0 ? myW / totalW : 0

    const purchaseIrr = price * rateP
    const shipShare = qty > 0 ? (shipCny * rateS * ratio) / qty : 0
    const clearShare = qty > 0 ? (clearIrr * ratio) / qty : 0
    return Math.round(purchaseIrr + shipShare + clearShare)
  }

  function handleSubmit() {
    if (!hdr.supplier_id || !hdr.date || !hdr.rate_purchase_cny) return setMsg({ type: 'error', text: 'تامین‌کننده، تاریخ و نرخ خرید الزامی است' })
    if (items.some(it => !it.variant_id || !it.quantity || !it.unit_price_cny)) return setMsg({ type: 'error', text: 'اطلاعات تمام اقلام را کامل کنید' })
    createMut.mutate({ ...hdr, items, extra_costs: extras })
  }

  return (
    <div className="space-y-5">
      {/* هدر فاکتور */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">اطلاعات کلی فاکتور</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="label text-xs mb-1 block">تامین‌کننده *</label>
            <select value={hdr.supplier_id} onChange={e => setHdr(h => ({ ...h, supplier_id: e.target.value }))} className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {suppliers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">شماره فاکتور</label>
            <input value={hdr.invoice_number} onChange={e => setHdr(h => ({ ...h, invoice_number: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">تاریخ *</label>
            <input type="date" value={hdr.date} onChange={e => setHdr(h => ({ ...h, date: e.target.value }))} className="input text-sm" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">نرخ یوان خرید (تومان) *</label>
            <input type="number" value={hdr.rate_purchase_cny} onChange={e => setHdr(h => ({ ...h, rate_purchase_cny: e.target.value }))} className="input text-sm" placeholder="مثلاً 27000" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">نرخ یوان حمل (تومان) *</label>
            <input type="number" value={hdr.rate_shipping_cny} onChange={e => setHdr(h => ({ ...h, rate_shipping_cny: e.target.value }))} className="input text-sm" placeholder="مثلاً 27000" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">انبار مقصد</label>
            <select value={hdr.warehouse_id} onChange={e => setHdr(h => ({ ...h, warehouse_id: e.target.value }))} className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">شرکت حمل / ترخیص‌کار</label>
            <select value={hdr.shipping_contact_id} onChange={e => setHdr(h => ({ ...h, shipping_contact_id: e.target.value }))} className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {shippers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">هزینه حمل کل (یوان)</label>
            <input type="number" value={hdr.shipping_cost_cny} onChange={e => setHdr(h => ({ ...h, shipping_cost_cny: e.target.value }))} className="input text-sm" placeholder="0" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">هزینه ترخیص کل (ریال)</label>
            <input type="number" value={hdr.clearance_cost_irr} onChange={e => setHdr(h => ({ ...h, clearance_cost_irr: e.target.value }))} className="input text-sm" placeholder="0" />
          </div>
        </div>
        <div className="mt-3">
          <label className="label text-xs mb-1 block">توضیحات</label>
          <input value={hdr.note} onChange={e => setHdr(h => ({ ...h, note: e.target.value }))} className="input text-sm" />
        </div>
      </div>

      {/* اقلام */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">اقلام فاکتور (پکینگ لیست)</h3>
          <button onClick={addItem} className="text-xs text-brand hover:text-brand/80">+ افزودن کالا</button>
        </div>
        <div className="space-y-3">
          {items.map((item, idx) => (
            <div key={idx} className="bg-white/5 rounded-xl p-4">
              <div className="grid grid-cols-6 gap-3 mb-2">
                <div className="col-span-2">
                  <label className="label text-[10px] mb-1 block">کالا *</label>
                  <select value={item.variant_id} onChange={e => updateItem(idx, 'variant_id', e.target.value)} className="input text-xs">
                    <option value="">انتخاب کالا...</option>
                    {variants.map(v => <option key={v.id} value={v.id}>{v.product_name} [{v.sku}]</option>)}
                  </select>
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">تعداد کل *</label>
                  <input type="number" value={item.quantity} onChange={e => updateItem(idx, 'quantity', e.target.value)} className="input text-xs" />
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">تعداد کارتن</label>
                  <input type="number" value={item.carton_count} onChange={e => updateItem(idx, 'carton_count', e.target.value)} className="input text-xs" />
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">وزن هر کارتن (kg)</label>
                  <input type="number" step="0.001" value={item.carton_weight} onChange={e => updateItem(idx, 'carton_weight', e.target.value)} className="input text-xs" />
                </div>
                <div>
                  <label className="label text-[10px] mb-1 block">قیمت واحد (¥)</label>
                  <input type="number" step="0.01" value={item.unit_price_cny} onChange={e => updateItem(idx, 'unit_price_cny', e.target.value)} className="input text-xs" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-xs text-green-400">
                  بهای تمام شده تخمینی: <span className="font-bold">{fmt(calcCost(item))}</span> ریال/عدد
                </div>
                {items.length > 1 && (
                  <button onClick={() => removeItem(idx)} className="text-xs text-red-400 hover:text-red-300">× حذف</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* هزینه‌های جانبی */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">هزینه‌های جانبی</h3>
          <button onClick={addExtra} className="text-xs text-brand hover:text-brand/80">+ افزودن هزینه</button>
        </div>
        {extras.length === 0 ? (
          <div className="text-center py-4 text-gray-steel text-xs">هزینه جانبی‌ای ثبت نشده</div>
        ) : (
          <div className="space-y-2">
            {extras.map((e, idx) => (
              <div key={idx} className="grid grid-cols-4 gap-3 bg-white/5 rounded-lg p-3">
                <select value={e.cost_type} onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, cost_type: ev.target.value } : x))} className="input text-xs">
                  {EXTRA_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <input type="number" value={e.amount_irr} onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, amount_irr: ev.target.value } : x))}
                  className="input text-xs" placeholder="مبلغ (ریال)" />
                <input value={e.description} onChange={ev => setExtras(ex => ex.map((x, i) => i === idx ? { ...x, description: ev.target.value } : x))}
                  className="input text-xs" placeholder="توضیح" />
                <button onClick={() => setExtras(ex => ex.filter((_, i) => i !== idx))} className="text-red-400 text-xs">× حذف</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {msg && <div className={`rounded-lg px-4 py-3 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{msg.text}</div>}

      <div className="flex gap-3">
        <button onClick={handleSubmit} disabled={createMut.isPending} className="btn-primary flex-1 py-3 disabled:opacity-50">
          {createMut.isPending ? 'در حال ثبت...' : 'ثبت فاکتور خرید'}
        </button>
        <button onClick={onClose} className="btn-secondary px-6 py-3">انصراف</button>
      </div>
    </div>
  )
}

export default function PurchaseInvoicePage() {
  const [view, setView] = useState('list') // list | new | detail
  const [selectedId, setSelectedId] = useState(null)

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices'],
    queryFn: () => api.get('/accounting/invoices/').then(r => r.data),
    enabled: view === 'list',
  })

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {view !== 'list' && (
            <button onClick={() => setView('list')} className="text-gray-steel hover:text-white text-sm">← برگشت</button>
          )}
          <h1 className="font-display font-bold text-2xl text-white">
            {view === 'list' ? 'فاکتورهای خرید' : view === 'new' ? 'فاکتور خرید جدید' : 'جزئیات فاکتور'}
          </h1>
        </div>
        {view === 'list' && (
          <button onClick={() => setView('new')} className="btn-primary text-sm px-4 py-2">+ فاکتور جدید</button>
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
              <button onClick={() => setView('new')} className="btn-primary text-sm px-6 py-2">+ ثبت اولین فاکتور</button>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['شماره', 'تامین‌کننده', 'تاریخ', 'وضعیت', 'اقلام', 'جمع یوان', 'جمع ریال', ''].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv, i) => (
                  <tr key={inv.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px' }}>{inv.invoice_number || `#${inv.id}`}</td>
                    <td style={{ padding: '10px 12px' }}>{inv.supplier_name}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{inv.date}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: STATUS_COLORS[inv.status], background: STATUS_COLORS[inv.status] + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>{inv.status_display}</span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>{inv.items_count}</td>
                    <td style={{ padding: '10px 12px', color: '#0066FF' }}>{fmt(inv.total_cny)} ¥</td>
                    <td style={{ padding: '10px 12px', color: '#00C896' }}>{fmt(inv.total_irr)} ت</td>
                    <td style={{ padding: '10px 12px' }}>
                      <button onClick={() => { setSelectedId(inv.id); setView('detail') }}
                        className="text-xs text-brand hover:text-brand/80">مشاهده</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {view === 'new' && <NewInvoiceForm onClose={() => setView('list')} onSuccess={() => setView('list')} />}
      {view === 'detail' && selectedId && <InvoiceDetail id={selectedId} onClose={() => setView('list')} />}
    </div>
  )
}
"""

# ─── 3. BalancePage.jsx ──────────────────────────────────────
balance_jsx = r"""import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function BalancePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['balance-report'],
    queryFn: () => api.get('/accounting/reports/balance/').then(r => r.data),
  })

  const contacts = data?.contacts || []
  const totalDebtIrr = contacts.filter(c => c.balance_irr > 0).reduce((s, c) => s + c.balance_irr, 0)
  const totalCreditIrr = contacts.filter(c => c.balance_irr < 0).reduce((s, c) => s + Math.abs(c.balance_irr), 0)
  const totalDebtCny = contacts.filter(c => c.balance_cny > 0).reduce((s, c) => s + c.balance_cny, 0)
  const totalCreditCny = contacts.filter(c => c.balance_cny < 0).reduce((s, c) => s + Math.abs(c.balance_cny), 0)

  return (
    <div className="container-main py-8 max-w-5xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">تراز حساب‌ها</h1>

      {/* خلاصه */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بدهکاران (ریال)</div>
          <div className="text-lg font-bold text-red-400">{fmt(totalDebtIrr)}</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بستانکاران (ریال)</div>
          <div className="text-lg font-bold text-green-400">{fmt(totalCreditIrr)}</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بدهکاران (یوان)</div>
          <div className="text-lg font-bold text-red-400">{fmt(totalDebtCny)} ¥</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بستانکاران (یوان)</div>
          <div className="text-lg font-bold text-green-400">{fmt(totalCreditCny)} ¥</div>
        </div>
      </div>

      {/* جدول تراز */}
      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-12 text-gray-steel">هنوز تراکنشی ثبت نشده</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['طرف حساب', 'نوع', 'وضعیت ریالی', 'مانده ریال', 'وضعیت یوانی', 'مانده یوان'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contacts.map((c, i) => (
                <tr key={c.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{c.name}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{c.contact_type_display}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896',
                      background: (c.balance_irr > 0 ? '#FF3B3B' : '#00C896') + '20',
                      padding: '2px 10px', borderRadius: 20, fontSize: 11
                    }}>{c.status_irr}</span>
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896' }}>
                    {fmt(Math.abs(c.balance_irr))} ت
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {c.balance_cny !== 0 && (
                      <span style={{
                        color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896',
                        background: (c.balance_cny > 0 ? '#FF3B3B' : '#00C896') + '20',
                        padding: '2px 10px', borderRadius: 20, fontSize: 11
                      }}>{c.status_cny}</span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896' }}>
                    {c.balance_cny !== 0 ? `${fmt(Math.abs(c.balance_cny))} ¥` : '—'}
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
"""

# ─── نوشتن فایل‌ها ────────────────────────────────────────────
files = {
    os.path.join(pages_admin, "ContactsPage.jsx"): contacts_jsx,
    os.path.join(pages_admin, "PurchaseInvoicePage.jsx"): invoice_jsx,
    os.path.join(pages_admin, "BalancePage.jsx"): balance_jsx,
}
for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ {os.path.basename(path)}")

# ─── آپدیت App.jsx ───────────────────────────────────────────
app_jsx_path = os.path.join(FRONTEND, "App.jsx")
with open(app_jsx_path, encoding="utf-8") as f:
    app = f.read()

imports_to_add = """import ContactsPage from './pages/admin/ContactsPage'
import PurchaseInvoicePage from './pages/admin/PurchaseInvoicePage'
import BalancePage from './pages/admin/BalancePage'
"""
routes_to_add = """        <Route path="admin/contacts" element={<RequireAuth><ContactsPage /></RequireAuth>} />
        <Route path="admin/purchases" element={<RequireAuth><PurchaseInvoicePage /></RequireAuth>} />
        <Route path="admin/balance" element={<RequireAuth><BalancePage /></RequireAuth>} />"""

if "ContactsPage" not in app:
    app = app.replace("import KardexPage", imports_to_add + "import KardexPage")
    app = app.replace(
        '<Route path="admin/kardex"',
        routes_to_add + '\n        <Route path="admin/kardex"'
    )
    with open(app_jsx_path, "w", encoding="utf-8") as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")
else:
    print("✓ App.jsx قبلاً آپدیت شده بود")

print("\n✅ همه فایل‌ها ساخته شدند!")
print("آدرس‌های جدید:")
print("  /admin/contacts   — طرف حساب‌ها")
print("  /admin/purchases  — فاکتورهای خرید")
print("  /admin/balance    — تراز حساب‌ها")
