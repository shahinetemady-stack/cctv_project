import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const DELIVERY_STATUS = [
  { value: 'pending',    label: '⏳ در انتظار ارسال', color: '#FF9500' },
  { value: 'shipped',    label: '📦 ارسال شده',        color: '#0066FF' },
  { value: 'in_transit', label: '🚚 در مسیر',          color: '#8B5CF6' },
  { value: 'delivered',  label: '✅ تحویل داده شده',   color: '#00C896' },
  { value: 'returned',   label: '↩️ مرجوع شده',        color: '#FF3B3B' },
]

const COURIERS = [
  { value: '',       label: '— انتخاب کنید' },
  { value: 'post',   label: 'پست' },
  { value: 'tipax',  label: 'تیپاکس' },
  { value: 'chapar', label: 'چاپار' },
  { value: 'snap',   label: 'اسنپ‌باکس' },
  { value: 'other',  label: 'سایر' },
]

const ORDER_STATUS = [
  { value: 'pending',          label: 'در انتظار', color: '#FF9500' },
  { value: 'confirmed',        label: 'تأیید شده', color: '#0066FF' },
  { value: 'awaiting_payment', label: 'در انتظار پرداخت', color: '#8B5CF6' },
  { value: 'paid',             label: 'پرداخت شده', color: '#00C896' },
  { value: 'ready_to_ship',    label: 'آماده ارسال', color: '#00C896' },
  { value: 'shipped',          label: 'ارسال شده', color: '#0066FF' },
  { value: 'cancelled',        label: 'لغو شده', color: '#FF3B3B' },
]

// ─── Modal ویرایش وضعیت ──────────────────────────────────────
function EditOrderModal({ order, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    delivery_status: order.delivery_status || 'pending',
    courier_company: order.courier_company || '',
    tracking_code:   order.tracking_code || '',
    status:          order.status || 'pending',
  })
  const [msg, setMsg] = useState(null)

  const mut = useMutation({
    mutationFn: (data) => api.patch(`/orders/admin/${order.order_number}/update/`, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-orders'])
      setMsg({ type: 'success', text: 'ذخیره شد' })
      setTimeout(onClose, 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white">ویرایش سفارش</h2>
            <div className="font-mono text-xs text-brand mt-1">{order.order_number}</div>
          </div>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label text-xs mb-1 block">وضعیت سفارش</label>
            <select value={form.status}
              onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
              className="input text-sm">
              {ORDER_STATUS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs mb-1 block">وضعیت ارسال</label>
            <select value={form.delivery_status}
              onChange={e => setForm(f => ({ ...f, delivery_status: e.target.value }))}
              className="input text-sm">
              {DELIVERY_STATUS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs mb-1 block">شرکت حمل</label>
            <select value={form.courier_company}
              onChange={e => setForm(f => ({ ...f, courier_company: e.target.value }))}
              className="input text-sm">
              {COURIERS.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label text-xs mb-1 block">کد رهگیری</label>
            <input value={form.tracking_code}
              onChange={e => setForm(f => ({ ...f, tracking_code: e.target.value }))}
              className="input text-sm font-mono" placeholder="مثلاً: 1234567890" dir="ltr" />
          </div>
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={() => mut.mutate(form)} disabled={mut.isPending}
            className="flex-1 py-2.5 rounded-xl bg-brand text-white font-semibold text-sm disabled:opacity-50">
            {mut.isPending ? 'در حال ذخیره...' : '✓ ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
export default function AdminOrdersPage() {
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [deliveryFilter, setDeliveryFilter] = useState('')

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ['admin-orders', statusFilter, deliveryFilter],
    queryFn: () => api.get('/orders/admin/orders/', {
      params: {
        status: statusFilter || undefined,
        delivery_status: deliveryFilter || undefined,
      }
    }).then(r => r.data),
    refetchInterval: 30000,
  })

  const filtered = orders.filter(o =>
    !search || o.order_number.includes(search) ||
    o.user_name?.includes(search) || o.user_phone?.includes(search)
  )

  const deliveryLabel = (val) => DELIVERY_STATUS.find(s => s.value === val)
  const orderLabel = (val) => ORDER_STATUS.find(s => s.value === val)

  return (
    <div className="container-main py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">مدیریت سفارشات</h1>
        <div className="text-xs text-gray-steel">بروزرسانی هر ۳۰ ثانیه</div>
      </div>

      {/* فیلترها */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="جستجو (شماره سفارش، نام، موبایل)..."
          className="input text-sm col-span-2" />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input text-sm">
          <option value="">همه وضعیت‌ها</option>
          {ORDER_STATUS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select value={deliveryFilter} onChange={e => setDeliveryFilter(e.target.value)} className="input text-sm">
          <option value="">همه وضعیت ارسال</option>
          {DELIVERY_STATUS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {/* آمار سریع */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        {DELIVERY_STATUS.map(s => {
          const count = orders.filter(o => (o.delivery_status || 'pending') === s.value).length
          return (
            <button key={s.value}
              onClick={() => setDeliveryFilter(deliveryFilter === s.value ? '' : s.value)}
              className={`card p-3 text-center cursor-pointer transition-all ${deliveryFilter === s.value ? 'border-brand/50' : ''}`}>
              <div className="text-lg font-bold" style={{ color: s.color }}>{count}</div>
              <div className="text-[10px] text-gray-steel mt-1">{s.label}</div>
            </button>
          )
        })}
      </div>

      {/* لیست سفارشات */}
      {isLoading ? (
        <div className="text-center py-10 text-gray-steel">در حال بارگذاری...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-10 text-gray-steel">سفارشی یافت نشد</div>
      ) : (
        <div className="card overflow-hidden">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)' }}>
                {['شماره سفارش', 'مشتری', 'موبایل', 'مبلغ', 'وضعیت سفارش', 'وضعیت ارسال', 'کد رهگیری', 'آپدیت توسط', 'عملیات'].map(h => (
                  <th key={h} style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((o, i) => {
                const ds = deliveryLabel(o.delivery_status || 'pending')
                const os = orderLabel(o.status)
                return (
                  <tr key={o.order_number}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="font-mono text-xs text-brand">{o.order_number}</span>
                    </td>
                    <td style={{ padding: '10px 12px', color: '#fff', fontSize: 12 }}>{o.user_name || '—'}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{o.user_phone || '—'}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: '#fff' }}>{fmt(o.total_amount)} ت</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: os?.color, background: (os?.color || '#fff') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                        {os?.label || o.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: ds?.color, background: (ds?.color || '#fff') + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                        {ds?.label || '⏳ در انتظار'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 11, color: '#00C896' }}>
                      {o.tracking_code || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 11 }}>
                      {o.updated_by ? (
                        <div>
                          <div style={{ color: '#fff' }}>{o.updated_by}</div>
                          <div style={{ color: 'var(--color-text-secondary)', fontSize: 10 }}>{o.status_updated_at}</div>
                        </div>
                      ) : <span style={{ color: 'var(--color-text-secondary)' }}>—</span>}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <button onClick={() => setSelected(o)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 transition-colors">
                        ✏️ ویرایش
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected && <EditOrderModal order={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
