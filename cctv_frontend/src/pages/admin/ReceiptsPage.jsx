import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import AmountInput from '../../components/ui/AmountInput'
import { formatPrice } from '../../utils/format'
import { formatDate } from '../../utils/date'
import { mediaUrl } from '../../utils/media'
import { UserStamp } from '../../components/ui'

const STATUS_TABS = [
  { value: 'pending',  label: 'در انتظار بررسی' },
  { value: 'approved', label: 'تأیید شده' },
  { value: 'rejected', label: 'رد شده' },
  { value: '',         label: 'همه' },
]

const STATUS_BADGE = {
  pending:  { label: 'در انتظار بررسی', color: '#FF9500' },
  approved: { label: 'تأیید شد',        color: '#00C896' },
  rejected: { label: 'رد شد',           color: '#FF3B3B' },
}

// تاریخ امروز به فرمت YYYY-MM-DD (محلی)
const todayStr = () => new Date().toLocaleDateString('en-CA')

// ─── مودال رد فیش (علت الزامی) ───────────────────────────────
function RejectModal({ receipt, onClose }) {
  const qc = useQueryClient()
  const [reason, setReason] = useState('')

  const mut = useMutation({
    mutationFn: () => api.post(`/orders/admin/receipts/${receipt.id}/reject/`, { reason }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-receipts'])
      toast.success('فیش رد شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در رد فیش'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white">رد فیش واریزی</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="text-xs text-gray-steel mb-3">
          سفارش <span className="font-mono text-brand">{receipt.order_number}</span> — {formatPrice(receipt.amount)}
        </div>
        <label className="label text-xs mb-1 block">علت رد *</label>
        <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
          className="input text-sm resize-none" placeholder="مثلاً: تصویر فیش ناخوانا است" />
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => reason.trim() ? mut.mutate() : toast.error('علت رد را وارد کنید')}
            disabled={mut.isPending}
            className="flex-1 py-2.5 rounded-xl bg-red-500/80 text-white font-semibold text-sm disabled:opacity-50">
            {mut.isPending ? '...' : '✗ رد فیش'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال ثبت فیش به نیابت از مشتری ─────────────────────────
function BehalfModal({ onClose }) {
  const qc = useQueryClient()
  const [orderNumber, setOrderNumber] = useState('')
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [amount, setAmount] = useState('')
  const [paidAt, setPaidAt] = useState(todayStr())
  const [trackingCode, setTrackingCode] = useState('')

  const mut = useMutation({
    mutationFn: (fd) => api.post('/orders/admin/receipts/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-receipts'])
      toast.success('فیش به نیابت ثبت شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ثبت فیش'),
  })

  const pickImage = (e) => {
    const f = e.target.files?.[0] || null
    setImage(f)
    setPreview(f ? URL.createObjectURL(f) : null)
  }

  const submit = () => {
    if (!orderNumber.trim()) return toast.error('شماره سفارش را وارد کنید')
    if (!image) return toast.error('تصویر فیش واریزی الزامی است')
    if (!Number(amount) || Number(amount) <= 0) return toast.error('مبلغ واریز را وارد کنید')
    if (!paidAt) return toast.error('تاریخ واریز را وارد کنید')
    const fd = new FormData()
    fd.append('order_number', orderNumber.trim())
    fd.append('image', image)
    fd.append('amount', String(Number(amount)))
    fd.append('paid_at', paidAt)
    if (trackingCode.trim()) fd.append('tracking_code', trackingCode.trim())
    mut.mutate(fd)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white">ثبت فیش به نیابت از مشتری</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label text-xs mb-1 block">شماره سفارش *</label>
            <input value={orderNumber} onChange={e => setOrderNumber(e.target.value)}
              className="input text-sm font-mono" dir="ltr" placeholder="ORD-..." />
          </div>
          <div>
            <label className="label text-xs mb-1 block">تصویر فیش *</label>
            <input type="file" accept="image/*" capture="environment" onChange={pickImage}
              className="block w-full text-xs text-gray-steel file:ml-3 file:rounded-lg file:border-0 file:bg-brand/15 file:text-brand file:px-3 file:py-2 file:text-xs hover:file:bg-brand/25" />
            <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
              عکس واضح و خوانا از فیش — کادر عمودی (موبایل) مناسب است — حجم تا ۲ مگابایت.
            </p>
            {preview && (
              <img src={preview} alt="پیش‌نمایش فیش"
                className="mt-2 h-28 rounded-lg border border-white/10 object-contain bg-black/30" />
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-xs mb-1 block">مبلغ واریز (ریال) *</label>
              <AmountInput value={amount} onChange={e => setAmount(e.target.value)}
                className="input text-sm" placeholder="0" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">تاریخ واریز *</label>
              <input type="date" value={paidAt} onChange={e => setPaidAt(e.target.value)}
                className="input text-sm" dir="ltr" />
            </div>
          </div>
          <div>
            <label className="label text-xs mb-1 block">کد پیگیری (اختیاری)</label>
            <input value={trackingCode} onChange={e => setTrackingCode(e.target.value)}
              className="input text-sm font-mono" dir="ltr" />
          </div>
        </div>

        <div className="flex gap-3 mt-5">
          <button onClick={submit} disabled={mut.isPending}
            className="flex-1 py-2.5 rounded-xl bg-brand text-white font-semibold text-sm disabled:opacity-50">
            {mut.isPending ? 'در حال ثبت...' : '✓ ثبت فیش'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه مدیریت فیش‌های واریزی ──────────────────────────────
export default function ReceiptsPage() {
  const qc = useQueryClient()
  const [status, setStatus] = useState('pending')
  const [rejecting, setRejecting] = useState(null)
  const [behalfOpen, setBehalfOpen] = useState(false)
  const [search, setSearch] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['admin-receipts', status],
    queryFn: () => api.get('/orders/admin/receipts/', {
      params: { status: status || undefined },
    }).then(r => r.data),
    refetchInterval: 15000,
    refetchOnWindowFocus: 'always',
  })

  const approveMut = useMutation({
    mutationFn: (id) => api.post(`/orders/admin/receipts/${id}/approve/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-receipts'])
      toast.success('فیش تأیید شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در تأیید فیش'),
  })

  const allReceipts = data?.results || data || []
  // جستجو: شماره سفارش / نام مشتری / موبایل (ارقام فارسی هم پشتیبانی می‌شود)
  const toEn = (s) => String(s || '').replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  const q = toEn(search.trim())
  const receipts = !q ? allReceipts : allReceipts.filter(r =>
    toEn(r.order_number).includes(q) ||
    (r.customer_name || r.user_name || '').includes(search.trim()) ||
    toEn(r.customer_phone || r.user_phone).includes(q)
  )

  const approve = (r) => {
    if (window.confirm(`تأیید فیش ${formatPrice(r.amount)} برای سفارش ${r.order_number}؟`))
      approveMut.mutate(r.id)
  }

  return (
    <div className="container-main py-8">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="font-display font-bold text-2xl text-white">فیش‌های واریزی</h1>
        <button onClick={() => setBehalfOpen(true)} className="btn-primary text-sm px-5 py-2.5">
          + ثبت فیش به نیابت
        </button>
      </div>

      {/* فیلتر وضعیت + جستجو */}
      <div className="flex gap-2 mb-6 flex-wrap items-center">
        {STATUS_TABS.map(t => (
          <button key={t.value} onClick={() => setStatus(t.value)}
            className={`text-xs px-4 py-2 rounded-xl border transition-all
              ${status === t.value
                ? 'border-brand bg-brand/10 text-brand'
                : 'border-white/10 text-gray-steel hover:border-brand/40'}`}>
            {t.label}
          </button>
        ))}
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="جستجو: شماره سفارش، نام، موبایل..."
          className="input text-xs py-2 flex-1 min-w-[200px] max-w-xs" />
      </div>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel">در حال بارگذاری...</div>
      ) : receipts.length === 0 ? (
        <div className="text-center py-10 text-gray-steel">فیشی یافت نشد</div>
      ) : (
        <div className="card overflow-hidden overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 900 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)' }}>
                {['فیش', 'سفارش', 'مشتری', 'موبایل', 'مبلغ', 'تاریخ واریز', 'کد پیگیری', 'ثبت‌کننده', 'وضعیت', 'عملیات'].map(h => (
                  <th key={h} style={{ padding: '12px', textAlign: h === 'موبایل' ? 'center' : 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {receipts.map((r, i) => {
                const st = STATUS_BADGE[r.status] || { label: r.status, color: '#888' }
                const img = mediaUrl(r.image_url || r.image)
                return (
                  <tr key={r.id}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px' }}>
                      {img ? (
                        <a href={img} target="_blank" rel="noreferrer">
                          <img src={img} alt="فیش" className="w-12 h-12 rounded-lg object-cover border border-white/10 hover:opacity-80 transition-opacity" />
                        </a>
                      ) : '—'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <Link to="/admin/orders-management" className="font-mono text-xs text-brand hover:underline">
                        {r.order_number}
                      </Link>
                      <div className="text-[10px] text-gray-steel mt-0.5">{formatDate(r.created_at, { withTime: true })}</div>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--color-text-primary)' }}>
                      {r.customer_name || r.user_name || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap', textAlign: 'center' }} dir="ltr">
                      {r.customer_phone || r.user_phone || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--color-text-primary)', whiteSpace: 'nowrap' }}>
                      {formatPrice(r.amount)}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(r.paid_at)}</td>
                    <td style={{ padding: '10px 12px', fontSize: 11 }} dir="ltr">{r.tracking_code || '—'}</td>
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                      <UserStamp createdBy={r.uploaded_by_name} createdAt={r.created_at} />
                    </td>
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                      <span style={{ color: st.color, background: st.color + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                        {st.label}
                      </span>
                      {r.status === 'rejected' && r.reject_reason && (
                        <div className="text-[10px] text-red-400 mt-1 max-w-[160px]">{r.reject_reason}</div>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                      {r.status === 'pending' && (
                        <div className="flex gap-2">
                          <button onClick={() => approve(r)} disabled={approveMut.isPending}
                            className="text-xs px-3 py-1.5 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 transition-colors disabled:opacity-40">
                            ✓ تایید
                          </button>
                          <button onClick={() => setRejecting(r)}
                            className="text-xs px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors">
                            ✗ رد
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {rejecting && <RejectModal receipt={rejecting} onClose={() => setRejecting(null)} />}
      {behalfOpen && <BehalfModal onClose={() => setBehalfOpen(false)} />}
    </div>
  )
}
