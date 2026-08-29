import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../../components/ui/AmountInput'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const METHODS = [
  { value: 'cash', label: 'نقد' },
  { value: 'transfer', label: 'حواله بانکی' },
  { value: 'card', label: 'کارت به کارت' },
  { value: 'cheque', label: 'چک' },
]

// ─── فرم ثبت پرداخت/دریافت ───────────────────────────────────
export function PaymentForm({ direction, editing = null, onClose, onSuccess }) {
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
    contact_id: editing?.contact_id ?? '',
    from_account_id: editing?.from_account_id ?? '',
    to_account_id: editing?.to_account_id ?? '',
    payment_type: editing?.payment_type ?? 'transfer',
    currency: editing?.currency ?? 'IRR',
    amount: editing?.amount ?? '',
    rate_irr: editing?.rate_irr ?? '',
    account_amount: '',  // مبلغ برداشت/واریز به ارز حساب (فقط بین‌ارزی — دستی قابل تغییر)
    date: editing?.date ?? new Date().toISOString().split('T')[0],
    reference: editing?.reference ?? '',
    note: editing?.note ?? '',
  })
  const [msg, setMsg] = useState(null)

  // نرخ یوان مرجع روز — پیش‌پر کردن نرخ تبدیل برای پرداخت یوانی
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  useEffect(() => {
    if (!editing && form.currency === 'CNY' && rateData?.rate_cny_to_irt) {
      setForm(f => f.rate_irr ? f : { ...f, rate_irr: String(rateData.rate_cny_to_irt) })
    }
  }, [rateData, form.currency, editing])

  // حساب فعال در جریان (مبدا در پرداخت / مقصد در دریافت)
  const activeAccId = isReceive ? form.to_account_id : form.from_account_id
  const activeAcc = accounts.find(a => String(a.id) === String(activeAccId))
  const crossCurrency = !!(activeAcc && activeAcc.currency !== form.currency)

  // تبدیل دومسیره (الگوی Odoo/QuickBooks): مبلغ × نرخ = برداشت — تغییر هر یک بقیه را حساب می‌کند
  const computedDeduction = () => {
    const amt = Number(form.amount) || 0
    const rate = Number(form.rate_irr) || 0
    if (!crossCurrency || !amt || !rate) return ''
    return activeAcc.currency === 'IRR'
      ? String(Math.round(amt * rate))
      : String(Math.round((amt / rate) * 100) / 100)
  }
  const onAmountChange = (e) => setForm(f => ({ ...f, amount: e.target.value, account_amount: '' }))
  const onRateChange = (e) => setForm(f => ({ ...f, rate_irr: e.target.value, account_amount: '' }))
  const onDeductionChange = (e) => {
    const v = e.target.value
    const amt = Number(form.amount) || 0
    const ded = Number(v) || 0
    // نرخ از روی برداشت دستی برمی‌گردد محاسبه شود
    const newRate = amt > 0 && ded > 0
      ? (activeAcc.currency === 'IRR'
          ? String(Math.round(ded / amt))
          : String(Math.round((amt / ded) * 1000000) / 1000000))
      : form.rate_irr
    setForm(f => ({ ...f, account_amount: v, rate_irr: newRate }))
  }
  const deductionValue = form.account_amount !== '' ? form.account_amount : computedDeduction()

  const mut = useMutation({
    mutationFn: (d) => editing
      ? api.patch(`/accounting/payments/${editing.id}/`, d).then(r => r.data)
      : api.post('/accounting/payments/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      qc.invalidateQueries(['contacts-all'])
      setMsg({ type: 'success', text: editing ? 'تراکنش به‌روز شد' : 'پرداخت ثبت شد' })
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
    if (crossCurrency && !(Number(form.rate_irr) > 0)) {
      return setMsg({ type: 'error', text: 'نرخ تبدیل را وارد کنید (یا مبلغ برداشت را دستی وارد کنید تا نرخ محاسبه شود)' })
    }

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
            {editing ? '✏️ ویرایش تراکنش' : isReceive ? '💚 ثبت دریافت' : '🔴 ثبت پرداخت'}
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
              <label className="label text-xs mb-1 block">مبلغ * ({form.currency === 'CNY' ? 'یوان' : 'ریال'})</label>
              <AmountInput value={form.amount}
                onChange={onAmountChange}
                className="input text-sm" placeholder="0" />
            </div>
          </div>

          {/* پنل تبدیل ارز — فقط وقتی ارز حساب با ارز پرداخت فرق دارد */}
          {crossCurrency && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 space-y-3">
              <div className="text-xs font-bold text-blue-300">
                💱 تبدیل ارز — {form.currency === 'CNY' ? 'یوان' : 'ریال'} ← {activeAcc.currency === 'CNY' ? 'یوان' : 'ریال'}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به ازای هر یوان) *</label>
                  <AmountInput value={form.rate_irr}
                    onChange={onRateChange}
                    className="input text-sm" placeholder="مثلاً 280000" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">
                    {isReceive ? 'واریز به حساب' : 'برداشت از حساب'} ({activeAcc.currency === 'CNY' ? 'یوان' : 'ریال'}) *
                  </label>
                  <AmountInput value={deductionValue}
                    onChange={onDeductionChange}
                    className="input text-sm" placeholder="خودکار" />
                </div>
              </div>
              <div className="text-[10px] text-blue-300/80 leading-5">
                فیلدها به هم لینک هستند: مبلغ یا نرخ را عوض کنی برداشت محاسبه می‌شود؛ برداشت را دستی عوض کنی نرخ برمی‌گردد محاسبه می‌شود.
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {!isReceive && (
              <div>
                <label className="label text-xs mb-1 block">پرداخت از حساب *</label>
                <select value={form.from_account_id} onChange={e => setForm(f => ({ ...f, from_account_id: e.target.value }))} className="input text-sm">
                  <option value="">انتخاب کنید...</option>
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </select>
              </div>
            )}
            {isReceive && (
              <div>
                <label className="label text-xs mb-1 block">دریافت در حساب *</label>
                <select value={form.to_account_id} onChange={e => setForm(f => ({ ...f, to_account_id: e.target.value }))} className="input text-sm">
                  <option value="">انتخاب کنید...</option>
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
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
            {mut.isPending ? 'در حال ثبت...' : editing ? '✓ ذخیره تغییرات' : isReceive ? '✓ ثبت دریافت' : '✓ ثبت پرداخت'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── فرم سند حسابداری — انتقال بدهی/طلب بین دو طرف حساب ─────
function VoucherForm({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    from_contact_id: '', to_contact_id: '', currency: 'IRR', amount: '', rate_irr: '',
    date: new Date().toISOString().split('T')[0], reference: '', note: '',
  })
  const [msg, setMsg] = useState(null)

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-all'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const mut = useMutation({
    mutationFn: async (payloads) => {
      // دو رکورد متقابل: از مبدا «پرداخت» (balance مثبت‌تر) و به مقصد «دریافت» (balance منفی‌تر)
      await api.post('/accounting/payments/', payloads[0])
      return api.post('/accounting/payments/', payloads[1]).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      qc.invalidateQueries(['contacts-all'])
      qc.invalidateQueries(['contacts'])
      qc.invalidateQueries(['contact-detail'])
      setMsg({ type: 'success', text: 'سند انتقال ثبت شد' })
      setTimeout(onClose, 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const fromContact = contacts.find(c => String(c.id) === String(form.from_contact_id))
  const toContact = contacts.find(c => String(c.id) === String(form.to_contact_id))

  function handleSubmit() {
    if (!form.from_contact_id) return setMsg({ type: 'error', text: 'طرف حساب مبدا را انتخاب کنید' })
    if (!form.to_contact_id) return setMsg({ type: 'error', text: 'طرف حساب مقصد را انتخاب کنید' })
    if (form.from_contact_id === form.to_contact_id) return setMsg({ type: 'error', text: 'مبدا و مقصد نمی‌توانند یکی باشند' })
    if (!form.amount || Number(form.amount) <= 0) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    setMsg(null)
    const base = {
      currency: form.currency,
      amount: Number(form.amount),
      rate_irr: Number(form.rate_irr) || 0,
      date: form.date,
      reference: form.reference,
      payment_type: 'other',
    }
    mut.mutate([
      { ...base, contact_id: form.from_contact_id, direction: 'out',
        note: `سند انتقال به ${toContact?.name || ''}${form.note ? ' — ' + form.note : ''}` },
      { ...base, contact_id: form.to_contact_id, direction: 'in',
        note: `سند انتقال از ${fromContact?.name || ''}${form.note ? ' — ' + form.note : ''}` },
    ])
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">📒 سند حسابداری — انتقال بین طرف حساب‌ها</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label text-xs mb-1 block">از طرف حساب *</label>
            <select value={form.from_contact_id} onChange={e => setForm(f => ({ ...f, from_contact_id: e.target.value }))} className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {contacts.map(c => <option key={c.id} value={c.id}>{c.name} ({c.contact_type_display})</option>)}
            </select>
            <div className="text-[10px] text-gray-steel mt-1">بستانکاری‌اش کم / بدهی‌اش زیاد می‌شود</div>
          </div>
          <div>
            <label className="label text-xs mb-1 block">به طرف حساب *</label>
            <select value={form.to_contact_id} onChange={e => setForm(f => ({ ...f, to_contact_id: e.target.value }))} className="input text-sm">
              <option value="">انتخاب کنید...</option>
              {contacts.filter(c => String(c.id) !== String(form.from_contact_id)).map(c => <option key={c.id} value={c.id}>{c.name} ({c.contact_type_display})</option>)}
            </select>
            <div className="text-[10px] text-gray-steel mt-1">بستانکاری‌اش زیاد / بدهی‌اش کم می‌شود</div>
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
              <AmountInput value={form.amount}
                onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                className="input text-sm" placeholder="0" />
            </div>
          </div>

          {form.currency === 'CNY' && (
            <div>
              <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به ازای هر یوان)</label>
              <AmountInput value={form.rate_irr}
                onChange={e => setForm(f => ({ ...f, rate_irr: e.target.value }))}
                className="input text-sm" placeholder="مثلاً 270000" />
            </div>
          )}

          <div>
            <label className="label text-xs mb-1 block">تاریخ</label>
            <input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} className="input text-sm" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">شماره پیگیری / مرجع</label>
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))} className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">شرح سند</label>
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
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {mut.isPending ? 'در حال ثبت...' : '✓ ثبت سند انتقال'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── فرم جابجایی پول بین حساب‌های داخلی (هم‌ارز یا با نرخ تبدیل) ───
function TransferForm({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    from_account_id: '', to_account_id: '', amount: '', rate_irr: '',
    date: new Date().toISOString().split('T')[0], reference: '', note: '',
  })
  const [msg, setMsg] = useState(null)

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })
  // نرخ یوان مرجع روز — پیش‌پر کردن نرخ تبدیل بین‌ارزی
  const { data: rateData } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })
  useEffect(() => {
    if (rateData?.rate_cny_to_irt) {
      setForm(f => f.rate_irr ? f : { ...f, rate_irr: String(rateData.rate_cny_to_irt) })
    }
  }, [rateData])

  const mut = useMutation({
    mutationFn: async (payloads) => {
      await api.post('/accounting/payments/', payloads[0])
      if (payloads[1]) return api.post('/accounting/payments/', payloads[1]).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      setMsg({ type: 'success', text: 'جابجایی ثبت شد' })
      setTimeout(onClose, 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const fromAcc = accounts.find(a => String(a.id) === String(form.from_account_id))
  const toAcc = accounts.find(a => String(a.id) === String(form.to_account_id))
  const crossCurrency = fromAcc && toAcc && fromAcc.currency !== toAcc.currency
  const toAccounts = accounts.filter(a => String(a.id) !== String(form.from_account_id))

  // مبلغ واریز به مقصد بر اساس نرخ (ریال به ازای هر واحد ارز)
  const rate = Number(form.rate_irr) || 0
  const amountFrom = Number(form.amount) || 0
  let amountTo = amountFrom
  if (crossCurrency && rate > 0 && amountFrom > 0) {
    amountTo = fromAcc.currency === 'IRR' ? amountFrom / rate : amountFrom * rate
  }
  const CUR_LABEL = { IRR: 'ریال', CNY: 'یوان', USD: 'دلار' }

  function handleSubmit() {
    if (!form.from_account_id) return setMsg({ type: 'error', text: 'حساب مبدا را انتخاب کنید' })
    if (!form.to_account_id) return setMsg({ type: 'error', text: 'حساب مقصد را انتخاب کنید' })
    if (!form.amount || Number(form.amount) <= 0) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    if (crossCurrency) {
      if (fromAcc.currency !== 'IRR' && toAcc.currency !== 'IRR') {
        return setMsg({ type: 'error', text: 'تبدیل مستقیم بین دو ارز غیرریالی پشتیبانی نمی‌شود — ابتدا به حساب ریالی منتقل کنید' })
      }
      if (!rate || rate <= 0) return setMsg({ type: 'error', text: 'نرخ تبدیل را وارد کنید' })
    }
    setMsg(null)
    const base = {
      payment_type: 'transfer',
      date: form.date,
      reference: form.reference,
      rate_irr: rate,
      note: form.note,
    }
    if (crossCurrency) {
      // دو رکورد: برداشت از مبدا + واریز به مقصد با ارز و مبلغ خودشان
      mut.mutate([
        { ...base, direction: 'out', from_account_id: form.from_account_id,
          currency: fromAcc.currency, amount: amountFrom,
          note: `جابجایی به ${toAcc.name}${form.note ? ' — ' + form.note : ''}` },
        { ...base, direction: 'in', to_account_id: form.to_account_id,
          currency: toAcc.currency, amount: Math.round(amountTo * 100) / 100,
          note: `جابجایی از ${fromAcc.name}${form.note ? ' — ' + form.note : ''}` },
      ])
    } else {
      mut.mutate([
        { ...base, direction: 'out', from_account_id: form.from_account_id,
          to_account_id: form.to_account_id, currency: fromAcc?.currency || 'IRR', amount: amountFrom },
      ])
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">🔁 جابجایی پول بین حساب‌ها</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">از حساب *</label>
              <select value={form.from_account_id}
                onChange={e => setForm(f => ({ ...f, from_account_id: e.target.value, to_account_id: '' }))}
                className="input text-sm">
                <option value="">انتخاب کنید...</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">به حساب *</label>
              <select value={form.to_account_id} onChange={e => setForm(f => ({ ...f, to_account_id: e.target.value }))}
                className="input text-sm" disabled={!form.from_account_id}>
                <option value="">انتخاب کنید...</option>
                {toAccounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">مبلغ برداشت * {fromAcc && `(${CUR_LABEL[fromAcc.currency]})`}</label>
              <AmountInput value={form.amount}
                onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                className="input text-sm" placeholder="0" />
            </div>
            {crossCurrency ? (
              <div>
                <label className="label text-xs mb-1 block">نرخ تبدیل (ریال به ازای هر {CUR_LABEL[toAcc.currency === 'IRR' ? fromAcc.currency : toAcc.currency]}) *</label>
                <AmountInput value={form.rate_irr}
                  onChange={e => setForm(f => ({ ...f, rate_irr: e.target.value }))}
                  className="input text-sm" placeholder="مثلاً 270000" />
              </div>
            ) : (
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} className="input text-sm" />
              </div>
            )}
          </div>

          {crossCurrency && (
            <>
              <div className="bg-brand/10 border border-brand/30 rounded-xl px-4 py-3 text-sm">
                <span className="text-gray-steel">مبلغ واریز به مقصد: </span>
                <span className="font-bold text-brand">
                  {rate > 0 && amountFrom > 0
                    ? `${Number(amountTo.toFixed(2)).toLocaleString('fa-IR')} ${CUR_LABEL[toAcc.currency]}`
                    : '—'}
                </span>
              </div>
              <div>
                <label className="label text-xs mb-1 block">تاریخ</label>
                <input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} className="input text-sm" />
              </div>
            </>
          )}

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
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {mut.isPending ? 'در حال ثبت...' : '✓ ثبت جابجایی'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه اصلی: هاب دریافت و پرداخت ─────────────────────────
const ACTIONS = [
  { key: 'in',       icon: '💚', title: 'ثبت دریافت',       desc: 'دریافت وجه از طرف حساب به یکی از حساب‌ها', color: '#00C896' },
  { key: 'out',      icon: '🔴', title: 'ثبت پرداخت',       desc: 'پرداخت وجه به طرف حساب از یکی از حساب‌ها', color: '#FF3B3B' },
  { key: 'voucher',  icon: '📒', title: 'سند حسابداری',     desc: 'انتقال بدهی/طلب بین دو طرف حساب (بدون گردش بانکی)', color: '#FBC02D' },
  { key: 'transfer', icon: '🔁', title: 'جابجایی پول درون بانک', desc: 'انتقال بین حساب‌های داخلی — هم‌ارز یا با نرخ تبدیل', color: '#0066FF' },
]

export default function PaymentsPage() {
  const [active, setActive] = useState(null) // 'in' | 'out' | 'voucher' | 'transfer' | null
  const { can } = usePermissions()

  return (
    <div className="container-main py-8 max-w-3xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">دریافت و پرداخت</h1>

      {!can('purchase_create') ? (
        <div className="card p-12 text-center text-gray-steel text-sm">دسترسی ثبت تراکنش ندارید</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {ACTIONS.map(a => (
            <button key={a.key} onClick={() => setActive(a.key)}
              className="card p-6 text-right hover:bg-white/5 transition-all cursor-pointer">
              <div className="text-3xl mb-3">{a.icon}</div>
              <div className="font-bold text-white mb-1" style={{ color: a.color }}>{a.title}</div>
              <div className="text-xs text-gray-steel">{a.desc}</div>
            </button>
          ))}
        </div>
      )}

      {(active === 'in' || active === 'out') && (
        <PaymentForm direction={active} onClose={() => setActive(null)} onSuccess={() => setActive(null)} />
      )}
      {active === 'voucher' && <VoucherForm onClose={() => setActive(null)} />}
      {active === 'transfer' && <TransferForm onClose={() => setActive(null)} />}
    </div>
  )
}
