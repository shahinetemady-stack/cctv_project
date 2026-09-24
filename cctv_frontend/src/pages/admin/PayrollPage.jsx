import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import usePermissions from '../../hooks/usePermissions'
import AmountInput, { parseAmount } from '../../components/ui/AmountInput'
import JalaliDateInput from '../../components/ui/JalaliDateInput'
import SearchSelect from '../../components/ui/SearchSelect'
import { jalaliToGregorian, gregorianToJalali, JALALI_MONTHS, jalaliText } from '../../utils/jalali'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const STATUS_BADGE = {
  draft:     { cls: 'badge-gold',          label: 'پیش‌نویس' },
  confirmed: { cls: 'badge-success',       label: 'تأیید شده' },
  paid:      { cls: 'badge',               label: '💳 پرداخت شده' },
}

const LEAVE_TYPES = [
  { value: 'entitled', label: 'استحقاقی' },
  { value: 'sick',     label: 'استعلاجی' },
  { value: 'unpaid',   label: 'بدون حقوق' },
]
const LEAVE_TYPE_LABEL = Object.fromEntries(LEAVE_TYPES.map(t => [t.value, t.label]))

const MODULES = [
  { key: 'has_base_salary',       label: 'حقوق ثابت',           desc: 'پرداخت ماهانه یک مبلغ ثابت به این پرسنل' },
  { key: 'has_commission_personal', label: 'پورسانت فروش شخصی', desc: 'محاسبه پلکانی روی فروش شخصی ماه' },
  { key: 'has_commission_total',  label: 'سهم فروش مجموعه',     desc: 'محاسبه پلکانی روی فروش کل ماه مجموعه' },
  { key: 'has_bonus_penalty',     label: 'تشویقی و تنبیه',      desc: 'ثبت و اعمال آیتم‌های انضباطی در فیش حقوقی' },
  { key: 'has_annual_bonus',      label: 'عیدی',                desc: 'محاسبه و پرداخت عیدی پایان سال' },
  { key: 'has_leave_management',  label: 'مدیریت مرخصی',        desc: 'کسر حقوق روزهای مرخصی بدون حقوق' },
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

// ─── مودال پرداخت فیش — انتخاب حساب ریالی + تاریخ + مبلغ قسط ───
function PayModal({ slip, onClose }) {
  const qc = useQueryClient()
  const remaining = Math.max(0, Number(slip.net_amount || 0) - Number(slip.paid_amount || 0))
  const [accountId, setAccountId] = useState('')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [amount, setAmount] = useState(String(remaining))
  const [msg, setMsg] = useState(null)

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })
  const irrAccounts = accounts.filter(a => a.currency === 'IRR')

  const payMut = useMutation({
    mutationFn: () => api.post(`/payroll/payslips/${slip.id}/pay/`, {
      account_id: accountId, date, amount: Number(parseAmount(amount)) || 0,
    }).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['payroll-payslips'])
      qc.invalidateQueries(['payroll-payslip'])
      qc.invalidateQueries(['accounts'])
      toast.success(r.status === 'paid'
        ? 'فیش کاملاً پرداخت شد'
        : `قسط ثبت شد — مانده: ${fmt(r.remaining_amount)} ریال`)
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  function submit() {
    if (!accountId) return setMsg({ type: 'error', text: 'حساب بانکی را انتخاب کنید' })
    if (!date) return setMsg({ type: 'error', text: 'تاریخ پرداخت را وارد کنید' })
    if (!(Number(parseAmount(amount)) > 0)) return setMsg({ type: 'error', text: 'مبلغ این قسط را وارد کنید' })
    setMsg(null)
    payMut.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">💳 پرداخت حقوق — {slip.staff_name}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="bg-white/5 rounded-xl px-4 py-3 mb-4 text-sm flex items-center justify-between">
          <span className="text-gray-steel">خالص قابل پرداخت</span>
          <span className="font-bold text-brand">{fmt(slip.net_amount)} ریال</span>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-steel block mb-1">مبلغ این قسط (ریال)</label>
            <AmountInput value={amount} onChange={e => setAmount(e.target.value)}
              className="input text-sm" placeholder="0" />
            <div className="text-[10px] text-gray-steel mt-1">مانده فیش: {fmt(remaining)} ریال</div>
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">حساب بانکی (ریالی) *</label>
            <SearchSelect
              value={accountId}
              onChange={setAccountId}
              placeholder="جستجو و انتخاب حساب..."
              options={irrAccounts.map(a => ({ value: a.id, label: a.name }))}
            />
            {irrAccounts.length === 0 && (
              <div className="text-[10px] text-red-400 mt-1">حساب ریالی فعالی تعریف نشده — اول در مدیریت بانک بسازید</div>
            )}
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">تاریخ پرداخت</label>
            <JalaliDateInput value={date} onChange={setDate} className="input text-sm" />
          </div>
        </div>
        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}
        <div className="flex gap-3 mt-5">
          <button onClick={submit} disabled={payMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {payMut.isPending ? 'در حال پرداخت...' : '✓ تأیید و صدور سند پرداخت'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال فیش حقوقی قابل چاپ ─────────────────────────────────
function PayslipDetailModal({ slipId, monthLabel, onClose }) {
  const { data: slip, isLoading } = useQuery({
    queryKey: ['payroll-payslip', slipId],
    queryFn: () => api.get(`/payroll/payslips/${slipId}/`).then(r => r.data),
  })

  const badge = slip && STATUS_BADGE[slip.status]

  // ردیف‌های مؤلفه‌ها — فقط موارد غیرصفر نمایش داده می‌شوند
  const rows = slip ? [
    { label: 'حقوق ثابت', value: slip.base_amount },
    { label: 'پورسانت فروش شخصی', value: slip.personal_commission_amount,
      sub: `فروش ماه: ${fmt(slip.personal_sales)} ریال` },
    { label: 'سهم فروش مجموعه', value: slip.total_sales_share_amount,
      sub: `فروش کل: ${fmt(slip.total_sales)} ریال` },
    { label: 'تشویقی / تنبیه', value: slip.bonus_penalty_amount },
    { label: 'عیدی', value: slip.annual_bonus_amount },
    { label: 'کسر مرخصی', value: slip.leave_deduction, negative: true,
      sub: `مرخصی بدون حقوق: ${Number(slip.unpaid_used || 0).toLocaleString('fa-IR')} روز` },
    { label: 'پرداخت‌شده', value: slip.paid_amount },
    ...(Number(slip.remaining_amount) > 0 ? [{ label: 'مانده', value: slip.remaining_amount, danger: true }] : []),
  ].filter(r => Number(r.value) !== 0) : []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .payslip-print, .payslip-print * { visibility: visible; }
          .payslip-print { position: absolute; inset: 0; }
          .payslip-print .no-print { display: none; }
        }
      `}</style>
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        {isLoading || !slip ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : (
          <div className="payslip-print">
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="font-bold text-white text-lg">🧾 فیش حقوقی — {slip.staff_name}</h2>
                <div className="text-xs text-gray-steel mt-1">{monthLabel}</div>
              </div>
              <button onClick={onClose} className="no-print text-gray-steel hover:text-white text-2xl">×</button>
            </div>

            <div className="space-y-1">
              {rows.map(r => (
                <div key={r.label}
                  className="flex items-start justify-between px-3 py-2.5 rounded-lg"
                  style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '0.5px solid rgba(255,255,255,0.05)' }}>
                  <div>
                    <div className="text-sm text-white">{r.label}</div>
                    {r.sub && <div className="text-[10px] text-gray-steel mt-0.5">{r.sub}</div>}
                  </div>
                  <div className={`text-sm font-bold whitespace-nowrap ${r.negative || r.danger ? 'text-red-400' : 'text-white'}`}>
                    {r.negative ? '−' : ''}{fmt(Math.abs(Number(r.value)))} ریال
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between px-3 py-3 rounded-lg bg-white/5">
                <span className="text-sm font-semibold text-white">ناخالص</span>
                <span className="text-base font-bold text-white">{fmt(slip.gross_amount)} ریال</span>
              </div>
              <div className="flex items-center justify-between px-4 py-4 rounded-xl bg-brand/10 border border-brand/30">
                <span className="text-sm font-bold text-brand">خالص پرداختی</span>
                <span className="text-2xl font-black text-brand">{fmt(slip.net_amount)} ریال</span>
              </div>
            </div>

            {(slip.leave_records?.length > 0 || slip.bonus_penalty_records?.length > 0 || slip.installments?.length > 0) && (
              <div className="mt-4 space-y-3">
                {slip.installments?.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-gray-steel mb-1.5">💳 پرداخت‌ها</div>
                    <div className="space-y-1">
                      {slip.installments.map(r => (
                        <div key={r.id} className="flex items-center justify-between text-[11px] bg-white/5 rounded-lg px-3 py-1.5">
                          <span className="text-white">{r.account_name || '—'} — {fmt(r.amount)} ریال</span>
                          <span className="text-gray-steel">{jalaliText(r.date)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {slip.leave_records?.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-gray-steel mb-1.5">📋 مرخصی‌های این ماه</div>
                    <div className="space-y-1">
                      {slip.leave_records.map(r => (
                        <div key={r.id} className="flex items-center justify-between text-[11px] bg-white/5 rounded-lg px-3 py-1.5">
                          <span className="text-white">{LEAVE_TYPE_LABEL[r.leave_type] || r.leave_type} — {Number(r.days_count).toLocaleString('fa-IR')} روز{r.reason ? ` (${r.reason})` : ''}</span>
                          <span className="text-gray-steel">{jalaliText(r.date)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {slip.bonus_penalty_records?.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-gray-steel mb-1.5">🏅 تشویقی / تنبیه‌های این ماه</div>
                    <div className="space-y-1">
                      {slip.bonus_penalty_records.map(r => (
                        <div key={r.id} className="flex items-center justify-between text-[11px] bg-white/5 rounded-lg px-3 py-1.5">
                          <span className={Number(r.amount) >= 0 ? 'text-green-400' : 'text-red-400'}>
                            {Number(r.amount) >= 0 ? 'تشویقی' : 'تنبیه'}: {fmt(Math.abs(Number(r.amount)))} ریال{r.note ? ` (${r.note})` : ''}
                          </span>
                          <span className="text-gray-steel">{jalaliText(r.date)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-gray-steel">
              <span>وضعیت: {badge ? <span className={`badge ${badge.cls}`} style={{ fontSize: 10, padding: '1px 8px' }}>{badge.label}</span> : slip.status}</span>
              {slip.status === 'paid' && <span>سند پرداخت: <b className="text-white">#{slip.payment_id}</b></span>}
            </div>

            <button onClick={() => window.print()}
              className="no-print btn-secondary w-full mt-4 py-2.5 text-sm">
              🖨 چاپ فیش
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── تب فیش‌های حقوقی ─────────────────────────────────────────
function PayslipsTab() {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const [detailId, setDetailId] = useState(null)
  const [payFor, setPayFor] = useState(null)
  const now = new Date()
  const [curJy, curJm] = gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate())
  const [jy, setJy] = useState(curJy)
  const [jm, setJm] = useState(curJm)
  const [gy, gm] = jalaliToGregorian(jy, jm, 1)
  const monthLabel = `${JALALI_MONTHS[jm - 1]} ${jy.toLocaleString('fa-IR')}`

  const { data: slips = [], isLoading } = useQuery({
    queryKey: ['payroll-payslips', gy, gm],
    queryFn: () => api.get('/payroll/payslips/', { params: { year: gy, month: gm } }).then(r => r.data),
  })

  const genMut = useMutation({
    mutationFn: () => api.post('/payroll/payslips/generate/', { year: gy, month: gm }).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['payroll-payslips'])
      toast.success(`محاسبه انجام شد — ایجاد: ${Number(r.created).toLocaleString('fa-IR')} | به‌روزرسانی: ${Number(r.updated).toLocaleString('fa-IR')} | بدون تغییر: ${Number(r.skipped).toLocaleString('fa-IR')}`)
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  const actionMut = useMutation({
    mutationFn: ({ id, action }) => api.post(`/payroll/payslips/${id}/${action}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['payroll-payslips'])
      qc.invalidateQueries(['payroll-payslip'])
      toast.success('انجام شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  const tdS = { padding: '10px 12px' }
  return (
    <div>
      <div className="flex items-end justify-between mb-4 flex-wrap gap-2">
        <MonthSelector jy={jy} jm={jm} setJy={setJy} setJm={setJm} label={monthLabel} />
        {can('payroll_pay') && (
          <button onClick={() => genMut.mutate()} disabled={genMut.isPending}
            className="btn-primary text-sm px-4 py-2 disabled:opacity-50">
            {genMut.isPending ? 'در حال محاسبه...' : '🔄 محاسبه همه'}
          </button>
        )}
      </div>

      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : slips.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-3">➕</div>
            <div className="text-gray-steel text-sm">فیشی برای این ماه نیست — ابتدا «محاسبه همه» را بزنید</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['پرسنل', 'ناخالص', 'کسر مرخصی', 'خالص', 'وضعیت', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {slips.map((s, i) => {
                  const badge = STATUS_BADGE[s.status] || STATUS_BADGE.draft
                  return (
                    <tr key={s.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ ...tdS, fontWeight: 600 }}>{s.staff_name}</td>
                      <td style={tdS}>{fmt(s.gross_amount)} ت</td>
                      <td style={{ ...tdS, color: Number(s.leave_deduction) ? '#FF3B3B' : 'var(--color-text-secondary)' }}>
                        {Number(s.leave_deduction) ? fmt(s.leave_deduction) + ' ت' : '—'}
                      </td>
                      <td style={{ ...tdS, fontWeight: 700, color: '#FBC02D' }}>{fmt(s.net_amount)} ت</td>
                      <td style={tdS}>
                        <span className={`badge ${badge.cls}`} style={{ fontSize: 10, padding: '2px 8px' }}>{badge.label}</span>
                        {s.status === 'confirmed' && Number(s.paid_amount) > 0 && (
                          <div className="text-[10px] text-gray-steel mt-0.5">
                            ✅ تأیید شده — پرداخت‌شده {fmt(s.paid_amount)} از {fmt(s.net_amount)} ریال
                          </div>
                        )}
                      </td>
                      <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
                        <button onClick={() => setDetailId(s.id)}
                          className="text-xs px-2 py-1 rounded-lg bg-white/10 text-gray-steel hover:bg-white/20 transition-all ml-1">
                          👁 فیش
                        </button>
                        {can('payroll_pay') && (
                          <>
                            <button onClick={() => actionMut.mutate({ id: s.id, action: 'recalculate' })}
                              disabled={actionMut.isPending || s.status === 'paid'}
                              className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all ml-1 disabled:opacity-40">
                              🔄 بازمحاسبه
                            </button>
                            {s.status === 'draft' && (
                              <button onClick={() => actionMut.mutate({ id: s.id, action: 'confirm' })}
                                disabled={actionMut.isPending}
                                className="text-xs px-2 py-1 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 transition-all ml-1 disabled:opacity-40">
                                ✅ تأیید
                              </button>
                            )}
                            {s.status === 'confirmed' && (
                              <button onClick={() => setPayFor(s)}
                                className="text-xs px-2 py-1 rounded-lg bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 transition-all ml-1">
                                {Number(s.paid_amount) > 0 ? '💳 پرداخت قسط' : '💳 پرداخت'}
                              </button>
                            )}
                          </>
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

      {detailId && <PayslipDetailModal slipId={detailId} monthLabel={monthLabel} onClose={() => setDetailId(null)} />}
      {payFor && <PayModal slip={payFor} onClose={() => setPayFor(null)} />}
    </div>
  )
}

// ─── مودال پروفایل حقوقی پرسنل ────────────────────────────────
function ProfileModal({ staff, onClose }) {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const profile = staff.profile
  const [form, setForm] = useState({
    staff_id: profile ? String(profile.staff) : String(staff.id),
    has_base_salary: !!profile?.has_base_salary,
    has_commission_personal: !!profile?.has_commission_personal,
    has_commission_total: !!profile?.has_commission_total,
    has_bonus_penalty: !!profile?.has_bonus_penalty,
    has_annual_bonus: !!profile?.has_annual_bonus,
    has_leave_management: !!profile?.has_leave_management,
    base_amount: profile ? String(profile.base_amount ?? '') : '',
    annual_bonus_months: profile ? String(profile.annual_bonus_months ?? '2') : '2',
    annual_bonus_formula: profile?.annual_bonus_formula || 'legal',
    working_days_divisor: profile ? String(profile.working_days_divisor ?? '30') : '30',
    leave_entitled_days_per_month: profile ? String(profile.leave_entitled_days_per_month ?? '2.5') : '2.5',
    leave_sick_days_per_month: profile ? String(profile.leave_sick_days_per_month ?? '1') : '1',
    personal_commission_tiers: toStrTiers(profile?.personal_commission_tiers),
    total_share_tiers: toStrTiers(profile?.total_share_tiers),
    is_active: profile ? !!profile.is_active : true,
  })
  const [msg, setMsg] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const { data: staffList = [] } = useQuery({
    queryKey: ['payroll-staff'],
    queryFn: () => api.get('/payroll/staff/').then(r => r.data),
    enabled: !profile,
  })

  const saveMut = useMutation({
    mutationFn: (payload) => profile
      ? api.patch(`/payroll/profiles/${profile.id}/`, payload).then(r => r.data)
      : api.post('/payroll/profiles/', payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['payroll-staff'])
      qc.invalidateQueries(['payroll-profiles'])
      toast.success('پروفایل حقوقی ذخیره شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ذخیره' }),
  })

  function handleSubmit() {
    if (!profile && !form.staff_id) return setMsg({ type: 'error', text: 'پرسنل را انتخاب کنید' })
    setMsg(null)
    saveMut.mutate({
      ...(profile ? {} : { staff: Number(form.staff_id) }),
      has_base_salary: !!form.has_base_salary,
      has_commission_personal: !!form.has_commission_personal,
      has_commission_total: !!form.has_commission_total,
      has_bonus_penalty: !!form.has_bonus_penalty,
      has_annual_bonus: !!form.has_annual_bonus,
      has_leave_management: !!form.has_leave_management,
      base_amount: Number(parseAmount(form.base_amount)) || 0,
      annual_bonus_months: Number(form.annual_bonus_months) || 2,
      annual_bonus_formula: form.annual_bonus_formula,
      working_days_divisor: Number(form.working_days_divisor) || 30,
      leave_entitled_days_per_month: Number(form.leave_entitled_days_per_month) || 2.5,
      leave_sick_days_per_month: Number(form.leave_sick_days_per_month) || 1,
      personal_commission_tiers: cleanTiers(form.personal_commission_tiers),
      total_share_tiers: cleanTiers(form.total_share_tiers),
      is_active: !!form.is_active,
    })
  }

  const editable = can('payroll_edit')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">
            {profile ? `✏️ پروفایل حقوقی — ${profile.staff_name}` : `➕ پروفایل حقوقی — ${staff.name}`}
          </h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          {profile ? (
            <div className="text-xs text-gray-steel bg-white/5 rounded-lg px-3 py-2">
              پرسنل: <b className="text-white">{profile.staff_name}</b> — {profile.staff_phone || 'بدون موبایل'}
            </div>
          ) : (
            <div>
              <label className="text-xs text-gray-steel block mb-1">پرسنل *</label>
              <SearchSelect
                value={form.staff_id}
                onChange={v => set('staff_id', v)}
                placeholder="جستجو و انتخاب پرسنل..."
                options={staffList.map(s => ({ value: s.id, label: s.name, sub: s.phone }))}
              />
            </div>
          )}

          <div>
            <div className="text-xs font-bold text-white mb-2">ماژول‌های فعال</div>
            <div className="space-y-2">
              {MODULES.map(m => (
                <div key={m.key} className="bg-white/5 rounded-xl p-3">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input type="checkbox" checked={!!form[m.key]} disabled={!editable}
                      onChange={e => set(m.key, e.target.checked)}
                      className="accent-[#FBC02D] mt-0.5" />
                    <span className="text-xs text-white font-semibold">{m.label}
                      <span className="block text-[10px] text-gray-steel font-normal mt-0.5">{m.desc}</span>
                    </span>
                  </label>
                  {m.key === 'has_base_salary' && form.has_base_salary && (
                    <div className="mt-2 mr-6">
                      <label className="text-[10px] text-gray-steel block mb-1">مبلغ حقوق پایه (ریال)</label>
                      <AmountInput value={form.base_amount} disabled={!editable}
                        onChange={e => set('base_amount', e.target.value)}
                        className="input text-sm" placeholder="0" />
                    </div>
                  )}
                  {m.key === 'has_commission_personal' && form.has_commission_personal && (
                    <div className="mt-2 mr-6">
                      <TierEditor
                        title="پلکان پورسانت فروش شخصی"
                        hint="پلکان پیش‌رونده با بازه روی فروش شخصی ماه؛ «درصد هر گام» = درصدی از مبلغ همان گام"
                        tiers={form.personal_commission_tiers}
                        onChange={tiers => set('personal_commission_tiers', tiers)}
                        editable={editable}
                      />
                    </div>
                  )}
                  {m.key === 'has_commission_total' && form.has_commission_total && (
                    <div className="mt-2 mr-6">
                      <TierEditor
                        title="پلکان سهم فروش مجموعه"
                        hint="پلکان پیش‌رونده با بازه روی فروش کل ماه مجموعه"
                        tiers={form.total_share_tiers}
                        onChange={tiers => set('total_share_tiers', tiers)}
                        editable={editable}
                      />
                    </div>
                  )}
                  {m.key === 'has_annual_bonus' && form.has_annual_bonus && (
                    <div className="mt-2 mr-6 space-y-2">
                      <div>
                        <label className="text-[10px] text-gray-steel block mb-1">مبنای عیدی (ماه حقوق)</label>
                        <input type="number" step="0.5" value={form.annual_bonus_months} disabled={!editable}
                          onChange={e => set('annual_bonus_months', e.target.value)}
                          className="input text-sm" placeholder="2" />
                        <div className="text-[10px] text-gray-steel mt-1">قانون کار: حداکثر ۳ ماه</div>
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-steel block mb-1">فرمول عیدی</label>
                        <select value={form.annual_bonus_formula} disabled={!editable}
                          onChange={e => set('annual_bonus_formula', e.target.value)}
                          className="input text-sm">
                          <option value="legal">قانون کار (سقف ۳ ماه)</option>
                          <option value="agreed">توافقی</option>
                        </select>
                      </div>
                    </div>
                  )}
                  {m.key === 'has_leave_management' && form.has_leave_management && (
                    <div className="mt-2 mr-6 space-y-2">
                      <div>
                        <label className="text-[10px] text-gray-steel block mb-1">مبنای روزهای ماه</label>
                        <input type="number" step="1" value={form.working_days_divisor} disabled={!editable}
                          onChange={e => set('working_days_divisor', e.target.value)}
                          className="input text-sm" placeholder="30" />
                        <div className="text-[10px] text-gray-steel mt-1">حقوق روزانه = حقوق ثابت ÷ این عدد</div>
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-steel block mb-1">مرخصی استحقاقی ماهانه (روز)</label>
                        <input type="number" step="0.1" value={form.leave_entitled_days_per_month} disabled={!editable}
                          onChange={e => set('leave_entitled_days_per_month', e.target.value)}
                          className="input text-sm" placeholder="2.5" />
                      </div>
                      <div>
                        <label className="text-[10px] text-gray-steel block mb-1">سقف استعلاجی ماهانه (روز)</label>
                        <input type="number" step="0.1" value={form.leave_sick_days_per_month} disabled={!editable}
                          onChange={e => set('leave_sick_days_per_month', e.target.value)}
                          className="input text-sm" placeholder="1" />
                        <div className="text-[10px] text-gray-steel mt-1">مازادش بدون حقوق می‌شود</div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={!!form.is_active} disabled={!editable}
              onChange={e => set('is_active', e.target.checked)}
              className="accent-[#FBC02D]" />
            پروفایل فعال — در محاسبه حقوق این ماه لحاظ شود
          </label>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          {editable ? (
            <button onClick={handleSubmit} disabled={saveMut.isPending}
              className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
              {saveMut.isPending ? 'در حال ذخیره...' : '✓ ذخیره پروفایل'}
            </button>
          ) : (
            <div className="flex-1 text-center text-xs text-gray-steel py-2.5">فقط مشاهده — برای ذخیره نیاز به دسترسی ویرایش حقوق و دستمزد است</div>
          )}
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── تب پروفایل پرسنل ─────────────────────────────────────────
function StaffProfilesTab() {
  const [editing, setEditing] = useState(null)

  const { data: staff = [], isLoading } = useQuery({
    queryKey: ['payroll-staff'],
    queryFn: () => api.get('/payroll/staff/').then(r => r.data),
  })

  const tdS = { padding: '10px 12px' }
  return (
    <div>
      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : staff.length === 0 ? (
          <div className="text-center py-12 text-gray-steel text-sm">پرسنل فعالی تعریف نشده — از صفحه «نقش‌ها و پرسنل» پرسنل اضافه کنید</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['پرسنل', 'موبایل', 'ماژول‌های فعال', 'حقوق پایه', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {staff.map((s, i) => {
                  const p = s.profile
                  const activeModules = p ? MODULES.filter(m => p[m.key]) : []
                  return (
                    <tr key={s.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ ...tdS, fontWeight: 600 }}>
                        {s.name}
                        {p && !p.is_active && <div className="text-[10px] text-red-400 mt-0.5">غیرفعال</div>}
                      </td>
                      <td style={{ ...tdS, color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{s.phone || '—'}</td>
                      <td style={tdS}>
                        {activeModules.length === 0 ? (
                          <span className="text-[11px] text-gray-steel">—</span>
                        ) : (
                          <div className="flex gap-1 flex-wrap">
                            {activeModules.map(m => (
                              <span key={m.key} className="badge badge-gold" style={{ fontSize: 9, padding: '1px 6px' }}>{m.label}</span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td style={{ ...tdS, fontWeight: 600 }}>{p?.has_base_salary ? fmt(p.base_amount) + ' ت' : '—'}</td>
                      <td style={tdS}>
                        <button onClick={() => setEditing(s)}
                          className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all">
                          {p ? '✏️ ویرایش' : '➕ پروفایل'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && <ProfileModal staff={editing} onClose={() => setEditing(null)} />}
    </div>
  )
}

// ─── تب مرخصی و تشویقی ────────────────────────────────────────
function LeaveBonusTab() {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const editable = can('payroll_edit')
  const todayIso = new Date().toISOString().split('T')[0]

  const [leaveForm, setLeaveForm] = useState({ staff: '', leave_type: 'entitled', days_count: '1', date: todayIso, reason: '' })
  const [bonusForm, setBonusForm] = useState({ staff: '', amount: '', note: '', date: todayIso })
  const [leaveMsg, setLeaveMsg] = useState(null)
  const [bonusMsg, setBonusMsg] = useState(null)

  const { data: staff = [] } = useQuery({
    queryKey: ['payroll-staff'],
    queryFn: () => api.get('/payroll/staff/').then(r => r.data),
  })
  const { data: leaves = [] } = useQuery({
    queryKey: ['payroll-leaves'],
    queryFn: () => api.get('/payroll/leaves/').then(r => r.data),
  })
  const { data: bonuses = [] } = useQuery({
    queryKey: ['payroll-bonus-penalties'],
    queryFn: () => api.get('/payroll/bonus-penalties/').then(r => r.data),
  })

  const staffOptions = staff.map(s => ({ value: s.id, label: s.name, sub: s.phone }))

  const invalidate = () => {
    qc.invalidateQueries(['payroll-leaves'])
    qc.invalidateQueries(['payroll-bonus-penalties'])
    qc.invalidateQueries(['payroll-payslips'])
  }

  const leaveMut = useMutation({
    mutationFn: () => api.post('/payroll/leaves/', {
      staff: Number(leaveForm.staff),
      leave_type: leaveForm.leave_type,
      date: leaveForm.date,
      days_count: Number(leaveForm.days_count) || 0,
      reason: leaveForm.reason,
    }).then(r => r.data),
    onSuccess: () => {
      invalidate()
      setLeaveForm({ staff: '', leave_type: 'entitled', days_count: '1', date: todayIso, reason: '' })
      setLeaveMsg(null)
      toast.success('مرخصی ثبت شد')
    },
    onError: (e) => setLeaveMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const bonusMut = useMutation({
    mutationFn: () => api.post('/payroll/bonus-penalties/', {
      staff: Number(bonusForm.staff),
      amount: Number(parseAmount(bonusForm.amount)) || 0,
      note: bonusForm.note,
      date: bonusForm.date,
    }).then(r => r.data),
    onSuccess: () => {
      invalidate()
      setBonusForm({ staff: '', amount: '', note: '', date: todayIso })
      setBonusMsg(null)
      toast.success('ثبت شد')
    },
    onError: (e) => setBonusMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const delLeaveMut = useMutation({
    mutationFn: (id) => api.delete(`/payroll/leaves/${id}/`).then(r => r.data),
    onSuccess: () => { invalidate(); toast.success('حذف شد') },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })
  const delBonusMut = useMutation({
    mutationFn: (id) => api.delete(`/payroll/bonus-penalties/${id}/`).then(r => r.data),
    onSuccess: () => { invalidate(); toast.success('حذف شد') },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  const submitLeave = () => {
    if (!leaveForm.staff) return setLeaveMsg({ type: 'error', text: 'پرسنل را انتخاب کنید' })
    if (!(Number(leaveForm.days_count) > 0)) return setLeaveMsg({ type: 'error', text: 'تعداد روز را وارد کنید' })
    if (!leaveForm.date) return setLeaveMsg({ type: 'error', text: 'تاریخ را وارد کنید' })
    setLeaveMsg(null)
    leaveMut.mutate()
  }
  const submitBonus = () => {
    if (!bonusForm.staff) return setBonusMsg({ type: 'error', text: 'پرسنل را انتخاب کنید' })
    if (bonusForm.amount === '' || Number(parseAmount(bonusForm.amount)) === 0) return setBonusMsg({ type: 'error', text: 'مبلغ را وارد کنید (مثبت یا منفی)' })
    if (!bonusForm.date) return setBonusMsg({ type: 'error', text: 'تاریخ را وارد کنید' })
    setBonusMsg(null)
    bonusMut.mutate()
  }

  const tdS = { padding: '8px 10px' }
  const recentLeaves = leaves.slice(0, 50)
  const recentBonuses = bonuses.slice(0, 50)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
      {/* ─── ثبت مرخصی ─── */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">📋 ثبت مرخصی</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-steel block mb-1">پرسنل *</label>
            <SearchSelect value={leaveForm.staff}
              onChange={v => setLeaveForm(f => ({ ...f, staff: v }))}
              placeholder="جستجو و انتخاب پرسنل..."
              options={staffOptions} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-steel block mb-1">نوع مرخصی</label>
              <select value={leaveForm.leave_type} disabled={!editable}
                onChange={e => setLeaveForm(f => ({ ...f, leave_type: e.target.value }))}
                className="input text-sm">
                {LEAVE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-steel block mb-1">تعداد روز</label>
              <input type="number" step="0.5" min="0.5" value={leaveForm.days_count} disabled={!editable}
                onChange={e => setLeaveForm(f => ({ ...f, days_count: e.target.value }))}
                className="input text-sm" />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-steel block mb-1">تاریخ شروع</label>
              <JalaliDateInput value={leaveForm.date} onChange={v => setLeaveForm(f => ({ ...f, date: v }))} className="input text-sm" />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-steel block mb-1">توضیحات</label>
              <input value={leaveForm.reason} disabled={!editable}
                onChange={e => setLeaveForm(f => ({ ...f, reason: e.target.value }))}
                className="input text-sm" placeholder="اختیاری" />
            </div>
          </div>
          {leaveMsg && (
            <div className="rounded-lg px-4 py-2 text-xs bg-red-500/20 text-red-400">{leaveMsg.text}</div>
          )}
          {editable && (
            <button onClick={submitLeave} disabled={leaveMut.isPending}
              className="btn-primary w-full text-sm py-2.5 disabled:opacity-50">
              {leaveMut.isPending ? 'در حال ثبت...' : '✓ ثبت مرخصی'}
            </button>
          )}
        </div>

        <div className="mt-5 pt-4 border-t border-white/10">
          <div className="text-xs font-bold text-gray-steel mb-2">آخرین مرخصی‌ها</div>
          {recentLeaves.length === 0 ? (
            <div className="text-center py-4 text-gray-steel text-[11px]">مرخصی ثبت نشده</div>
          ) : (
            <div className="overflow-x-auto">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <tbody>
                  {recentLeaves.map((r, i) => (
                    <tr key={r.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ ...tdS, fontWeight: 600 }}>{r.staff_name}</td>
                      <td style={tdS}><span className="badge badge-gold" style={{ fontSize: 9, padding: '1px 6px' }}>{LEAVE_TYPE_LABEL[r.leave_type] || r.leave_type}</span></td>
                      <td style={{ ...tdS, whiteSpace: 'nowrap' }}>{Number(r.days_count).toLocaleString('fa-IR')} روز</td>
                      <td style={{ ...tdS, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>{jalaliText(r.date)}</td>
                      <td style={{ ...tdS, color: 'var(--color-text-secondary)', maxWidth: 100 }} className="truncate">{r.reason || '—'}</td>
                      <td style={tdS}>
                        {editable && (
                          <button onClick={() => { if (window.confirm('این مرخصی حذف شود؟')) delLeaveMut.mutate(r.id) }}
                            disabled={delLeaveMut.isPending}
                            className="text-red-400 hover:text-red-300 text-sm disabled:opacity-50">🗑</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ─── ثبت تشویقی / تنبیه ─── */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">🏅 ثبت تشویقی / تنبیه</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-steel block mb-1">پرسنل *</label>
            <SearchSelect value={bonusForm.staff}
              onChange={v => setBonusForm(f => ({ ...f, staff: v }))}
              placeholder="جستجو و انتخاب پرسنل..."
              options={staffOptions} />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">مبلغ (ریال) *</label>
            <AmountInput value={bonusForm.amount} disabled={!editable}
              onChange={e => setBonusForm(f => ({ ...f, amount: e.target.value }))}
              className="input text-sm" placeholder="مثبت = تشویقی، منفی = تنبیه" />
            <div className="text-[10px] text-gray-steel mt-1">عدد مثبت تشویقی و عدد منفی (با خط تیره اول) تنبیه ثبت می‌کند</div>
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">شرح</label>
            <input value={bonusForm.note} disabled={!editable}
              onChange={e => setBonusForm(f => ({ ...f, note: e.target.value }))}
              className="input text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="text-xs text-gray-steel block mb-1">تاریخ</label>
            <JalaliDateInput value={bonusForm.date} onChange={v => setBonusForm(f => ({ ...f, date: v }))} className="input text-sm" />
          </div>
          {bonusMsg && (
            <div className="rounded-lg px-4 py-2 text-xs bg-red-500/20 text-red-400">{bonusMsg.text}</div>
          )}
          {editable && (
            <button onClick={submitBonus} disabled={bonusMut.isPending}
              className="btn-primary w-full text-sm py-2.5 disabled:opacity-50">
              {bonusMut.isPending ? 'در حال ثبت...' : '✓ ثبت'}
            </button>
          )}
        </div>

        <div className="mt-5 pt-4 border-t border-white/10">
          <div className="text-xs font-bold text-gray-steel mb-2">آخرین موارد ثبت‌شده</div>
          {recentBonuses.length === 0 ? (
            <div className="text-center py-4 text-gray-steel text-[11px]">موردی ثبت نشده</div>
          ) : (
            <div className="overflow-x-auto">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <tbody>
                  {recentBonuses.map((r, i) => (
                    <tr key={r.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ ...tdS, fontWeight: 600 }}>{r.staff_name}</td>
                      <td style={{ ...tdS, fontWeight: 700, color: Number(r.amount) >= 0 ? '#00C896' : '#FF3B3B', whiteSpace: 'nowrap' }}>
                        {Number(r.amount) >= 0 ? '+' : '−'}{fmt(Math.abs(Number(r.amount)))} ت
                      </td>
                      <td style={{ ...tdS, color: 'var(--color-text-secondary)', maxWidth: 110 }} className="truncate">{r.note || '—'}</td>
                      <td style={{ ...tdS, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>{jalaliText(r.date)}</td>
                      <td style={tdS}>
                        {editable && (
                          <button onClick={() => { if (window.confirm('این مورد حذف شود؟')) delBonusMut.mutate(r.id) }}
                            disabled={delBonusMut.isPending}
                            className="text-red-400 hover:text-red-300 text-sm disabled:opacity-50">🗑</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── ویرایشگر پلکان پیش‌رونده — هر بازه: از، تا، گام و درصد هر گام ──
function TierEditor({ title, hint, tiers, onChange, editable }) {
  const setTier = (i, k, v) => onChange(tiers.map((t, j) => j === i ? { ...t, [k]: v } : t))
  return (
    <div className="pt-4 border-t border-white/10">
      <div className="text-xs font-bold text-white mb-1">{title}</div>
      {hint && <div className="text-[10px] text-gray-steel mb-2">{hint}</div>}
      {tiers.length === 0 ? (
        <div className="text-[11px] text-gray-steel bg-white/5 rounded-lg px-3 py-2 mb-2">بازه‌ای تعریف نشده — با «افزودن بازه» شروع کنید</div>
      ) : (
        <div className="space-y-2 mb-2">
          {tiers.map((t, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-3 space-y-2 relative">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-gray-steel block mb-1">از (ریال)</label>
                  <AmountInput value={t.from} disabled={!editable}
                    onChange={e => setTier(i, 'from', e.target.value)}
                    className="input text-xs" placeholder="0" />
                </div>
                <div>
                  <label className="text-[10px] text-gray-steel block mb-1">تا (ریال)</label>
                  <AmountInput value={t.to} disabled={!editable}
                    onChange={e => setTier(i, 'to', e.target.value)}
                    className="input text-xs" placeholder="0" />
                </div>
                <div>
                  <label className="text-[10px] text-gray-steel block mb-1">هر چند ریال</label>
                  <AmountInput value={t.step} disabled={!editable}
                    onChange={e => setTier(i, 'step', e.target.value)}
                    className="input text-xs" placeholder="0" />
                </div>
                <div>
                  <label className="text-[10px] text-gray-steel block mb-1">درصد هر گام (٪)</label>
                  <input type="number" step="0.01" value={t.percent} disabled={!editable}
                    onChange={e => setTier(i, 'percent', e.target.value)}
                    className="input text-xs" placeholder="مثلاً 0.5" />
                </div>
              </div>
              {editable && (
                <button onClick={() => onChange(tiers.filter((_, j) => j !== i))}
                  className="text-[10px] text-red-400 hover:text-red-300">حذف بازه</button>
              )}
            </div>
          ))}
        </div>
      )}
      {editable && (
        <button onClick={() => onChange([...tiers, { from: '', to: '', step: '', percent: '' }])}
          className="text-xs px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all">
          + افزودن بازه
        </button>
      )}
    </div>
  )
}

// تبدیل پلکان‌های بک‌اند به رشته برای فرم
const toStrTiers = (tiers) => (tiers || []).map(t => ({
  from: String(t.from ?? ''), to: String(t.to ?? ''), step: String(t.step ?? ''), percent: String(t.percent ?? ''),
}))

// پلکان‌ها برای ذخیره — ردیف‌های با تا/گام/درصد خالی یا صفر حذف (از می‌تواند صفر باشد)، مرتب‌شده بر اساس آغاز بازه
function cleanTiers(tiers) {
  return tiers
    .map(t => ({
      from: Number(parseAmount(t.from)) || 0,
      to: Number(parseAmount(t.to)) || 0,
      step: Number(parseAmount(t.step)) || 0,
      percent: Number(parseAmount(t.percent)) || 0,
    }))
    .filter(t => t.to > 0 && t.step > 0 && t.percent > 0)
    .sort((a, b) => a.from - b.from)
}

// ─── صفحه اصلی حقوق و دستمزد ──────────────────────────────────
export default function PayrollPage() {
  const { can } = usePermissions()
  const [tab, setTab] = useState('payslips')

  if (!can('payroll_view')) {
    return (
      <div className="container-main py-20 text-center">
        <div className="text-5xl mb-4">🔒</div>
        <h2 className="font-display font-bold text-xl text-white mb-3">دسترسی محدود</h2>
        <p className="text-gray-steel text-sm">برای مشاهده حقوق و دستمزد نیاز به دسترسی مخصوص دارید.</p>
      </div>
    )
  }

  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">حقوق و دستمزد</h1>

      <div className="flex gap-2 mb-6 border-b border-white/10">
        {[
          { key: 'payslips', label: '🧾 فیش‌های حقوقی' },
          { key: 'profiles', label: '👤 پروفایل پرسنل' },
          { key: 'leave', label: '📋 مرخصی و تشویقی' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${tab === t.key ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'payslips' && <PayslipsTab />}
      {tab === 'profiles' && <StaffProfilesTab />}
      {tab === 'leave' && <LeaveBonusTab />}
    </div>
  )
}
