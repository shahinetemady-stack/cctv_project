import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { orderService } from '../services/orders'
import { authService } from '../services/auth'
import useAuthStore from '../store/useAuthStore'
import { PageLoader, EmptyState } from '../components/ui'
import { statusLabel, statusColor, formatPrice } from '../utils/format'
import { Link } from 'react-router-dom'

// ─── سفارش‌ها ─────────────────────────────────────────────────────────────────
function OrderCard({ order }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-mono text-sm font-semibold">{order.order_number}</div>
          <div className="text-xs text-gray-steel mt-0.5">
            {new Date(order.created_at).toLocaleDateString('fa-IR')}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={statusColor[order.status]}>
            {statusLabel[order.status]}
          </span>
          {order.status === 'awaiting_payment' && order.payment_link && (
            <a href={order.payment_link} className="btn-primary text-xs px-3 py-1.5">
              💳 پرداخت
            </a>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-steel">{order.items?.length || 0} آیتم</span>
        <span className="font-bold text-brand dark:text-cyan">
          {formatPrice(order.effective_amount || order.total_amount)}
        </span>
      </div>

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
function ProfileTab() {
  const { user, updateUser } = useAuthStore()
  const [form, setForm] = useState({
    first_name: user?.first_name || '',
    last_name:  user?.last_name  || '',
    phone:      user?.phone      || '',
  })
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', new_password2: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const handleProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const data = await authService.updateMe(form)
      updateUser(data)
      setMsg('پروفایل با موفقیت بروزرسانی شد ✓')
    } catch { setMsg('خطا در ذخیره') } finally { setSaving(false) }
  }

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

  return (
    <div className="space-y-6">
      {msg && (
        <div className="bg-alert-green/10 border border-alert-green/20 rounded-xl p-3 text-sm text-alert-green">
          {msg}
        </div>
      )}

      <form onSubmit={handleProfile} className="card p-5 space-y-4">
        <h3 className="font-semibold text-sm">اطلاعات شخصی</h3>
        <div className="text-sm text-gray-steel bg-brand/5 px-3 py-2 rounded-lg font-mono">
          {user?.email}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">نام</label>
            <input value={form.first_name} onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))}
              className="input" />
          </div>
          <div>
            <label className="label">نام خانوادگی</label>
            <input value={form.last_name} onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))}
              className="input" />
          </div>
        </div>
        <div>
          <label className="label">موبایل</label>
          <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
            className="input" dir="ltr" placeholder="09..." />
        </div>
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? '...' : 'ذخیره'}
        </button>
      </form>

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
    </div>
  )
}

// ─── صفحه اصلی پنل ────────────────────────────────────────────────────────────
export default function AccountPage() {
  const { user, isPartner } = useAuthStore()
  const tabs = ['سفارش‌ها', 'پروفایل']
  const [tab, setTab] = useState(0)

  return (
    <div className="container-main py-8 max-w-3xl">
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

      {tab === 0 && <OrdersTab />}
      {tab === 1 && <ProfileTab />}
    </div>
  )
}
