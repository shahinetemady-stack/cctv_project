import { useState, Fragment } from 'react'
import { toast } from 'sonner'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { orderService, paymentService } from '../services/orders'
import { authService } from '../services/auth'
import api from '../services/api'
import useAuthStore from '../store/useAuthStore'
import { PageLoader, EmptyState } from '../components/ui'
import Seo from '../components/Seo'
import { statusLabel, statusColor, formatPrice } from '../utils/format'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const fmt = (n) => Number(n || 0).toLocaleString('fa-IR')

// تبدیل ریال به تومان با ارقام فارسی
const fmtToman = (rial) => fmt(Math.round(Number(rial || 0) / 10)) + ' تومان'

// ─── داشبورد عملکرد مشتری ────────────────────────────────────────────────────
function DashboardTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-dashboard'],
    queryFn: () => api.get('/accounting/my/dashboard/').then(r => r.data),
  })
  if (isLoading) return <PageLoader />
  if (!data) return null

  const monthly = (data.monthly || []).map(m => {
    const [y, mo] = m.month.split('-').map(Number)
    return { ...m, label: new Date(y, mo - 1).toLocaleDateString('fa-IR', { month: 'long' }) }
  })

  const cards = [
    { label: 'تعداد سفارش‌ها', value: fmt(data.total_orders), icon: '📦', color: '#4FC3F7' },
    { label: 'مجموع خرید', value: `${fmt(data.total_spent)} ریال`, icon: '💰', color: '#00C896' },
    { label: 'سفارش‌های در جریان', value: fmt(data.pending_orders), icon: '⏳', color: '#FF9500' },
    {
      label: 'بدهی فاکتور',
      value: data.debt_irr === 0 && data.debt_cny === 0 ? 'تسویه ✓'
        : `${fmt(Math.abs(data.debt_irr))} ریال${data.debt_cny ? ` + ${fmt(Math.abs(data.debt_cny))} ¥` : ''}`,
      icon: '🧾',
      color: (data.debt_irr > 0 || data.debt_cny > 0) ? '#FF3B3B' : '#00C896',
    },
  ]

  return (
    <div className="space-y-6">
      {/* وضعیت همکاری */}
      {data.is_partner && data.club && (
        <div className="card p-5 border-r-4 border-brand space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🤝</span>
              <div>
                <div className="text-sm font-bold text-white">حساب همکار فعال</div>
                {data.partner_tier_display && (
                  <div className="text-xs text-gold mt-0.5">{data.partner_tier_display}</div>
                )}
              </div>
            </div>
            <div className="text-xs text-gray-steel">{fmt(data.club.progress || 0)}٪</div>
          </div>

          {/* نوار پیشرفت تا سطح بعد */}
          <div className="h-2 rounded-full bg-white/10 overflow-hidden" dir="ltr">
            <div className="h-full rounded-full bg-gradient-to-l from-brand to-gold transition-all"
              style={{ width: `${Math.min(100, data.club.progress || 0)}%` }} />
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-steel">خرید شمرده‌شده در این دوره:</span>
              <span className="font-bold text-white">{fmtToman(data.club.total)}</span>
            </div>
            {data.club.next_tier ? (
              <div className="flex justify-between">
                <span className="text-gray-steel">مانده تا {data.club.next_tier_display}:</span>
                <span className="font-bold text-gold">{fmtToman(data.club.remaining)}</span>
              </div>
            ) : (
              <div className="text-gold font-bold">🏆 بالاترین سطح باشگاه</div>
            )}
            {data.club.platinum_tenure_locked && (
              <div className="text-[11px] text-gray-steel leading-4">
                ⏳ ارتقای پلاتینیوم پس از ۶ ماه همکاری فعال می‌شود.
              </div>
            )}
          </div>

          <Link to="/club" className="text-[11px] text-gray-steel hover:text-brand transition-colors">
            مشاهده قوانین باشگاه ←
          </Link>
        </div>
      )}

      {/* fallback: همکار بدون داده باشگاه */}
      {data.is_partner && !data.club && (
        <div className="card p-4 flex items-center gap-3 border-r-4 border-brand">
          <span className="text-2xl">🤝</span>
          <div>
            <div className="text-sm font-bold text-white">حساب همکار فعال</div>
            {data.partner_tier_display && (
              <div className="text-xs text-gold mt-0.5">{data.partner_tier_display}</div>
            )}
          </div>
        </div>
      )}

      {/* کارت‌های آماری */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map(c => (
          <div key={c.label} className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-gray-steel">{c.label}</span>
              <span className="text-lg">{c.icon}</span>
            </div>
            <div className="font-display font-bold text-lg" style={{ color: c.color }}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* نمودار خرید ماهانه */}
      <div className="card p-5">
        <h3 className="font-semibold text-sm text-white mb-4">خرید ۶ ماه اخیر (ریال)</h3>
        {monthly.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-xs">خریدی در ۶ ماه اخیر ثبت نشده است</div>
        ) : (
          <div dir="ltr" style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#888' }} />
                <YAxis tick={{ fontSize: 10, fill: '#888' }} tickFormatter={v => (v / 1000000).toFixed(0) + 'M'} />
                <Tooltip
                  formatter={(v) => [`${fmt(v)} ریال`, 'خرید']}
                  contentStyle={{ background: '#161618', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 12 }}
                  labelStyle={{ color: '#fff' }}
                />
                <Bar dataKey="total" fill="#FBC02D" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* آخرین سفارش‌ها */}
      <div className="card p-5">
        <h3 className="font-semibold text-sm text-white mb-3">آخرین سفارش‌ها</h3>
        {data.recent_orders.length === 0 ? (
          <div className="text-center py-6 text-gray-steel text-xs">سفارشی ثبت نشده است</div>
        ) : (
          <div className="divide-y divide-white/5">
            {data.recent_orders.map(o => (
              <div key={o.order_number} className="flex items-center justify-between py-2.5 text-xs">
                <span className="font-mono text-gray-300">{o.order_number}</span>
                <span className="text-gray-steel">{new Date(o.date).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}</span>
                <span className={statusColor[o.status]}>{statusLabel[o.status] || o.status_display}</span>
                <span className="font-bold text-white">{fmt(o.total_amount)} ریال</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── کاردکس مشتری — سندها + ریز اقلام ─────────────────────────────────────────
function KardexTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-kardex'],
    queryFn: () => api.get('/accounting/my/kardex/').then(r => r.data),
  })
  const [view, setView] = useState('docs')   // docs = سندها | items = ریز اقلام
  const [expanded, setExpanded] = useState(null)

  if (isLoading) return <PageLoader />
  const items = data?.items || []

  const balChip = (val, unit) => (
    <span className={`font-bold ${val > 0 ? 'text-red-400' : val < 0 ? 'text-green-400' : 'text-gray-steel'}`}>
      {val === 0 ? 'تسویه ✓' : `${val > 0 ? 'بدهکار' : 'بستانکار'} ${fmt(Math.abs(val))} ${unit}`}
    </span>
  )

  // ریز اقلام — فلت همه اقلام فاکتورها
  const flatItems = []
  for (const it of items) {
    for (const sub of (it.inv_items || [])) {
      flatItems.push({ date: it.date, inv_number: it.inv_number, ...sub })
    }
  }

  return (
    <div className="space-y-4">
      {/* مانده حساب */}
      <div className="card p-4 flex gap-6 flex-wrap">
        <span className="text-sm text-gray-steel">مانده ریال: {balChip(data?.balance_irr || 0, 'ت')}</span>
        <span className="text-sm text-gray-steel">مانده یوان: {balChip(data?.balance_cny || 0, '¥')}</span>
      </div>

      {/* سوییچ نمایش */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit">
        {[['docs', '📑 سندها'], ['items', '🧾 ریز اقلام']].map(([k, label]) => (
          <button key={k} onClick={() => setView(k)}
            className={`text-xs px-3 py-1.5 rounded-md transition-all ${view === k ? 'bg-brand/20 text-brand' : 'text-gray-steel hover:text-white'}`}>
            {label}
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <EmptyState icon="🧾" title="سندی در حساب شما ثبت نشده" />
      ) : view === 'docs' ? (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-steel">
                {['تاریخ', 'نوع سند', 'شرح', 'بدهکار', 'بستانکار', 'مانده'].map(h => (
                  <th key={h} className="text-right font-medium px-3 py-2.5 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <Fragment key={i}>
                  <tr
                    onClick={() => it.inv_items?.length > 0 && setExpanded(expanded === i ? null : i)}
                    className={`border-b border-white/5 ${it.inv_items?.length ? 'cursor-pointer hover:bg-white/5' : ''}`}>
                    <td className="px-3 py-2.5 text-gray-steel whitespace-nowrap">
                      {it.date ? new Date(it.date).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' }) : '—'}
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-full text-[10px]"
                        style={{ color: it.type === 'invoice' ? '#0066FF' : it.type === 'payment' ? '#00C896' : '#FF9500',
                                 background: (it.type === 'invoice' ? '#0066FF' : it.type === 'payment' ? '#00C896' : '#FF9500') + '20' }}>
                        {it.type_label}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-gray-300">{it.description}</td>
                    <td className="px-3 py-2.5 text-red-400 whitespace-nowrap">
                      {it.debit_irr ? fmt(it.debit_irr) + ' ت' : ''}{it.debit_cny ? ` ${fmt(it.debit_cny)} ¥` : ''}{!it.debit_irr && !it.debit_cny ? '—' : ''}
                    </td>
                    <td className="px-3 py-2.5 text-green-400 whitespace-nowrap">
                      {it.credit_irr ? fmt(it.credit_irr) + ' ت' : ''}{it.credit_cny ? ` ${fmt(it.credit_cny)} ¥` : ''}{!it.credit_irr && !it.credit_cny ? '—' : ''}
                    </td>
                    <td className="px-3 py-2.5 font-bold whitespace-nowrap"
                      style={{ color: it.bal_irr > 0 ? '#FF3B3B' : it.bal_irr < 0 ? '#00C896' : '#888' }}>
                      {it.bal_irr !== 0 ? `${fmt(Math.abs(it.bal_irr))} ${it.bal_irr > 0 ? 'بد' : 'بس'}` : '✓'}
                      {it.bal_cny !== 0 && <span className="text-[10px]"> | {fmt(Math.abs(it.bal_cny))} ¥</span>}
                    </td>
                  </tr>
                  {expanded === i && it.inv_items?.map((sub, j) => (
                    <tr key={`${i}-${j}`} className="border-b border-white/5 bg-brand/5">
                      <td className="px-3 py-1.5 text-gray-steel text-[10px]">{new Date(it.date).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}</td>
                      <td />
                      <td className="px-3 py-1.5 text-gray-steel">
                        <span className="mr-1">↳</span> {sub.product_name}
                        <span className="text-[10px]" dir="ltr"> [{sub.sku}]</span>
                        <span className="text-[10px]"> × {fmt(sub.quantity)}</span>
                      </td>
                      <td colSpan={3} className="px-3 py-1.5 text-gray-steel">{fmt(sub.unit_price)} ریال</td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-steel">
                {['تاریخ', 'فاکتور', 'کالا', 'تعداد', 'فی'].map(h => (
                  <th key={h} className="text-right font-medium px-3 py-2.5 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {flatItems.map((it, i) => (
                <tr key={i} className="border-b border-white/5">
                  <td className="px-3 py-2.5 text-gray-steel whitespace-nowrap">{new Date(it.date).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}</td>
                  <td className="px-3 py-2.5 font-mono text-gray-300 whitespace-nowrap">{it.inv_number}</td>
                  <td className="px-3 py-2.5 text-gray-300">{it.product_name} <span className="text-gray-steel text-[10px]" dir="ltr">[{it.sku}]</span></td>
                  <td className="px-3 py-2.5">{fmt(it.quantity)}</td>
                  <td className="px-3 py-2.5 text-gray-300">{fmt(it.unit_price)} ریال</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}


// ─── سفارش‌ها ─────────────────────────────────────────────────────────────────
function OrderCard({ order }) {
  const [expanded, setExpanded] = useState(false)
  const [paying, setPaying] = useState(false)

  // هدایت به درگاه به‌پرداخت ملت
  const handleOnlinePay = async () => {
    setPaying(true)
    try {
      const res = await paymentService.requestPayment(order.order_number)
      window.location.href = res.redirect_url
    } catch (e) {
      toast.error(e?.response?.data?.error || 'خطا در اتصال به درگاه پرداخت')
      setPaying(false)
    }
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-mono text-sm font-semibold">{order.order_number}</div>
          <div className="text-xs text-gray-steel mt-0.5">
            {new Date(order.created_at).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={statusColor[order.status]}>
            {statusLabel[order.status]}
          </span>
          {order.status === 'awaiting_payment' && order.order_type === 'direct_purchase' && !order.is_payment_expired && (
            <button onClick={handleOnlinePay} disabled={paying}
              className="btn-primary text-xs px-3 py-1.5 disabled:opacity-50">
              {paying ? 'اتصال به بانک…' : '💳 پرداخت'}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-steel">{order.items?.length || 0} آیتم</span>
        <span className="font-bold text-brand dark:text-cyan">
          {formatPrice(order.effective_amount || order.total_amount)}
        </span>
      </div>

      {/* نحوه تسویه و موعد آن */}
      {order.settlement_display && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-steel">نحوه تسویه: <b className="text-gray-700 dark:text-gray-300">{order.settlement_display}</b></span>
          {order.settlement_due_date && order.settlement_type !== 'cash' && (
            <span className={order.is_settlement_due ? 'text-alert-red font-bold' : 'text-gray-steel'}>
              {order.is_settlement_due ? '⚠️ سررسید تسویه: ' : 'موعد تسویه: '}
              {new Date(order.settlement_due_date).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}
            </span>
          )}
        </div>
      )}

      {/* هشدار سررسید گذشته */}
      {order.is_settlement_due && (
        <div className="text-[11px] bg-alert-red/10 text-alert-red rounded-lg px-3 py-2">
          ⚠️ موعد تسویه این سفارش گذشته است — لطفاً جهت تسویه با فروشگاه تماس بگیرید.
        </div>
      )}

      <button onClick={() => setExpanded(!expanded)}
        className="text-xs text-gray-steel hover:text-brand transition-colors">
        {expanded ? '▲ بستن' : '▼ جزئیات'}
      </button>

      {expanded && order.items?.length > 0 && (
        <div className="border-t border-gray-100 dark:border-white/5 pt-3 space-y-2">
          {order.items.map(item => (
            <div key={item.id} className="flex justify-between text-xs">
              <span className="text-gray-700 dark:text-gray-300">
                {item.variant_name} × {item.quantity}
                {item.settlement_type && item.settlement_type !== 'cash' && (
                  <span className="mr-1 text-brand">
                    ({item.settlement_display}
                    {item.settlement_due_date && ` — ${new Date(item.settlement_due_date).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}`})
                  </span>
                )}
              </span>
              <span className="text-gray-steel">{formatPrice(item.subtotal)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function OrdersTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-orders'],
    queryFn: orderService.getOrders,
  })
  if (isLoading) return <PageLoader />
  const orders = data || []
  if (orders.length === 0) return (
    <EmptyState icon="📦" title="سفارشی ثبت نشده"
      action={<Link to="/products" className="btn-primary">مشاهده محصولات</Link>} />
  )
  return (
    <div className="space-y-3">
      {orders.map(o => <OrderCard key={o.id} order={o} />)}
    </div>
  )
}

// ─── پروفایل ──────────────────────────────────────────────────────────────────
const PROFILE_FIELD_LABELS = {
  first_name: 'نام',
  last_name: 'نام خانوادگی',
  company_name: 'نام شرکت',
  national_id: 'کد ملی',
  address: 'آدرس',
}

function ProfileTab() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', new_password2: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [showPhoneModal, setShowPhoneModal] = useState(false)
  const [phoneForm, setPhoneForm] = useState({ new_phone: '', reason: '' })
  const [submittingPhone, setSubmittingPhone] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [profForm, setProfForm] = useState({ field: 'first_name', new_value: '', reason: '' })
  const [submittingProf, setSubmittingProf] = useState(false)

  const { data: phoneChangeData } = useQuery({
    queryKey: ['phone-change-request'],
    queryFn: () => api.get('/users/me/phone-change-request/').then(r => r.data),
  })
  const phoneRequest = phoneChangeData?.request

  const { data: profReqData } = useQuery({
    queryKey: ['profile-change-requests'],
    queryFn: () => api.get('/users/me/profile-change-request/').then(r => r.data),
  })
  const profRequests = profReqData?.requests || []

  const handlePw = async (e) => {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.new_password2) { setMsg('رمزها مطابقت ندارند'); return }
    setSaving(true)
    try {
      await authService.changePassword(pwForm)
      setMsg('رمز عبور تغییر کرد ✓')
      setPwForm({ old_password: '', new_password: '', new_password2: '' })
    } catch { setMsg('رمز فعلی اشتباه است') } finally { setSaving(false) }
  }

  const handlePhoneChange = async (e) => {
    e.preventDefault()
    setSubmittingPhone(true)
    try {
      await api.post('/users/me/phone-change-request/', phoneForm)
      toast.success('درخواست ثبت شد و پس از تأیید مدیر اعمال می‌شود')
      queryClient.invalidateQueries({ queryKey: ['phone-change-request'] })
      setShowPhoneModal(false)
      setPhoneForm({ new_phone: '', reason: '' })
    } catch (err) {
      toast.error(err?.response?.data?.error || 'خطا در ثبت درخواست')
    } finally { setSubmittingPhone(false) }
  }

  const handleProfileChange = async (e) => {
    e.preventDefault()
    setSubmittingProf(true)
    try {
      await api.post('/users/me/profile-change-request/', profForm)
      toast.success('درخواست ثبت شد و پس از تأیید مدیر اعمال می‌شود')
      queryClient.invalidateQueries({ queryKey: ['profile-change-requests'] })
      setShowProfileModal(false)
      setProfForm({ field: 'first_name', new_value: '', reason: '' })
    } catch (err) {
      toast.error(err?.response?.data?.error || 'خطا در ثبت درخواست')
    } finally { setSubmittingProf(false) }
  }

  const profileValue = (f) => {
    if (f === 'first_name') return user?.first_name
    if (f === 'last_name') return user?.last_name
    return user?.profile?.[f]
  }

  return (
    <div className="space-y-6">
      {msg && (
        <div className="bg-alert-green/10 border border-alert-green/20 rounded-xl p-3 text-sm text-alert-green">
          {msg}
        </div>
      )}

      {user?.parent_account && (
        <div className="bg-brand/10 border border-brand/20 rounded-xl p-3 text-sm text-brand">
          🔗 این حساب، شریک حساب «{user.parent_account.name}» است — سفارش‌ها و کارت‌ها روی حساب اصلی ثبت و دیده می‌شوند
        </div>
      )}

      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-sm">اطلاعات شخصی</h3>
        <div className="text-sm text-gray-steel bg-brand/5 px-3 py-2 rounded-lg font-mono">
          {user?.email}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">نام</label>
            <input value={user?.first_name || ''} readOnly className="input opacity-60 cursor-not-allowed" />
          </div>
          <div>
            <label className="label">نام خانوادگی</label>
            <input value={user?.last_name || ''} readOnly className="input opacity-60 cursor-not-allowed" />
          </div>
        </div>
        {user?.is_partner && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">نام شرکت</label>
                <input value={user?.profile?.company_name || ''} readOnly className="input opacity-60 cursor-not-allowed" />
              </div>
              <div>
                <label className="label">کد ملی</label>
                <input value={user?.profile?.national_id || ''} readOnly className="input opacity-60 cursor-not-allowed" dir="ltr" />
              </div>
            </div>
            <div>
              <label className="label">آدرس</label>
              <input value={user?.profile?.address || ''} readOnly className="input opacity-60 cursor-not-allowed" />
            </div>
          </>
        )}
        <div>
          <label className="label">موبایل</label>
          <input value={user?.phone || ''} readOnly
            className="input opacity-60 cursor-not-allowed" dir="ltr" placeholder="09..." />
          {phoneRequest && (
            <div className="mt-2 text-xs">
              {phoneRequest.status === 'pending' && (
                <span className="badge badge-gold">⏳ درخواست تغییر به {phoneRequest.new_phone} در انتظار تأیید</span>
              )}
              {phoneRequest.status === 'approved' && (
                <span className="text-alert-green">✅ تأیید شد</span>
              )}
              {phoneRequest.status === 'rejected' && (
                <span className="text-alert-red">❌ رد شد</span>
              )}
            </div>
          )}
        </div>
        <div className="text-[11px] text-gray-steel">
          مشخصات هویتی (نام، موبایل، شرکت و…) قابل ویرایش مستقیم نیست — برای تغییر، درخواست بدهید تا پس از تأیید مدیریت اعمال شود.
        </div>
        {profRequests.length > 0 && (
          <div className="space-y-1">
            {profRequests.map(r => (
              <div key={r.id} className="text-xs">
                {r.status === 'pending' && (
                  <span className="badge badge-gold">⏳ تغییر {r.field_display} به «{r.new_value}» در انتظار تأیید</span>
                )}
                {r.status === 'approved' && (
                  <span className="text-alert-green">✅ تغییر {r.field_display} تأیید شد</span>
                )}
                {r.status === 'rejected' && (
                  <span className="text-alert-red">❌ تغییر {r.field_display} رد شد</span>
                )}
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <button type="button" onClick={() => setShowProfileModal(true)}
            className="btn-secondary text-xs px-3 py-1.5">
            ✏️ درخواست تغییر مشخصات
          </button>
          <button type="button" onClick={() => setShowPhoneModal(true)}
            className="btn-secondary text-xs px-3 py-1.5">
            📱 درخواست تغییر موبایل
          </button>
        </div>
      </div>

      <form onSubmit={handlePw} className="card p-5 space-y-4">
        <h3 className="font-semibold text-sm">تغییر رمز عبور</h3>
        {['old_password', 'new_password', 'new_password2'].map((k, i) => (
          <div key={k}>
            <label className="label">{['رمز فعلی', 'رمز جدید', 'تکرار رمز جدید'][i]}</label>
            <input type="password" value={pwForm[k]}
              onChange={e => setPwForm(f => ({ ...f, [k]: e.target.value }))}
              className="input" dir="ltr" />
          </div>
        ))}
        <button type="submit" disabled={saving} className="btn-secondary">
          {saving ? '...' : 'تغییر رمز'}
        </button>
      </form>

      {/* مودال درخواست تغییر موبایل */}
      {showPhoneModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4"
          onClick={() => setShowPhoneModal(false)}>
          <div className="card p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-white text-sm">📱 درخواست تغییر موبایل</h2>
              <button onClick={() => setShowPhoneModal(false)}
                className="text-gray-steel hover:text-white text-lg leading-none">✕</button>
            </div>
            <form onSubmit={handlePhoneChange} className="space-y-4">
              <div>
                <label className="label">موبایل جدید</label>
                <input value={phoneForm.new_phone}
                  onChange={e => setPhoneForm(f => ({ ...f, new_phone: e.target.value }))}
                  className="input" dir="ltr" placeholder="0912..." required />
              </div>
              <div>
                <label className="label">دلیل تغییر</label>
                <textarea value={phoneForm.reason}
                  onChange={e => setPhoneForm(f => ({ ...f, reason: e.target.value }))}
                  className="input" rows={3} required />
              </div>
              <button type="submit" disabled={submittingPhone}
                className="btn-primary w-full disabled:opacity-50">
                {submittingPhone ? '...' : 'ثبت درخواست'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* مودال درخواست تغییر مشخصات */}
      {showProfileModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4"
          onClick={() => setShowProfileModal(false)}>
          <div className="card p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-white text-sm">✏️ درخواست تغییر مشخصات</h2>
              <button onClick={() => setShowProfileModal(false)}
                className="text-gray-steel hover:text-white text-lg leading-none">✕</button>
            </div>
            <form onSubmit={handleProfileChange} className="space-y-4">
              <div>
                <label className="label">کدام مورد را می‌خواهید تغییر دهید؟</label>
                <select value={profForm.field}
                  onChange={e => setProfForm(f => ({ ...f, field: e.target.value, new_value: '' }))}
                  className="input">
                  {Object.entries(PROFILE_FIELD_LABELS).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">مقدار فعلی</label>
                <input value={profileValue(profForm.field) || '—'} readOnly
                  className="input opacity-60 cursor-not-allowed" />
              </div>
              <div>
                <label className="label">مقدار جدید</label>
                <input value={profForm.new_value}
                  onChange={e => setProfForm(f => ({ ...f, new_value: e.target.value }))}
                  className="input" required />
              </div>
              <div>
                <label className="label">دلیل تغییر</label>
                <textarea value={profForm.reason}
                  onChange={e => setProfForm(f => ({ ...f, reason: e.target.value }))}
                  className="input" rows={3} required />
              </div>
              <button type="submit" disabled={submittingProf}
                className="btn-primary w-full disabled:opacity-50">
                {submittingProf ? '...' : 'ثبت درخواست'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── صفحه اصلی پنل ────────────────────────────────────────────────────────────
export default function AccountPage() {
  const { user, isPartner } = useAuthStore()
  const tabs = ['📊 داشبورد', 'سفارش‌ها', 'کاردکس مشتری', 'پروفایل']
  const [tab, setTab] = useState(0)

  return (
    <div className="container-main py-8 max-w-5xl">
      <Seo title="حساب کاربری" noindex />
      {/* سربرگ */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-14 h-14 bg-brand rounded-2xl flex items-center justify-center
          text-white font-bold font-display text-xl shadow-brand">
          {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
        </div>
        <div>
          <h1 className="font-display font-bold text-xl text-white">
            {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.email}
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={isPartner() ? 'badge-blue' : 'badge bg-gray-200 dark:bg-white/10 text-gray-600 dark:text-gray-400'}>
              {isPartner() ? '🤝 همکار' : '🛒 عمومی'}
            </span>
          </div>
        </div>
      </div>

      {/* تب‌ها */}
      <div className="flex gap-1 mb-6 bg-white/5 p-1 rounded-xl">
        {tabs.map((t, i) => (
          <button key={t} onClick={() => setTab(i)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all
              ${tab === i ? 'bg-brand text-white shadow-sm' : 'text-gray-steel hover:text-white'}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === 0 && <DashboardTab />}
      {tab === 1 && <OrdersTab />}
      {tab === 2 && <KardexTab />}
      {tab === 3 && <ProfileTab />}
    </div>
  )
}
