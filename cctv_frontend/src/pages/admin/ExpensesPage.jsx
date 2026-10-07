import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import usePermissions from '../../hooks/usePermissions'
import AmountInput, { parseAmount } from '../../components/ui/AmountInput'
import JalaliDateInput from '../../components/ui/JalaliDateInput'
import SearchSelect from '../../components/ui/SearchSelect'
import { jalaliToGregorian, gregorianToJalali, JALALI_MONTHS, jalaliText, jalaliMonthDays } from '../../utils/jalali'
import { todayTehran, todayTehranParts } from '../../utils/date'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_BADGE = {
  draft:     { cls: 'badge-gold',    label: 'پیش‌نویس' },
  confirmed: { cls: 'badge-success', label: 'تأیید شده' },
  paid:      { cls: 'badge',         label: '💳 پرداخت شده' },
}

const MOVEMENT_TYPES = [
  { value: 'deposit',  label: 'واریز' },
  { value: 'withdraw', label: 'برداشت' },
]

// ─── انتخاب ماه جلالی مشترک — خروجی ماه/سال میلادی برای کوئری‌ها ──
function MonthSelector({ jy, jm, setJy, setJm, label }) {
  const years = Array.from({ length: 16 }, (_, i) => 1400 + i)
  return (
    <div className="flex items-end gap-3 flex-wrap">
      <div>
        <label className="text-xs text-gray-steel block mb-1">ماه</label>
        <select value={jm} onChange={e => setJm(Number(e.target.value))} className="input text-sm">
          {JALALI_MONTHS.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
        </select>
      </div>
      <div>
        <label className="text-xs text-gray-steel block mb-1">سال</label>
        <select value={jy} onChange={e => setJy(Number(e.target.value))} className="input text-sm">
          {years.map(y => <option key={y} value={y}>{y.toLocaleString('fa-IR')}</option>)}
        </select>
      </div>
      <div className="text-sm text-brand font-bold pb-2">{label}</div>
    </div>
  )
}

// ─── برچسب ماه جلالی از سال/ماه میلادی ─────────────────────────
function monthLabelFromGregorian(year, month) {
  const [jy, jm] = gregorianToJalali(Number(year), Number(month), 1)
  return `${JALALI_MONTHS[jm - 1]} ${jy.toLocaleString('fa-IR')}`
}

// ─── انتخاب سر فصل با افزودن سریع ─────────────────────────────
function CategorySelect({ value, onChange, type, disabled }) {
  const qc = useQueryClient()
  const { data: categories = [] } = useQuery({
    queryKey: ['expenses-categories', type],
    queryFn: () => api.get('/expenses/categories/', { params: { type } }).then(r => r.data),
  })

  const addMut = useMutation({
    mutationFn: (name) => api.post('/expenses/categories/', { name, category_type: type, is_active: true }).then(r => r.data),
    onSuccess: (c) => {
      qc.invalidateQueries(['expenses-categories'])
      onChange(String(c.id))
      toast.success('سر فصل جدید ساخته شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  function quickAdd() {
    const name = window.prompt('نام سر فصل جدید:')
    if (name && name.trim()) addMut.mutate(name.trim())
  }

  return (
    <div className="flex items-end gap-2">
      <div className="flex-1">
        <select value={value} disabled={disabled}
          onChange={e => onChange(e.target.value)}
          className="input text-sm w-full">
          <option value="">— انتخاب —</option>
          {categories.filter(c => c.is_active).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>
      <button type="button" onClick={quickAdd} disabled={disabled || addMut.isPending}
        className="btn-secondary text-xs px-3 py-2 whitespace-nowrap disabled:opacity-50">
        + سر فصل
      </button>
    </div>
  )
}

// ─── حذف هزینه — برگشت اسناد حسابداری و حذف سند هزینه ─────────
function useChargeDelete(onDeleted) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => api.delete(`/expenses/charges/${id}/delete/`).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['expenses-charges'])
      qc.invalidateQueries(['expenses-charge'])
      qc.invalidateQueries(['expenses-recurring-kardex'])
      qc.invalidateQueries(['expenses-investors-kardex'])
      toast.success(r.message || 'حذف شد')
      onDeleted?.()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })
}

// ─── مودال جزئیات هزینه با لیست اقساط ─────────────────────────
function ChargeDetailModal({ chargeId, onClose }) {
  const { can } = usePermissions()
  const delMut = useChargeDelete(onClose)
  const { data: charge, isLoading } = useQuery({
    queryKey: ['expenses-charge', chargeId],
    queryFn: () => api.get(`/expenses/charges/${chargeId}/`).then(r => r.data),
  })

  const badge = charge && STATUS_BADGE[charge.status]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        {isLoading || !charge ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : (
          <div>
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="font-bold text-white text-lg">🧾 {charge.title}</h2>
                <div className="text-xs text-gray-steel mt-1">{monthLabelFromGregorian(charge.year, charge.month)}</div>
              </div>
              <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
            </div>

            <div className="space-y-1">
              {[
                { label: 'سر فصل', value: charge.category_name || '—' },
                { label: 'طرف حساب', value: charge.contact_name || '—' },
                { label: 'مبلغ', value: `${fmt(charge.amount)} ریال` },
                { label: 'پرداخت‌شده', value: `${fmt(charge.paid_amount)} ریال` },
                ...(Number(charge.remaining_amount) > 0 ? [{ label: 'مانده', value: `${fmt(charge.remaining_amount)} ریال`, danger: true }] : []),
                ...(charge.notes ? [{ label: 'یادداشت', value: charge.notes }] : []),
              ].map(r => (
                <div key={r.label}
                  className="flex items-start justify-between px-3 py-2.5 rounded-lg"
                  style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '0.5px solid rgba(255,255,255,0.05)' }}>
                  <div className="text-sm text-gray-steel">{r.label}</div>
                  <div className={`text-sm font-bold whitespace-nowrap ${r.danger ? 'text-red-400' : 'text-white'}`}>{r.value}</div>
                </div>
              ))}
            </div>

            {charge.installments?.length > 0 && (
              <div className="mt-4">
                <div className="text-xs font-bold text-gray-steel mb-1.5">💳 پرداخت‌ها</div>
                <div className="space-y-1">
                  {charge.installments.map(r => (
                    <div key={r.id} className="flex items-center justify-between text-[11px] bg-white/5 rounded-lg px-3 py-1.5">
                      <span className="text-white">{r.account_name || '—'} — {fmt(r.amount)} ریال</span>
                      <span className="text-gray-steel">{jalaliText(r.date)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-gray-steel">
              <span>وضعیت: {badge ? <span className={`badge ${badge.cls}`} style={{ fontSize: 10, padding: '1px 8px' }}>{badge.label}</span> : charge.status}</span>
              {can('expenses_edit') && (
                <button
                  onClick={() => { if (window.confirm(`حذف «${charge.title}»؟ سندهای حسابداری‌اش برگشت می‌خورند.`)) delMut.mutate(charge.id) }}
                  disabled={delMut.isPending}
                  className="text-xs px-2 py-1 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all disabled:opacity-50">
                  {delMut.isPending ? 'در حال حذف...' : '🗑 حذف هزینه'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── مودال هزینه تکرارشونده (جدید / ویرایش) ───────────────────
function RecurringFormModal({ recurring, onClose }) {
  const qc = useQueryClient()
  const todayIso = todayTehran()
  const [form, setForm] = useState({
    title: recurring?.title || '',
    category: recurring ? String(recurring.category ?? '') : '',
    monthly_amount: recurring ? String(recurring.monthly_amount ?? '') : '',
    contact: recurring ? String(recurring.contact ?? '') : '',
    deposit_amount: recurring ? String(recurring.deposit_amount ?? '') : '',
    start_date: recurring?.start_date || todayIso,
    is_active: recurring ? !!recurring.is_active : true,
  })
  const [msg, setMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-plain'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const saveMut = useMutation({
    mutationFn: (payload) => recurring
      ? api.patch(`/expenses/recurring/${recurring.id}/`, payload).then(r => r.data)
      : api.post('/expenses/recurring/', payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['expenses-recurring'])
      toast.success(recurring ? 'هزینه تکرارشونده ویرایش شد' : 'هزینه تکرارشونده ساخته شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ذخیره' }),
  })

  function handleSubmit() {
    if (!form.title.trim()) return setMsg({ type: 'error', text: 'عنوان را وارد کنید' })
    if (!form.category) return setMsg({ type: 'error', text: 'سر فصل را انتخاب کنید' })
    if (!(Number(parseAmount(form.monthly_amount)) > 0)) return setMsg({ type: 'error', text: 'مبلغ ماهانه را وارد کنید' })
    if (!form.start_date) return setMsg({ type: 'error', text: 'تاریخ شروع را وارد کنید' })
    setMsg(null)
    saveMut.mutate({
      title: form.title.trim(),
      category: Number(form.category),
      monthly_amount: Number(parseAmount(form.monthly_amount)) || 0,
      contact: form.contact ? Number(form.contact) : null,
      deposit_amount: form.deposit_amount ? Number(parseAmount(form.deposit_amount)) : null,
      start_date: form.start_date,
      is_active: !!form.is_active,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">{recurring ? `✏️ ویرایش — ${recurring.title}` : '➕ هزینه تکرارشونده جدید'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-steel block mb-1">عنوان *</label>
            <input value={form.title} onChange={e => set('title', e.target.value)}
              className="input text-sm" placeholder="مثلاً اجاره دفتر" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">سر فصل *</label>
            <CategorySelect value={form.category} onChange={v => set('category', v)} type="recurring" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">مبلغ ماهانه (ریال) *</label>
            <AmountInput value={form.monthly_amount} onChange={e => set('monthly_amount', e.target.value)}
              className="input text-sm" placeholder="0" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">طرف حساب</label>
            <SearchSelect value={form.contact} onChange={v => set('contact', v)}
              placeholder="جستجو و انتخاب طرف حساب... (اختیاری)"
              options={contacts.map(c => ({ value: c.id, label: c.name, sub: c.phone }))} />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">ودیعه (ریال)</label>
            <AmountInput value={form.deposit_amount} onChange={e => set('deposit_amount', e.target.value)}
              className="input text-sm" placeholder="0" />
            <div className="text-[10px] text-gray-steel mt-1">صرفاً اطلاع — در سند ماه لحاظ نمی‌شود</div>
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">تاریخ شروع</label>
            <JalaliDateInput value={form.start_date} onChange={v => set('start_date', v)} className="input text-sm" />
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={!!form.is_active} onChange={e => set('is_active', e.target.checked)}
              className="accent-[#FBC02D]" />
            فعال — در «صدور سند ماه» لحاظ شود
          </label>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : '✓ ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال کارتکس هزینه تکرارشونده ────────────────────────────
function RecurringKardexModal({ recurringId, onClose }) {
  const { can } = usePermissions()
  const delMut = useChargeDelete()
  const { data, isLoading } = useQuery({
    queryKey: ['expenses-recurring-kardex', recurringId],
    queryFn: () => api.get(`/expenses/recurring/${recurringId}/kardex/`).then(r => r.data),
  })
  const recurring = data?.recurring
  const charges = data?.charges || []

  const tdS = { padding: '8px 10px' }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="card p-6 w-full max-w-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">📒 کارت هزینه — {recurring?.title || '...'}</h2>
            {recurring && (
              <div className="text-xs text-gray-steel mt-1">
                {recurring.category_name} — مبلغ ماهانه: <b className="text-white">{fmt(recurring.monthly_amount)}</b> ریال
                {recurring.contact_name ? ` — ${recurring.contact_name}` : ''}
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : charges.length === 0 ? (
          <div className="text-center py-10 text-gray-steel text-sm">سندی برای این هزینه صادر نشده — با «صدور سند ماه» سند بسازید</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['ماه', 'مبلغ', 'پرداخت‌شده', 'مانده', 'وضعیت', ''].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {charges.map((c, i) => {
                  const badge = STATUS_BADGE[c.status] || STATUS_BADGE.draft
                  return (
                    <tr key={c.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ ...tdS, fontWeight: 600, whiteSpace: 'nowrap' }}>{monthLabelFromGregorian(c.year, c.month)}</td>
                      <td style={tdS}>{fmt(c.amount)} ت</td>
                      <td style={tdS}>{fmt(c.paid_amount)} ت</td>
                      <td style={{ ...tdS, color: Number(c.remaining_amount) > 0 ? '#FF3B3B' : 'var(--color-text-secondary)' }}>{fmt(c.remaining_amount)} ت</td>
                      <td style={tdS}>
                        <span className={`badge ${badge.cls}`} style={{ fontSize: 10, padding: '2px 8px' }}>{badge.label}</span>
                      </td>
                      <td style={tdS}>
                        {can('expenses_edit') && (
                          <button
                            onClick={() => { if (window.confirm(`حذف «${recurring?.title || c.title}»؟ سندهای حسابداری‌اش برگشت می‌خورند.`)) delMut.mutate(c.id) }}
                            disabled={delMut.isPending}
                            className="text-red-400 hover:text-red-300 text-sm disabled:opacity-50">🗑</button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── مودال صدور سند ماه ───────────────────────────────────────
function AccrueModal({ onClose }) {
  const qc = useQueryClient()
  const [curJy, curJm] = gregorianToJalali(...todayTehranParts())
  const [jy, setJy] = useState(curJy)
  const [jm, setJm] = useState(curJm)
  const [gy, gm] = jalaliToGregorian(jy, jm, 1)
  const monthLabel = `${JALALI_MONTHS[jm - 1]} ${jy.toLocaleString('fa-IR')}`

  const accrueMut = useMutation({
    mutationFn: () => api.post('/expenses/accrue-month/', { year: gy, month: gm }).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['expenses-charges'])
      qc.invalidateQueries(['expenses-recurring-kardex'])
      qc.invalidateQueries(['expenses-investors-kardex'])
      qc.invalidateQueries(['expenses-recurring'])
      toast.success(`سند ماه ${monthLabel} صادر شد — تکرارشونده: ${Number(r.recurring).toLocaleString('fa-IR')} | سرمایه‌گذار: ${Number(r.investor).toLocaleString('fa-IR')}`)
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">🧾 صدور سند ماه</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="bg-white/5 rounded-xl px-4 py-3 mb-4 text-xs text-gray-steel leading-5">
          برای همه هزینه‌های تکرارشونده فعال سند بدهی این ماه صادر می‌شود و سود روزشمار سرمایه‌گذاران محاسبه و ثبت می‌گردد.
        </div>
        <MonthSelector jy={jy} jm={jm} setJy={setJy} setJm={setJm} label={monthLabel} />
        <div className="flex gap-3 mt-5">
          <button onClick={() => accrueMut.mutate()} disabled={accrueMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {accrueMut.isPending ? 'در حال صدور...' : '✓ صدور سند'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── تب هزینه‌های تکرارشونده ──────────────────────────────────
function RecurringTab() {
  const { can } = usePermissions()
  const [formFor, setFormFor] = useState(null)   // null | {} (new) | recurring obj
  const [kardexId, setKardexId] = useState(null)
  const [accrueOpen, setAccrueOpen] = useState(false)

  const { data: recurring = [], isLoading } = useQuery({
    queryKey: ['expenses-recurring'],
    queryFn: () => api.get('/expenses/recurring/').then(r => r.data),
  })

  const tdS = { padding: '10px 12px' }
  return (
    <div>
      <div className="flex items-center justify-end mb-4 flex-wrap gap-2">
        {can('expenses_edit') && (
          <>
            <button onClick={() => setAccrueOpen(true)}
              className="btn-secondary text-sm px-4 py-2 ml-2">
              🧾 صدور سند ماه
            </button>
            <button onClick={() => setFormFor({})}
              className="btn-primary text-sm px-4 py-2">
              + هزینه جدید
            </button>
          </>
        )}
      </div>

      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : recurring.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-3">➕</div>
            <div className="text-gray-steel text-sm">هزینه تکرارشونده‌ای تعریف نشده</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['عنوان', 'سر فصل', 'مبلغ ماهانه', 'طرف حساب', 'ودیعه', 'وضعیت', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recurring.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ ...tdS, fontWeight: 600 }}>{r.title}</td>
                    <td style={tdS}>{r.category_name || '—'}</td>
                    <td style={{ ...tdS, fontWeight: 700, color: '#FBC02D' }}>{fmt(r.monthly_amount)} ت</td>
                    <td style={{ ...tdS, color: 'var(--color-text-secondary)' }}>{r.contact_name || '—'}</td>
                    <td style={tdS}>{Number(r.deposit_amount) ? fmt(r.deposit_amount) + ' ت' : '—'}</td>
                    <td style={tdS}>
                      <span className={`badge ${r.is_active ? 'badge-success' : 'badge'}`} style={{ fontSize: 10, padding: '2px 8px' }}>
                        {r.is_active ? 'فعال' : 'غیرفعال'}
                      </span>
                    </td>
                    <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
                      <button onClick={() => setKardexId(r.id)}
                        className="text-xs px-2 py-1 rounded-lg bg-white/10 text-gray-steel hover:bg-white/20 transition-all ml-1">
                        📒 کارت
                      </button>
                      {can('expenses_edit') && (
                        <button onClick={() => setFormFor(r)}
                          className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all ml-1">
                          ✏️ ویرایش
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {formFor && <RecurringFormModal recurring={formFor.id ? formFor : null} onClose={() => setFormFor(null)} />}
      {kardexId && <RecurringKardexModal recurringId={kardexId} onClose={() => setKardexId(null)} />}
      {accrueOpen && <AccrueModal onClose={() => setAccrueOpen(false)} />}
    </div>
  )
}

// ─── مودال ثبت هزینه متفرقه ───────────────────────────────────
function GeneralChargeModal({ onClose }) {
  const qc = useQueryClient()
  const todayIso = todayTehran()
  const [form, setForm] = useState({
    title: '', category: '', amount: '', date: todayIso, contact: '', notes: '',
  })
  const [msg, setMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-plain'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const saveMut = useMutation({
    mutationFn: () => api.post('/expenses/charges/', {
      title: form.title.trim(),
      category: form.category ? Number(form.category) : null,
      contact: form.contact ? Number(form.contact) : null,
      amount: Number(parseAmount(form.amount)) || 0,
      date: form.date,
      notes: form.notes,
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['expenses-charges'])
      toast.success('سند هزینه صادر شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت' }),
  })

  function handleSubmit() {
    if (!form.title.trim()) return setMsg({ type: 'error', text: 'عنوان را وارد کنید' })
    if (!(Number(parseAmount(form.amount)) > 0)) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    if (!form.date) return setMsg({ type: 'error', text: 'تاریخ را وارد کنید' })
    setMsg(null)
    saveMut.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">➕ ثبت هزینه متفرقه</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-steel block mb-1">عنوان *</label>
            <input value={form.title} onChange={e => set('title', e.target.value)}
              className="input text-sm" placeholder="مثلاً خرید لوازم اداری" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">سر فصل</label>
            <CategorySelect value={form.category} onChange={v => set('category', v)} type="general" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">مبلغ (ریال) *</label>
            <AmountInput value={form.amount} onChange={e => set('amount', e.target.value)}
              className="input text-sm" placeholder="0" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">تاریخ *</label>
            <JalaliDateInput value={form.date} onChange={v => set('date', v)} className="input text-sm" />
            <div className="text-[10px] text-gray-steel mt-1">تاریخ باید در ماه انتخاب‌شده باشد</div>
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">طرف حساب</label>
            <SearchSelect value={form.contact} onChange={v => set('contact', v)}
              placeholder="جستجو و انتخاب طرف حساب... (اختیاری)"
              options={contacts.map(c => ({ value: c.id, label: c.name, sub: c.phone }))} />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">یادداشت</label>
            <input value={form.notes} onChange={e => set('notes', e.target.value)}
              className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ثبت...' : '✓ ثبت و صدور سند بدهی'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── تب هزینه‌های متفرقه ──────────────────────────────────────
function GeneralTab() {
  const { can } = usePermissions()
  const delMut = useChargeDelete()
  const [addOpen, setAddOpen] = useState(false)
  const [detailId, setDetailId] = useState(null)

  const [curJy, curJm] = gregorianToJalali(...todayTehranParts())
  const [jy, setJy] = useState(curJy)
  const [jm, setJm] = useState(curJm)
  const monthLabel = `${JALALI_MONTHS[jm - 1]} ${jy.toLocaleString('fa-IR')}`
  // ماه جلالی ممکن است دو ماه میلادی را بپوشاند → فیلتر با بازه تاریخ واقعی
  const [gFromY, gFromM, gFromD] = jalaliToGregorian(jy, jm, 1)
  const dateFrom = `${gFromY}-${String(gFromM).padStart(2, '0')}-${String(gFromD).padStart(2, '0')}`
  const [gToY, gToM, gToD] = jalaliToGregorian(jy, jm, jalaliMonthDays(jy, jm))
  const dateTo = `${gToY}-${String(gToM).padStart(2, '0')}-${String(gToD).padStart(2, '0')}`

  const { data: charges = [], isLoading } = useQuery({
    queryKey: ['expenses-charges', dateFrom, dateTo, 'general'],
    queryFn: () => api.get('/expenses/charges/', { params: { date_from: dateFrom, date_to: dateTo, source: 'general' } }).then(r => r.data),
  })

  const tdS = { padding: '10px 12px' }
  return (
    <div>
      <div className="flex items-end justify-between mb-4 flex-wrap gap-2">
        <MonthSelector jy={jy} jm={jm} setJy={setJy} setJm={setJm} label={monthLabel} />
        {can('expenses_edit') && (
          <button onClick={() => setAddOpen(true)}
            className="btn-primary text-sm px-4 py-2">
            + ثبت هزینه
          </button>
        )}
      </div>

      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : charges.length === 0 ? (
          <div className="text-center py-12 text-gray-steel text-sm">هزینه متفرقه‌ای برای این ماه ثبت نشده</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['عنوان', 'سر فصل', 'مبلغ', 'پرداخت‌شده', 'مانده', 'وضعیت', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {charges.map((c, i) => {
                  const badge = STATUS_BADGE[c.status] || STATUS_BADGE.draft
                  return (
                    <tr key={c.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ ...tdS, fontWeight: 600 }}>{c.title}</td>
                      <td style={tdS}>{c.category_name || '—'}</td>
                      <td style={{ ...tdS, fontWeight: 700, color: '#FBC02D' }}>{fmt(c.amount)} ت</td>
                      <td style={tdS}>{fmt(c.paid_amount)} ت</td>
                      <td style={{ ...tdS, color: Number(c.remaining_amount) > 0 ? '#FF3B3B' : 'var(--color-text-secondary)' }}>{fmt(c.remaining_amount)} ت</td>
                      <td style={tdS}>
                        <span className={`badge ${badge.cls}`} style={{ fontSize: 10, padding: '2px 8px' }}>{badge.label}</span>
                      </td>
                      <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
                        <button onClick={() => setDetailId(c.id)}
                          className="text-xs px-2 py-1 rounded-lg bg-white/10 text-gray-steel hover:bg-white/20 transition-all ml-1">
                          👁 جزئیات
                        </button>
                        {can('expenses_edit') && (
                          <button
                            onClick={() => { if (window.confirm(`حذف «${c.title}»؟ سندهای حسابداری‌اش برگشت می‌خورند.`)) delMut.mutate(c.id) }}
                            disabled={delMut.isPending}
                            className="text-xs px-2 py-1 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all ml-1 disabled:opacity-50">
                            🗑 حذف
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="text-xs text-gray-steel mt-3">
          💡 پرداخت هزینه‌ها از منوی «دریافت و پرداخت» — طرف‌حساب را انتخاب کنید و «هزینه باز» را برگزینید.
        </div>
      </div>

      {addOpen && <GeneralChargeModal onClose={() => setAddOpen(false)} />}
      {detailId && <ChargeDetailModal chargeId={detailId} onClose={() => setDetailId(null)} />}
    </div>
  )
}

// ─── مودال سرمایه‌گذار جدید ───────────────────────────────────
function InvestorFormModal({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    mode: 'new', contact: '', name: '', phone: '', annual_rate: '', is_active: true,
  })
  const [msg, setMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts-plain'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const saveMut = useMutation({
    mutationFn: () => api.post('/expenses/investors/', {
      ...(form.mode === 'existing' && form.contact
        ? { contact: Number(form.contact) }
        : { name: form.name.trim(), phone: form.phone || '' }),
      annual_rate: Number(form.annual_rate) || 0,
      is_active: !!form.is_active,
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['expenses-investors'])
      toast.success('سرمایه‌گذار ثبت شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت' }),
  })

  function handleSubmit() {
    if (form.mode === 'existing' && !form.contact) return setMsg({ type: 'error', text: 'طرف حساب را انتخاب کنید' })
    if (form.mode === 'new' && !form.name.trim()) return setMsg({ type: 'error', text: 'نام سرمایه‌گذار را وارد کنید' })
    setMsg(null)
    saveMut.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">➕ سرمایه‌گذار جدید</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-steel block mb-1">انتخاب طرف حساب</label>
            <select value={form.mode} onChange={e => set('mode', e.target.value)} className="input text-sm">
              <option value="new">➕ شخص جدید (نام + موبایل)</option>
              <option value="existing">👤 انتخاب از طرف حساب‌های موجود</option>
            </select>
          </div>
          {form.mode === 'existing' ? (
            <div>
              <label className="text-xs text-gray-steel block mb-1">طرف حساب *</label>
              <SearchSelect value={form.contact} onChange={v => set('contact', v)}
                placeholder="جستجو و انتخاب طرف حساب..."
                options={contacts.map(c => ({ value: c.id, label: c.name, sub: c.phone }))} />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-steel block mb-1">نام *</label>
                <input value={form.name} onChange={e => set('name', e.target.value)}
                  className="input text-sm" placeholder="نام سرمایه‌گذار" />
              </div>
              <div>
                <label className="text-xs text-gray-steel block mb-1">موبایل</label>
                <input value={form.phone} onChange={e => set('phone', e.target.value)}
                  className="input text-sm" placeholder="09..." dir="ltr" />
              </div>
            </div>
          )}
          <div>
            <label className="text-xs text-gray-steel block mb-1">نرخ سود سالانه (٪)</label>
            <input type="number" step="0.01" value={form.annual_rate} onChange={e => set('annual_rate', e.target.value)}
              className="input text-sm" placeholder="مثلاً 18" />
            <div className="text-[10px] text-gray-steel mt-1">نرخ سالانه — سود روزشمار: اصل × نرخ × روزها ÷ ۳۶۵</div>
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={!!form.is_active} onChange={e => set('is_active', e.target.checked)}
              className="accent-[#FBC02D]" />
            فعال — در «صدور سند ماه» سودش محاسبه شود
          </label>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : '✓ ذخیره سرمایه‌گذار'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال ویرایش سرمایه‌گذار (نرخ / وضعیت) ───────────────────
function InvestorEditModal({ investor, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    annual_rate: String(investor.annual_rate ?? ''),
    is_active: !!investor.is_active,
  })
  const [msg, setMsg] = useState(null)

  const saveMut = useMutation({
    mutationFn: () => api.patch(`/expenses/investors/${investor.id}/`, {
      annual_rate: Number(form.annual_rate) || 0,
      is_active: !!form.is_active,
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['expenses-investors'])
      toast.success('سرمایه‌گذار ویرایش شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ذخیره' }),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">✏️ ویرایش — {investor.contact_name}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-steel block mb-1">نرخ سود سالانه (٪)</label>
            <input type="number" step="0.01" value={form.annual_rate}
              onChange={e => setForm(f => ({ ...f, annual_rate: e.target.value }))}
              className="input text-sm" placeholder="مثلاً 18" />
            <div className="text-[10px] text-gray-steel mt-1">نرخ سالانه — سود روزشمار: اصل × نرخ × روزها ÷ ۳۶۵</div>
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={!!form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
              className="accent-[#FBC02D]" />
            فعال — در «صدور سند ماه» سودش محاسبه شود
          </label>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : '✓ ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال گردش سرمایه (واریز / برداشت) ───────────────────────
function MovementModal({ investor, onClose }) {
  const qc = useQueryClient()
  const todayIso = todayTehran()
  const [form, setForm] = useState({
    movement_type: 'deposit', date: todayIso, amount: '', account: '', note: '',
  })
  const [msg, setMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })
  const irrAccounts = accounts.filter(a => a.currency === 'IRR')

  const saveMut = useMutation({
    mutationFn: () => api.post('/expenses/investor-movements/', {
      investor: investor.id,
      movement_type: form.movement_type,
      date: form.date,
      amount: Number(parseAmount(form.amount)) || 0,
      account: form.movement_type === 'withdraw' ? Number(form.account) : (form.account ? Number(form.account) : null),
      note: form.note,
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['expenses-investors'])
      qc.invalidateQueries(['expenses-investors-kardex'])
      qc.invalidateQueries(['accounts'])
      toast.success('گردش سرمایه ثبت شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ثبت' }),
  })

  function handleSubmit() {
    if (!(Number(parseAmount(form.amount)) > 0)) return setMsg({ type: 'error', text: 'مبلغ را وارد کنید' })
    if (!form.date) return setMsg({ type: 'error', text: 'تاریخ را وارد کنید' })
    if (form.movement_type === 'withdraw' && !form.account) return setMsg({ type: 'error', text: 'برای برداشت، حساب بانکی را انتخاب کنید' })
    setMsg(null)
    saveMut.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">💰 گردش سرمایه — {investor.contact_name}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-steel block mb-1">نوع گردش *</label>
            <select value={form.movement_type} onChange={e => set('movement_type', e.target.value)} className="input text-sm">
              {MOVEMENT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">مبلغ (ریال) *</label>
            <AmountInput value={form.amount} onChange={e => set('amount', e.target.value)}
              className="input text-sm" placeholder="0" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">تاریخ *</label>
            <JalaliDateInput value={form.date} onChange={v => set('date', v)} className="input text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">حساب بانکی {form.movement_type === 'withdraw' ? '*' : ''}</label>
            <SearchSelect value={form.account} onChange={v => set('account', v)}
              placeholder={form.movement_type === 'withdraw' ? 'انتخاب حساب برداشت...' : 'انتخاب حساب... (اختیاری)'}
              options={irrAccounts.map(a => ({ value: a.id, label: a.name }))} />
            {form.movement_type === 'withdraw' && irrAccounts.length === 0 && (
              <div className="text-[10px] text-red-400 mt-1">حساب ریالی فعالی تعریف نشده — اول در مدیریت بانک بسازید</div>
            )}
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">یادداشت</label>
            <input value={form.note} onChange={e => set('note', e.target.value)}
              className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ثبت...' : '✓ ثبت گردش'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال کارتکس سرمایه‌گذار ─────────────────────────────────
function InvestorKardexModal({ investorId, onClose }) {
  const { can } = usePermissions()
  const delMut = useChargeDelete()
  const { data, isLoading } = useQuery({
    queryKey: ['expenses-investors-kardex', investorId],
    queryFn: () => api.get(`/expenses/investors/${investorId}/kardex/`).then(r => r.data),
  })
  const investor = data?.investor
  const movements = data?.movements || []
  const profits = data?.profits || []

  const tdS = { padding: '8px 10px' }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="card p-6 w-full max-w-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">📒 کارت سرمایه‌گذار — {investor?.contact_name || '...'}</h2>
            {investor && (
              <div className="text-xs text-gray-steel mt-1">
                نرخ سالانه: <b className="text-white">{Number(investor.annual_rate).toLocaleString('fa-IR')}٪</b>
                {' — '}اصل سرمایه: <b className="text-white">{fmt(data?.principal)} ریال</b>
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : (
          <div className="space-y-5">
            <div>
              <div className="text-xs font-bold text-gray-steel mb-2">💰 گردش‌های سرمایه</div>
              {movements.length === 0 ? (
                <div className="text-center py-4 text-gray-steel text-[11px] bg-white/5 rounded-lg">گردشی ثبت نشده</div>
              ) : (
                <div className="overflow-x-auto">
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                        {['نوع', 'تاریخ', 'مبلغ', 'حساب', 'توضیح'].map(h => (
                          <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {movements.map((m, i) => (
                        <tr key={m.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                          <td style={tdS}>
                            <span className={`badge ${m.movement_type === 'deposit' ? 'badge-success' : 'badge-gold'}`} style={{ fontSize: 10, padding: '2px 8px' }}>
                              {MOVEMENT_TYPES.find(t => t.value === m.movement_type)?.label || m.movement_type}
                            </span>
                          </td>
                          <td style={{ ...tdS, whiteSpace: 'nowrap' }}>{jalaliText(m.date)}</td>
                          <td style={{ ...tdS, fontWeight: 700, color: Number(m.signed_amount) >= 0 ? '#00C896' : '#FF3B3B', whiteSpace: 'nowrap' }}>
                            {Number(m.signed_amount) >= 0 ? '+' : '−'}{fmt(Math.abs(Number(m.signed_amount)))} ت
                          </td>
                          <td style={tdS}>{m.account_name || '—'}</td>
                          <td style={{ ...tdS, color: 'var(--color-text-secondary)', maxWidth: 120 }} className="truncate">{m.note || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div>
              <div className="text-xs font-bold text-gray-steel mb-2">📈 سودهای سرمایه‌گذاری</div>
              {profits.length === 0 ? (
                <div className="text-center py-4 text-gray-steel text-[11px] bg-white/5 rounded-lg">سودی ثبت نشده — با «صدور سند ماه» سود ماهانه صادر می‌شود</div>
              ) : (
                <div className="overflow-x-auto">
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                        {['ماه', 'مبلغ سود', 'وضعیت', 'پرداخت‌شده', 'مانده', ''].map(h => (
                          <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {profits.map((p, i) => {
                        const badge = STATUS_BADGE[p.status] || STATUS_BADGE.draft
                        return (
                          <tr key={p.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                            <td style={{ ...tdS, fontWeight: 600, whiteSpace: 'nowrap' }}>{monthLabelFromGregorian(p.year, p.month)}</td>
                            <td style={{ ...tdS, fontWeight: 700, color: '#FBC02D' }}>{fmt(p.amount)} ت</td>
                            <td style={tdS}>
                              <span className={`badge ${badge.cls}`} style={{ fontSize: 10, padding: '2px 8px' }}>{badge.label}</span>
                            </td>
                            <td style={tdS}>{fmt(p.paid_amount)} ت</td>
                            <td style={{ ...tdS, color: Number(p.remaining_amount) > 0 ? '#FF3B3B' : 'var(--color-text-secondary)' }}>{fmt(p.remaining_amount)} ت</td>
                            <td style={tdS}>
                              {can('expenses_edit') && (
                                <button
                                  onClick={() => { if (window.confirm(`حذف «سود ${monthLabelFromGregorian(p.year, p.month)}»؟ سندهای حسابداری‌اش برگشت می‌خورند.`)) delMut.mutate(p.id) }}
                                  disabled={delMut.isPending}
                                  className="text-red-400 hover:text-red-300 text-sm disabled:opacity-50">🗑</button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── تب سرمایه‌گذاران ─────────────────────────────────────────
function InvestorsTab() {
  const { can } = usePermissions()
  const [addOpen, setAddOpen] = useState(false)
  const [editFor, setEditFor] = useState(null)
  const [movementFor, setMovementFor] = useState(null)
  const [kardexId, setKardexId] = useState(null)

  const { data: investors = [], isLoading } = useQuery({
    queryKey: ['expenses-investors'],
    queryFn: () => api.get('/expenses/investors/').then(r => r.data),
  })

  const tdS = { padding: '10px 12px' }
  return (
    <div>
      <div className="flex items-center justify-end mb-4">
        {can('expenses_edit') && (
          <button onClick={() => setAddOpen(true)}
            className="btn-primary text-sm px-4 py-2">
            + سرمایه‌گذار
          </button>
        )}
      </div>

      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : investors.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-3">➕</div>
            <div className="text-gray-steel text-sm">سرمایه‌گذاری تعریف نشده</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['نام', 'موبایل', 'نرخ سالانه (٪)', 'اصل سرمایه', 'وضعیت', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {investors.map((inv, i) => (
                  <tr key={inv.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ ...tdS, fontWeight: 600 }}>{inv.contact_name}</td>
                    <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{inv.contact_phone || '—'}</td>
                    <td style={tdS}>{Number(inv.annual_rate).toLocaleString('fa-IR')}٪</td>
                    <td style={{ ...tdS, fontWeight: 700, color: '#FBC02D' }}>{fmt(inv.principal)} ت</td>
                    <td style={tdS}>
                      <span className={`badge ${inv.is_active ? 'badge-success' : 'badge'}`} style={{ fontSize: 10, padding: '2px 8px' }}>
                        {inv.is_active ? 'فعال' : 'غیرفعال'}
                      </span>
                    </td>
                    <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
                      <button onClick={() => setKardexId(inv.id)}
                        className="text-xs px-2 py-1 rounded-lg bg-white/10 text-gray-steel hover:bg-white/20 transition-all ml-1">
                        📒 کارت
                      </button>
                      {can('expenses_edit') && (
                        <>
                          <button onClick={() => setEditFor(inv)}
                            className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all ml-1">
                            ✏️ ویرایش
                          </button>
                          <button onClick={() => setMovementFor(inv)}
                            className="text-xs px-2 py-1 rounded-lg bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-all ml-1">
                            💰 گردش سرمایه
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {addOpen && <InvestorFormModal onClose={() => setAddOpen(false)} />}
      {editFor && <InvestorEditModal investor={editFor} onClose={() => setEditFor(null)} />}
      {movementFor && <MovementModal investor={movementFor} onClose={() => setMovementFor(null)} />}
      {kardexId && <InvestorKardexModal investorId={kardexId} onClose={() => setKardexId(null)} />}
    </div>
  )
}

// ─── صفحه اصلی هزینه‌ها ───────────────────────────────────────
export default function ExpensesPage() {
  const { can } = usePermissions()
  const [tab, setTab] = useState('recurring')

  if (!can('expenses_view')) {
    return (
      <div className="container-main py-20 text-center">
        <div className="text-5xl mb-4">🔒</div>
        <h2 className="font-display font-bold text-xl text-white mb-3">دسترسی محدود</h2>
        <p className="text-gray-steel text-sm">برای مشاهده هزینه‌ها نیاز به دسترسی مخصوص دارید.</p>
      </div>
    )
  }

  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">💸 هزینه‌ها</h1>

      <div className="flex gap-2 mb-6 border-b border-white/10">
        {[
          { key: 'recurring', label: '🔁 تکرارشونده' },
          { key: 'general',   label: '🧾 متفرقه' },
          { key: 'investors', label: '📈 سرمایه‌گذاران' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${tab === t.key ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'recurring' && <RecurringTab />}
      {tab === 'general' && <GeneralTab />}
      {tab === 'investors' && <InvestorsTab />}
    </div>
  )
}
