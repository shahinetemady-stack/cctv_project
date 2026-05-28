import { useState } from 'react'
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
