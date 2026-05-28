import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const METHODS = [
  { value: 'cash', label: 'نقد' },
  { value: 'transfer', label: 'حواله بانکی' },
  { value: 'card', label: 'کارت به کارت' },
  { value: 'cheque', label: 'چک' },
]

// ─── فرم ثبت پرداخت/دریافت ───────────────────────────────────
function PaymentForm({ direction, onClose, onSuccess }) {
  const isReceive = direction === 'in'
  const qc = useQueryClient()

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })

  const [form, setForm] = useState({
    contact_id: '',
    from_account_id: '',
    to_account_id: '',
    payment_type: 'transfer',
    currency: 'IRR',
    amount: '',
    rate_irr: '',
    date: new Date().toISOString().split('T')[0],
    reference: '',
    note: '',
  })
  const [msg, setMsg] = useState(null)

  const mut = useMutation({
    mutationFn: (d) => api.post('/accounting/payments/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['contacts-all'])
      setMsg({ type: 'success', text: 'پرداخت ثبت شد' })
      setTimeout(() => onSuccess?.(), 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const irrAccounts = accounts.filter(a => a.currency === 'IRR')
  const cnyAccounts = accounts.filter(a => a.currency === 'CNY')

  function handleSubmit() {
    if (!form.contact_id) return setMsg({ type: 'error', text: 'طرف حساب را انتخاب کنید' })
    if (!form.amount) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    if (isReceive && !form.to_account_id) return setMsg({ type: 'error', text: 'حساب مقصد را انتخاب کنید' })
    if (!isReceive && !form.from_account_id) return setMsg({ type: 'error', text: 'حساب مبدا را انتخاب کنید' })

    mut.mutate({
      ...form,
      direction: isReceive ? 'in' : 'out',
      amount: Number(form.amount),
      rate_irr: Number(form.rate_irr) || 0,
      contact: form.contact_id,
      from_account: form.from_account_id || null,
      to_account: form.to_account_id || null,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">
            {isReceive ? '💚 ثبت دریافت' : '🔴 ثبت پرداخت'}
          </h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">طرف حساب *</label>
              <select value={form.contact_id} onChange={e => setForm(f => ({ ...f, contact_id: e.target.value }))} className="input text-sm">
                <option value="">انتخاب کنید...</option>
                {contacts.map(c => <option key={c.id} value={c.id}>{c.name} ({c.contact_type_display})</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">روش پرداخت</label>
              <select value={form.payment_type} onChange={e => setForm(f => ({ ...f, payment_type: e.target.value }))} className="input text-sm">
                {METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">ارز</label>
              <select value={form.currency} onChange={e => setForm(f => ({ ...f, currency: e.target.value }))} className="input text-sm">
                <option value="IRR">ریال (IRR)</option>
                <option value="CNY">یوان (CNY)</option>
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">مبلغ *</label>
              <input inputMode="numeric" value={form.amount}
                onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                className="input text-sm" placeholder="0" />
            </div>
          </div>

          {form.currency === 'CNY' && (
            <div>
              <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به یوان)</label>
              <input inputMode="numeric" value={form.rate_irr}
                onChange={e => setForm(f => ({ ...f, rate_irr: e.target.value }))}
                className="input text-sm" placeholder="مثلاً 270000" />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {!isReceive && (
              <div>
                <label className="label text-xs mb-1 block">پرداخت از حساب *</label>
                <select value={form.from_account_id} onChange={e => setForm(f => ({ ...f, from_account_id: e.target.value }))} className="input text-sm">
                  <option value="">انتخاب کنید...</option>
                  {(form.currency === 'CNY' ? cnyAccounts : irrAccounts).map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            )}
            {isReceive && (
              <div>
                <label className="label text-xs mb-1 block">دریافت در حساب *</label>
                <select value={form.to_account_id} onChange={e => setForm(f => ({ ...f, to_account_id: e.target.value }))} className="input text-sm">
                  <option value="">انتخاب کنید...</option>
                  {(form.currency === 'CNY' ? cnyAccounts : irrAccounts).map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="label text-xs mb-1 block">تاریخ</label>
              <input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} className="input text-sm" />
            </div>
          </div>

          <div>
            <label className="label text-xs mb-1 block">شماره پیگیری / مرجع</label>
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">توضیحات</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={mut.isPending}
            className={`flex-1 py-2.5 rounded-xl font-semibold text-sm disabled:opacity-50 ${isReceive ? 'bg-green-600 hover:bg-green-500 text-white' : 'bg-red-600 hover:bg-red-500 text-white'}`}>
            {mut.isPending ? 'در حال ثبت...' : isReceive ? '✓ ثبت دریافت' : '✓ ثبت پرداخت'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
export default function PaymentsPage() {
  const [showForm, setShowForm] = useState(null) // 'in' | 'out' | null
  const qc = useQueryClient()

  const { data: payments = [], isLoading } = useQuery({
    queryKey: ['payments-list'],
    queryFn: () => api.get('/accounting/payments/').then(r => r.data),
  })

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })

  // جمع موجودی حساب‌ها
  const totalIRR = accounts.filter(a => a.currency === 'IRR').reduce((s, a) => s + (a.balance || 0), 0)
  const totalCNY = accounts.filter(a => a.currency === 'CNY').reduce((s, a) => s + (a.balance || 0), 0)

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">دریافت و پرداخت</h1>
        <div className="flex gap-3">
          <button onClick={() => setShowForm('in')}
            className="px-4 py-2 rounded-xl text-sm font-semibold bg-green-600 hover:bg-green-500 text-white transition-all">
            + ثبت دریافت
          </button>
          <button onClick={() => setShowForm('out')}
            className="px-4 py-2 rounded-xl text-sm font-semibold bg-red-600 hover:bg-red-500 text-white transition-all">
            + ثبت پرداخت
          </button>
        </div>
      </div>

      {/* خلاصه حساب‌ها */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="card p-4 col-span-1">
          <div className="text-xs text-gray-steel mb-2">موجودی کل (ریال)</div>
          <div className={`text-xl font-bold ${totalIRR >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(totalIRR)} ت</div>
        </div>
        <div className="card p-4 col-span-1">
          <div className="text-xs text-gray-steel mb-2">موجودی کل (یوان)</div>
          <div className={`text-xl font-bold ${totalCNY >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(totalCNY)} ¥</div>
        </div>
        <div className="card p-4 col-span-1">
          <div className="text-xs text-gray-steel mb-2">تعداد حساب‌های فعال</div>
          <div className="text-xl font-bold text-white">{accounts.length}</div>
        </div>
      </div>

      {/* لیست حساب‌ها */}
      <div className="card p-5 mb-6">
        <h3 className="text-sm font-semibold text-white mb-4">حساب‌های بانکی و صندوق</h3>
        <div className="grid grid-cols-2 gap-3">
          {accounts.map(a => (
            <div key={a.id} className="bg-white/5 rounded-xl p-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-white">{a.name}</div>
                <div className="text-xs text-gray-steel">{a.account_type_display || a.account_type} | {a.currency}</div>
              </div>
              <div className={`text-lg font-bold ${(a.balance || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {fmt(a.balance)} {a.currency === 'CNY' ? '¥' : 'ت'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* لیست تراکنش‌ها */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">آخرین تراکنش‌ها</h3>
        {isLoading ? (
          <div className="text-center py-6 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : payments.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-sm">تراکنشی ثبت نشده</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['نوع', 'طرف حساب', 'مبلغ', 'ارز', 'روش', 'تاریخ', 'مرجع'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {payments.slice(0, 50).map((p, i) => (
                  <tr key={p.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        color: p.direction === 'in' ? '#00C896' : '#FF3B3B',
                        background: p.direction === 'in' ? '#00C89620' : '#FF3B3B20',
                        padding: '2px 8px', borderRadius: 20, fontSize: 11
                      }}>
                        {p.direction === 'in' ? '↓ دریافت' : '↑ پرداخت'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>{p.contact_name || p.contact}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: p.direction === 'in' ? '#00C896' : '#FF3B3B' }}>
                      {fmt(p.amount)}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)' }}>{p.currency}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.payment_type_display || p.payment_type}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.date}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.reference || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showForm && (
        <PaymentForm
          direction={showForm}
          onClose={() => setShowForm(null)}
          onSuccess={() => setShowForm(null)}
        />
      )}
    </div>
  )
}
