import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import { formatDate, todayTehran } from '../../utils/date'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../../components/ui/AmountInput'
import { PaymentForm } from './PaymentsPage'
import { UserStamp } from '../../components/ui'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const TYPE_LABELS = { cash: 'نقد', bank: 'بانک', petty: 'صندوق', virtual: 'مجازی' }
const CURRENCY_SYMBOL = { IRR: 'ریال', CNY: '¥', USD: '$' }

const EMPTY_FORM = {
  name: '', account_type: 'bank', currency: 'IRR',
  bank_name: '', account_number: '', initial_balance: '', note: '', is_active: true,
}

// ─── فرم ساخت/ویرایش حساب ───────────────────────────────────
function AccountForm({ editing, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState(EMPTY_FORM)
  const [msg, setMsg] = useState(null)

  // در حالت ویرایش جزئیات کامل حساب (note / initial_balance / is_active) را جدا می‌گیریم
  const { data: detail } = useQuery({
    queryKey: ['account-detail', editing?.id],
    queryFn: () => api.get(`/accounting/accounts/${editing.id}/`).then(r => r.data),
    enabled: !!editing,
  })

  useEffect(() => {
    if (!editing) return
    setForm({
      name: editing.name || '',
      account_type: editing.account_type || 'bank',
      currency: editing.currency || 'IRR',
      bank_name: editing.bank_name || '',
      account_number: editing.account_number || '',
      initial_balance: detail?.initial_balance ?? '',
      note: detail?.note ?? '',
      is_active: detail?.is_active ?? true,
    })
  }, [editing, detail])

  const saveMut = useMutation({
    mutationFn: (payload) => editing
      ? api.patch(`/accounting/accounts/${editing.id}/`, payload).then(r => r.data)
      : api.post('/accounting/accounts/', payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['accounts'])
      toast.success(editing ? 'حساب به‌روز شد' : 'حساب جدید ساخته شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || JSON.stringify(e.response?.data) || 'خطا' }),
  })

  function handleSubmit() {
    if (!form.name.trim()) return setMsg({ type: 'error', text: 'نام حساب را وارد کنید' })
    saveMut.mutate({
      name: form.name.trim(),
      account_type: form.account_type,
      currency: form.currency,
      bank_name: form.bank_name,
      account_number: form.account_number,
      initial_balance: Number(form.initial_balance) || 0,
      note: form.note,
      ...(editing ? { is_active: form.is_active } : {}),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">{editing ? '✏️ ویرایش حساب' : '🏦 بانک / حساب جدید'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">نام حساب *</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="input text-sm" placeholder="مثلاً بانک ملت" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">نوع حساب</label>
              <select value={form.account_type} onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))} className="input text-sm">
                {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">ارز</label>
              <select value={form.currency} onChange={e => setForm(f => ({ ...f, currency: e.target.value }))} className="input text-sm">
                <option value="IRR">ریال (IRR)</option>
                <option value="CNY">یوان (CNY)</option>
                <option value="USD">دلار (USD)</option>
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">موجودی اولیه</label>
              <AmountInput value={form.initial_balance}
                onChange={e => setForm(f => ({ ...f, initial_balance: e.target.value }))}
                className="input text-sm" placeholder="0" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">نام بانک</label>
              <input value={form.bank_name} onChange={e => setForm(f => ({ ...f, bank_name: e.target.value }))}
                className="input text-sm" placeholder="اختیاری" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">شماره حساب / کارت</label>
              <input value={form.account_number} onChange={e => setForm(f => ({ ...f, account_number: e.target.value }))}
                className="input text-sm" placeholder="اختیاری" />
            </div>
          </div>

          <div>
            <label className="label text-xs mb-1 block">توضیحات</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
              className="input text-sm" placeholder="اختیاری" />
          </div>

          {editing && (
            <label className="flex items-center gap-2 text-sm text-gray-steel cursor-pointer">
              <input type="checkbox" checked={form.is_active}
                onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                className="accent-brand w-4 h-4" />
              حساب فعال است
            </label>
          )}
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : editing ? '✓ ذخیره تغییرات' : '✓ ساخت حساب'}
          </button>
          <button onClick={onClose} className="btn-secondary text-sm py-2.5 px-6">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال تراکنش‌های یک حساب ───────────────────────────────
function TransactionsModal({ account, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['account-transactions', account.id],
    queryFn: () => api.get(`/accounting/accounts/${account.id}/transactions/`).then(r => r.data),
  })
  const txs = data?.transactions || []
  const summary = data?.summary
  const accCurrency = data?.account?.currency || account.currency

  function kindLabel(t) {
    if (t.kind === 'sale_payment') return 'دریافت فروش'
    return t.direction === 'out' ? 'پرداخت' : 'دریافت'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-4xl max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">تراکنش‌های «{account.name}»</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        {isLoading ? (
          <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : (
          <>
            {/* خلاصه */}
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                <div className="bg-white/5 rounded-xl p-3">
                  <div className="text-[11px] text-gray-steel mb-1">جمع ورود</div>
                  <div className="text-sm font-bold text-green-400">{fmt(summary.total_in_irr)} ریال</div>
                </div>
                <div className="bg-white/5 rounded-xl p-3">
                  <div className="text-[11px] text-gray-steel mb-1">جمع خروج</div>
                  <div className="text-sm font-bold text-red-400">{fmt(summary.total_out_irr)} ریال</div>
                </div>
                <div className="bg-white/5 rounded-xl p-3">
                  <div className="text-[11px] text-gray-steel mb-1">موجودی</div>
                  <div className={`text-sm font-bold ${summary.balance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {fmt(summary.balance)} {CURRENCY_SYMBOL[accCurrency] || accCurrency}
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-3">
                  <div className="text-[11px] text-gray-steel mb-1">تعداد تراکنش</div>
                  <div className="text-sm font-bold text-white">{fmt(summary.count)}</div>
                </div>
              </div>
            )}

            {txs.length === 0 ? (
              <div className="text-center py-10 text-gray-steel text-sm">تراکنشی برای این حساب ثبت نشده</div>
            ) : (
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['تاریخ', 'نوع', 'شرح', 'مبلغ', 'مبلغ ریالی', 'طرف حساب', 'فاکتور', 'مرجع', 'توضیحات', 'ثبت‌کننده'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {txs.map((t, i) => (
                      <tr key={`${t.kind}-${t.id}`} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(t.date)}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span className={t.direction === 'in' ? 'badge-green' : 'badge-red'}>
                            {t.direction === 'in' ? '↓ ورود' : '↑ خروج'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', fontSize: 11 }}>{kindLabel(t)}</td>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: t.direction === 'in' ? '#00C896' : '#FF3B3B', whiteSpace: 'nowrap' }}>
                          {fmt(t.amount)} {CURRENCY_SYMBOL[t.currency] || t.currency}
                          {t.currency === 'CNY' && t.rate_irr ? (
                            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 400 }}>نرخ: {fmt(t.rate_irr)}</div>
                          ) : null}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{fmt(t.amount_irr)} ریال</td>
                        <td style={{ padding: '10px 12px', fontSize: 11 }}>{t.counterparty || '—'}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{t.invoice_label || '—'}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{t.reference || '—'}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{t.note || '—'}</td>
                        <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                          <UserStamp createdBy={t.created_by} createdAt={t.created_at} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ─── صفحه مدیریت بانک ───────────────────────────────────────
export default function AdminBanksPage() {
  const qc = useQueryClient()
  const { can } = usePermissions()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [txAccount, setTxAccount] = useState(null)
  const [payForm, setPayForm] = useState(null)   // 'in' | 'out' | null — فرم تراکنش
  const [payEditing, setPayEditing] = useState(null)

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get('/accounting/accounts/').then(r => r.data),
  })

  const { data: payments = [], isLoading: loadingPayments } = useQuery({
    queryKey: ['payments-list'],
    queryFn: () => api.get('/accounting/payments/').then(r => r.data),
  })

  const delPayMut = useMutation({
    mutationFn: (id) => api.delete(`/accounting/payments/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      toast.success('تراکنش حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف تراکنش'),
  })

  // سند برگشت — اصلاح اصولی بدون حذف: سند معکوس با لینک به سند اصلی ثبت می‌شود
  const revPayMut = useMutation({
    mutationFn: (id) => api.post(`/accounting/payments/${id}/reverse/`).then(r => r.data),
    onSuccess: (r) => {
      qc.invalidateQueries(['payments-list'])
      qc.invalidateQueries(['accounts'])
      qc.invalidateQueries(['contacts-all'])
      toast.success(r.message || 'سند برگشت ثبت شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ثبت برگشت'),
  })

  // جمع موجودی حساب‌ها
  const totalIRR = accounts.filter(a => a.currency === 'IRR').reduce((s, a) => s + (a.balance || 0), 0)
  const totalCNY = accounts.filter(a => a.currency === 'CNY').reduce((s, a) => s + (a.balance || 0), 0)

  const delMut = useMutation({
    mutationFn: (id) => api.delete(`/accounting/accounts/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries(['accounts'])
      toast.success('حساب حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف حساب'),
  })

  function openCreate() {
    setEditing(null)
    setShowForm(true)
  }

  function openEdit(a) {
    setEditing(a)
    setShowForm(true)
  }

  function handleDelete(a) {
    if (!window.confirm(`حساب «${a.name}» حذف شود؟`)) return
    delMut.mutate(a.id)
  }

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="font-display font-bold text-2xl text-white">مدیریت بانک</h1>
        <div className="flex gap-3">
          {can('purchase_create') && (
            <>
              <button onClick={() => { setPayEditing(null); setPayForm('in') }}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-green-600 hover:bg-green-500 text-white transition-all">
                + ثبت دریافت
              </button>
              <button onClick={() => { setPayEditing(null); setPayForm('out') }}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-red-600 hover:bg-red-500 text-white transition-all">
                + ثبت پرداخت
              </button>
            </>
          )}
          {can('accounts_edit') && (
            <button onClick={openCreate} className="btn-primary text-sm px-4 py-2">+ بانک جدید</button>
          )}
        </div>
      </div>

      {/* خلاصه حساب‌ها — منتقل‌شده از صفحه دریافت و پرداخت */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="card p-4 col-span-1">
          <div className="text-xs text-gray-steel mb-2">موجودی کل (ریال)</div>
          <div className={`text-lg sm:text-xl font-bold ${totalIRR >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(totalIRR)} ریال</div>
        </div>
        <div className="card p-4 col-span-1">
          <div className="text-xs text-gray-steel mb-2">موجودی کل (یوان)</div>
          <div className={`text-lg sm:text-xl font-bold ${totalCNY >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(totalCNY)} ¥</div>
        </div>
        <div className="card p-4 col-span-1">
          <div className="text-xs text-gray-steel mb-2">تعداد حساب‌های فعال</div>
          <div className="text-xl font-bold text-white">{accounts.length}</div>
        </div>
      </div>

      {/* حساب‌های بانکی و صندوق — منتقل‌شده از صفحه دریافت و پرداخت */}
      <div className="card p-5 mb-6">
        <h3 className="text-sm font-semibold text-white mb-4">حساب‌های بانکی و صندوق</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {accounts.map(a => (
            <div key={a.id} className="bg-white/5 rounded-xl p-4 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-white truncate">{a.name}</div>
                <div className="text-xs text-gray-steel">{a.account_type_display || a.account_type} | {a.currency}</div>
              </div>
              <div className="flex items-center gap-3">
                <div className={`text-base sm:text-lg font-bold whitespace-nowrap ${(a.balance || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {fmt(a.balance)} {a.currency === 'CNY' ? '¥' : 'ریال'}
                </div>
                <button onClick={() => setTxAccount(a)}
                  className="btn-ghost text-xs px-3 py-1.5">
                  تراکنش‌ها
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* تراکنش‌های امروز — سندهای قدیمی‌تر در «دریافت و پرداخت ← ویرایش اسناد مالی» قابل جستجو/اصلاح است */}
      <div className="card p-5 mb-6">
        <h3 className="text-sm font-semibold text-white mb-4">تراکنش‌های امروز</h3>
        {(() => {
          const today = todayTehran()
          const filtered = payments.filter(p => p.date === today)
          return loadingPayments ? (
          <div className="text-center py-6 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-sm">امروز تراکنشی ثبت نشده — برای اسناد قبلی از «دریافت و پرداخت ← ویرایش اسناد مالی» استفاده کنید</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['سند', 'نوع', 'طرف حساب', 'حساب', 'فاکتور', 'مبلغ', 'مبلغ ریالی', 'روش', 'تاریخ', 'مرجع', 'عملیات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((p, i) => (
                  <tr key={p.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-muted)', fontSize: 11, fontFamily: 'monospace' }}>
                      #{p.id}
                      {p.paired_with && (
                        <div style={{ fontSize: 9, color: '#0066FF' }} title={`جفت‌شده با سند #${p.paired_with} (${p.paired_contact_name || ''})`}>🔗 #{p.paired_with}</div>
                      )}
                      {p.reversal_of && (
                        <div style={{ fontSize: 9, color: '#FBC02D' }} title="این ردیف، سند برگشت است">↩ برگشت #{p.reversal_of}</div>
                      )}
                      {p.is_reversed && (
                        <div style={{ fontSize: 9, color: 'var(--color-text-muted)' }} title="این سند برگشت خورده و اثرش خنثی است">✗ برگشت‌خورده</div>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        color: p.direction === 'in' ? '#00C896' : '#FF3B3B',
                        background: p.direction === 'in' ? '#00C89620' : '#FF3B3B20',
                        padding: '2px 8px', borderRadius: 20, fontSize: 11
                      }}>
                        {p.direction === 'in' ? '↓ دریافت' : '↑ پرداخت'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>{p.contact_name || '—'}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>
                      {(p.direction === 'in' ? p.to_account_name : p.from_account_name) || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.invoice_label || '—'}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: p.direction === 'in' ? '#00C896' : '#FF3B3B' }}>
                      {fmt(p.amount)} {p.currency === 'CNY' ? '¥' : ''}
                      {p.currency === 'CNY' && p.rate_irr ? (
                        <div style={{ fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 400 }}>نرخ: {fmt(p.rate_irr)}</div>
                      ) : null}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{fmt(p.amount_irr)} ریال</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.payment_type_display || p.payment_type}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>
                      {formatDate(p.date)}
                      {p.created_by && (
                        <div style={{ fontSize: 9, color: 'var(--color-text-muted)' }} title={`ویرایش: ${p.updated_by || '—'} ${p.updated_at || ''}`}>
                          📝 {p.created_by}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{p.reference || '—'}</td>
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                      {can('payment_edit') && (
                        <>
                          <button onClick={() => { setPayEditing(p); setPayForm(p.direction) }}
                            className="text-xs px-2 py-1 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all ml-1">
                            ویرایش
                          </button>
                          {!p.is_reversed && !p.reversal_of && (
                            <button onClick={() => { if (window.confirm(`سند برگشت برای تراکنش #${p.id}${p.paired_with ? ` و طرف مقابلش #${p.paired_with}` : ''} ثبت شود؟ (سند معکوس ساخته می‌شود و اثر خنثی می‌شود — سابقه حفظ می‌ماند)`)) revPayMut.mutate(p.id) }}
                              disabled={revPayMut.isPending}
                              className="text-xs px-2 py-1 rounded-lg bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25 transition-all ml-1 disabled:opacity-50">
                              برگشت
                            </button>
                          )}
                          <button onClick={() => { if (window.confirm('این تراکنش حذف شود؟')) delPayMut.mutate(p.id) }} disabled={delPayMut.isPending}
                            className="text-xs px-2 py-1 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all disabled:opacity-50">
                            حذف
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
        })()}
      </div>

      <h3 className="text-sm font-semibold text-white mb-4">مدیریت حساب‌ها</h3>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : accounts.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">🏦</div>
          <div className="text-gray-steel text-sm">هنوز حسابی ثبت نشده — با دکمه «بانک جدید» شروع کنید</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {accounts.map(a => (
            <div key={a.id} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  {/* نام حساب بزرگ بالا، نام بانک کوچک‌تر زیر آن */}
                  <div className="font-bold text-white text-lg">{a.name}</div>
                  {a.bank_name && (
                    <div className="text-xs text-gray-steel mt-1">🏦 {a.bank_name}</div>
                  )}
                  <div className="text-xs text-gray-steel mt-0.5">{TYPE_LABELS[a.account_type] || a.account_type_display || a.account_type}</div>
                </div>
                <div className="flex gap-2">
                  <span className="badge badge-gold">{a.currency}</span>
                  <span className={a.is_active === false ? 'badge badge-danger' : 'badge badge-success'}>
                    {a.is_active === false ? 'غیرفعال' : 'فعال'}
                  </span>
                </div>
              </div>

              {a.account_number && (
                <div className="text-xs text-gray-steel mb-3 tracking-wide">{a.account_number}</div>
              )}

              <div className="flex items-end justify-between">
                <div>
                  <div className="text-[11px] text-gray-steel mb-1">موجودی</div>
                  <div className={`text-lg font-bold ${(a.balance || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {fmt(a.balance)} {CURRENCY_SYMBOL[a.currency] || a.currency}
                  </div>
                </div>
                <div className="flex gap-2">
                  {can('accounts_edit') && (
                    <>
                      <button onClick={() => openEdit(a)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all">
                        ویرایش
                      </button>
                      <button onClick={() => handleDelete(a)} disabled={delMut.isPending}
                        className="text-xs px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all disabled:opacity-50">
                        حذف
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <AccountForm
          editing={editing}
          onClose={() => { setShowForm(false); setEditing(null) }}
        />
      )}

      {txAccount && (
        <TransactionsModal account={txAccount} onClose={() => setTxAccount(null)} />
      )}

      {payForm && (
        <PaymentForm
          direction={payForm}
          editing={payEditing}
          onClose={() => { setPayForm(null); setPayEditing(null) }}
          onSuccess={() => { setPayForm(null); setPayEditing(null) }}
        />
      )}
    </div>
  )
}
