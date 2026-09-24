import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import useAuthStore from '../../store/useAuthStore'
import { formatDate } from '../../utils/date'
import { mediaUrl } from '../../utils/media'
import { UserStamp } from '../../components/ui'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function fmtDate(iso) { return iso ? new Date(iso).toLocaleDateString('fa-IR') : '—' }

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
  { value: 'ready_to_ship',    label: 'منتظر ارسال', color: '#00C896' },
  { value: 'shipped',          label: 'ارسال شده', color: '#0066FF' },
  { value: 'cancelled',        label: 'لغو شده', color: '#FF3B3B' },
  { value: 'rejected',         label: 'رد شده', color: '#F43F5E' },
]

const STATUS_CARDS = [
  { value: 'pending',          label: 'در انتظار تایید', color: '#FF9500' },
  { value: 'awaiting_payment', label: 'در انتظار پرداخت', color: '#8B5CF6' },
  { value: 'ready_to_ship',    label: 'در انتظار ارسال', color: '#00C896' },
  { value: 'shipped',          label: 'ارسال شده',       color: '#0066FF', delivery: true },
  { value: 'rejected',         label: 'رد شده',          color: '#F43F5E' },
]

const SETTLEMENTS = [
  { value: 'cash',   label: 'نقدی' },
  { value: 'credit', label: 'تو حسابی' },
  { value: 'month1', label: 'یکماهه' },
  { value: 'month2', label: 'دوماهه' },
]

const SHIPPING_METHODS = [
  { value: '',        label: '—' },
  { value: 'post',    label: 'پست' },
  { value: 'courier', label: 'پیک' },
  { value: 'freight', label: 'باربری' },
]

// ─── Modal ویرایش وضعیت ──────────────────────────────────────
function EditOrderModal({ order, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    delivery_status: order.delivery_status || 'pending',
    courier_company: order.courier_company || '',
    tracking_code:   order.tracking_code || '',
    status:          order.status || 'pending',
    shipping_method: order.shipping_method || '',
    settlement_type: order.settlement_type || 'cash',
    settlement_due_date: order.settlement_due_date || '',
    confirmed_amount: order.confirmed_amount || '',
    admin_notes:     order.admin_notes || '',
  })
  const [msg, setMsg] = useState(null)

  const mut = useMutation({
    mutationFn: (data) => api.patch(`/orders/admin/${order.order_number}/update/`, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-orders'])
      qc.invalidateQueries(['admin-order-detail', order.order_number])
      setMsg({ type: 'success', text: 'ذخیره شد' })
      setTimeout(onClose, 800)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  function handleSave() {
    const payload = {
      ...form,
      confirmed_amount: Number(form.confirmed_amount) || 0,
    }
    // تو حسابی — موعد خودکار ۱۴ روزه است و تاریخ دستی ارسال نمی‌شود (بک‌اند خودش می‌گذارد)
    if (form.settlement_type === 'credit') delete payload.settlement_due_date
    else payload.settlement_due_date = form.settlement_due_date || null
    mut.mutate(payload)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-xs mb-1 block">نحوه تسویه</label>
              <select value={form.settlement_type}
                onChange={e => setForm(f => ({ ...f, settlement_type: e.target.value }))}
                className="input text-sm">
                {SETTLEMENTS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">موعد تسویه</label>
              {form.settlement_type === 'credit' ? (
                <div className="input text-sm text-gray-steel">۱۴ روز پس از تأیید (خودکار)</div>
              ) : (
                <input type="date" value={form.settlement_due_date || ''}
                  onChange={e => setForm(f => ({ ...f, settlement_due_date: e.target.value }))}
                  className="input text-sm" dir="ltr" />
              )}
            </div>
          </div>

          <div>
            <label className="label text-xs mb-1 block">مبلغ تأییدشده (ریال)</label>
            <input type="number" min="0" value={form.confirmed_amount}
              onChange={e => setForm(f => ({ ...f, confirmed_amount: e.target.value }))}
              className="input text-sm" dir="ltr" placeholder="0 = استفاده از مبلغ سفارش" />
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
            <label className="label text-xs mb-1 block">نحوه ارسال (انتخاب مشتری)</label>
            <select value={form.shipping_method}
              onChange={e => setForm(f => ({ ...f, shipping_method: e.target.value }))}
              className="input text-sm">
              {SHIPPING_METHODS.map(s => (
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

          <div>
            <label className="label text-xs mb-1 block">یادداشت ادمین</label>
            <textarea value={form.admin_notes} rows={2}
              onChange={e => setForm(f => ({ ...f, admin_notes: e.target.value }))}
              className="input text-sm resize-none" />
          </div>
        </div>

        {msg && (
          <div className={`mt-4 rounded-lg px-4 py-2 text-sm ${msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {msg.text}
          </div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSave} disabled={mut.isPending}
            className="flex-1 py-2.5 rounded-xl bg-brand text-white font-semibold text-sm disabled:opacity-50">
            {mut.isPending ? 'در حال ذخیره...' : '✓ ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── ردیف قلم قابل ویرایش در مودال جزئیات ─────────────────────
const DUE_LABELS = { cash: 'همان روز تأیید', credit: '۱۴ روز پس از تأیید', month1: '۳۰ روز پس از تأیید', month2: '۶۰ روز پس از تأیید' }

function ItemRow({ item, orderNumber, index, onChanged, showDate }) {
  const [qty, setQty] = useState(String(item.quantity))
  const [saving, setSaving] = useState(false)
  const [qtyFocus, setQtyFocus] = useState(false)

  const dirty = Number(qty) !== item.quantity

  async function save() {
    setSaving(true)
    try {
      await api.patch(`/orders/admin/${orderNumber}/items/${item.id}/`, {
        quantity: Number(qty),
      })
      toast.success('قلم به‌روز شد')
      onChanged()
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ذخیره قلم')
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: index % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
      <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{fmt(index + 1)}</td>
      <td style={{ padding: '10px 12px' }}>
        {item.product_name}
        <div className="text-gray-steel text-[10px] mt-0.5" dir="ltr">{item.sku}</div>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <input type="number" min="0" value={qty} onChange={e => setQty(e.target.value)}
          onFocus={() => setQtyFocus(true)} onBlur={() => setQtyFocus(false)}
          className="input text-xs w-20 text-center" dir="ltr" title="۰ = حذف قلم" />
        {qtyFocus && (
          <div className={`text-[10px] mt-1 whitespace-nowrap ${Number(qty) > (item.available_stock ?? Infinity) ? 'text-amber-400 font-bold' : 'text-gray-steel'}`}>
            موجودی: {fmt(item.available_stock ?? 0)}
            {Number(qty) > (item.available_stock ?? Infinity) && ' ⚠️ بیشتر از موجودی'}
            {/* تفکیک موجودی به انبار — 🔒 یعنی انبار بدون تیک «نمایش به مشتری» */}
            {item.stocks?.map(s => (
              <div key={s.warehouse}>
                {s.warehouse}: {fmt(s.quantity)}{!s.is_public && ' 🔒'}
              </div>
            ))}
          </div>
        )}
      </td>
      <td style={{ padding: '10px 12px' }}>{fmt(item.confirmed_unit_price || item.unit_price)} ریال</td>
      <td style={{ padding: '10px 12px', fontWeight: 600 }}>{fmt((item.confirmed_unit_price || item.unit_price) * (Number(qty) || 0))} ریال</td>
      <td style={{ padding: '10px 12px', fontSize: 11, whiteSpace: 'nowrap' }}>
        {showDate && item.settlement_due_date ? (
          <span className={item.is_settlement_due ? 'text-red-400 font-bold' : 'text-gray-steel'}>
            {item.is_settlement_due ? '⚠️ ' : ''}{fmtDate(item.settlement_due_date)}
          </span>
        ) : (
          <span className="text-gray-steel">{DUE_LABELS[item.settlement_type] || '—'}</span>
        )}
      </td>
      <td style={{ padding: '10px 12px' }}>
        <button onClick={save} disabled={!dirty || saving}
          className="text-xs px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all disabled:opacity-40">
          {saving ? '...' : '✓'}
        </button>
      </td>
    </tr>
  )
}

// ─── مودال رد پیش‌فاکتور (علت الزامی) ────────────────────────
function RejectOrderModal({ orderNumber, onClose }) {
  const qc = useQueryClient()
  const [reason, setReason] = useState('')

  const mut = useMutation({
    mutationFn: () => api.post(`/orders/admin/${orderNumber}/reject/`, { reason }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-orders'])
      qc.invalidateQueries(['admin-order-detail', orderNumber])
      toast.success('پیش‌فاکتور رد شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در رد پیش‌فاکتور'),
  })

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white">رد پیش‌فاکتور</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>
        <div className="text-xs text-gray-steel mb-3">
          سفارش <span className="font-mono text-brand">{orderNumber}</span>
        </div>
        <label className="label text-xs mb-1 block">علت رد *</label>
        <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
          className="input text-sm resize-none" placeholder="مثلاً: موجودی کافی نیست / قیمت توافق نشد" />
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => reason.trim() ? mut.mutate() : toast.error('علت رد را وارد کنید')}
            disabled={mut.isPending}
            className="flex-1 py-2.5 rounded-xl bg-red-500/80 text-white font-semibold text-sm disabled:opacity-50">
            {mut.isPending ? '...' : '✗ رد پیش‌فاکتور'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── بخش فیش‌های واریزی داخل مودال جزئیات سفارش ───────────────
const RECEIPT_STATUS = {
  pending:  { label: 'در انتظار بررسی', cls: 'bg-amber-500/15 text-amber-400' },
  approved: { label: 'تأیید شد',        cls: 'bg-green-500/15 text-green-400' },
  rejected: { label: 'رد شد',           cls: 'bg-red-500/15 text-red-400' },
}

function OrderReceiptsSection({ receipts, orderNumber }) {
  const qc = useQueryClient()
  const [rejecting, setRejecting] = useState(null) // فیش در حال رد
  const [reason, setReason] = useState('')

  const invalidate = () => {
    qc.invalidateQueries(['admin-order-detail', orderNumber])
    qc.invalidateQueries(['admin-orders'])
    qc.invalidateQueries(['admin-receipts'])
  }
  const approveMut = useMutation({
    mutationFn: (id) => api.post(`/orders/admin/receipts/${id}/approve/`),
    onSuccess: () => { toast.success('فیش تأیید و به روش FIFO تخصیص یافت'); invalidate() },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در تأیید فیش'),
  })
  const rejectMut = useMutation({
    mutationFn: ({ id, reason }) => api.post(`/orders/admin/receipts/${id}/reject/`, { reason }),
    onSuccess: () => { toast.success('فیش رد شد'); setRejecting(null); setReason(''); invalidate() },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در رد فیش'),
  })

  if (!receipts?.length) return null
  return (
    <div className="mb-5">
      <h3 className="text-sm font-semibold text-white mb-3">🧾 فیش‌های واریزی</h3>
      <div className="space-y-2">
        {receipts.map(r => {
          const st = RECEIPT_STATUS[r.status] || RECEIPT_STATUS.pending
          return (
            <div key={r.id} className="bg-white/5 rounded-xl p-3 flex items-center gap-3">
              <a href={mediaUrl(r.image_url || r.image)} target="_blank" rel="noreferrer" className="shrink-0">
                <img src={mediaUrl(r.image_url || r.image)} alt="فیش"
                  className="w-14 h-14 object-cover rounded-lg border border-white/10 hover:border-brand/50 transition-colors" />
              </a>
              <div className="flex-1 text-xs">
                <div className="font-semibold text-white">{fmt(r.amount)} ریال</div>
                <div className="text-gray-steel mt-0.5">
                  {formatDate(r.paid_at)}{r.tracking_code ? ` — پیگیری: ${r.tracking_code}` : ''}
                </div>
                {r.status === 'rejected' && r.reject_reason && (
                  <div className="text-red-400 mt-0.5">دلیل رد: {r.reject_reason}</div>
                )}
              </div>
              <span className={`text-[10px] px-2 py-1 rounded-full ${st.cls}`}>{st.label}</span>
              {r.status === 'pending' && (
                <div className="flex gap-2">
                  <button onClick={() => approveMut.mutate(r.id)} disabled={approveMut.isPending}
                    className="text-xs px-3 py-1.5 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 transition-colors disabled:opacity-50">
                    ✓ تأیید
                  </button>
                  <button onClick={() => { setRejecting(r.id); setReason('') }}
                    className="text-xs px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors">
                    ✗ رد
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* مودال دلیل رد */}
      {rejecting && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4">
          <div className="card p-6 w-full max-w-md">
            <h3 className="font-bold text-white mb-3">رد فیش واریزی</h3>
            <label className="label text-xs mb-1 block">دلیل رد *</label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              className="input text-sm resize-none" placeholder="مثلاً: مبلغ فیش با سفارش مطابقت ندارد" />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => reason.trim() ? rejectMut.mutate({ id: rejecting, reason }) : toast.error('دلیل رد را وارد کنید')}
                disabled={rejectMut.isPending}
                className="flex-1 py-2.5 rounded-xl bg-red-500/80 text-white font-semibold text-sm disabled:opacity-50">
                {rejectMut.isPending ? '...' : '✗ رد فیش'}
              </button>
              <button onClick={() => setRejecting(null)} className="btn-secondary px-6 py-2.5">انصراف</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── مودال جزئیات سفارش + اقلام + تأیید استعلام ─────────────
function OrderDetailModal({ orderNumber, onClose, onEdit }) {
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const [confirmForm, setConfirmForm] = useState({ confirmed_amount: '', sarraf_account_number: '', sarraf_account_holder: '' })
  const [rejectOpen, setRejectOpen] = useState(false)

  const { data: order, isLoading } = useQuery({
    queryKey: ['admin-order-detail', orderNumber],
    queryFn: () => api.get(`/orders/admin/${orderNumber}/detail/`).then(r => r.data),
  })

  // پیش‌فرض مبلغ نهایی = جمع اقلام نقدی (قابل ویرایش توسط پرسنل)
  const cashSum = (order?.items || [])
    .filter(it => it.settlement_type === 'cash')
    .reduce((s, it) => s + (it.confirmed_unit_price || it.unit_price) * it.quantity, 0)
  useEffect(() => {
    if (cashSum > 0) setConfirmForm(f => f.confirmed_amount ? f : { ...f, confirmed_amount: String(cashSum) })
  }, [cashSum])

  const confirmMut = useMutation({
    mutationFn: (payload) => api.post(`/orders/admin/${orderNumber}/confirm/`, payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-orders'])
      qc.invalidateQueries(['admin-order-detail', orderNumber])
      toast.success('سفارش تأیید شد')
      onClose()
    },
    onError: (e) => {
      const d = e.response?.data
      const msg = d?.error || d?.detail ||
        (d && typeof d === 'object' ? Object.values(d).flat().find(v => typeof v === 'string') : null) ||
        'خطا در تأیید سفارش'
      toast.error(msg)
    },
  })

  // حذف کامل سفارش ردشده — فقط سوپریوزر، غیرقابل بازگشت
  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/orders/admin/${orderNumber}/`),
    onSuccess: () => {
      qc.invalidateQueries(['admin-orders'])
      toast.success('سفارش به‌طور کامل حذف شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف سفارش'),
  })

  function handleDelete() {
    if (window.confirm(`⚠️ حذف کامل و غیرقابل بازگشت!\n\nسفارش ${orderNumber} و تمام سوابق آن برای همیشه از سیستم پاک می‌شود.\nاین عمل قابل بازگشت نیست — مطمئن هستید؟`)) {
      deleteMut.mutate()
    }
  }

  function handleConfirm() {
    // سفارش اعتباری: مبلغ = جمع اقلام (نیازی به ورودی نیست)؛ سفارش نقدی: مبلغ از پرسنل
    const amount = hasCashItem ? Number(confirmForm.confirmed_amount) : Number(order.total_amount)
    if (!amount || amount <= 0) return toast.error('مبلغ نهایی را وارد کنید')
    // برای سفارش‌های دارای قلم نقدی، حساب صراف الزامی است (بک‌اند هم بدون آن ۴۰۰ می‌دهد)
    if (hasCashItem && (!confirmForm.sarraf_account_number.trim() || !confirmForm.sarraf_account_holder.trim()))
      return toast.error('برای سفارش دارای قلم نقدی، شماره حساب و نام صراف الزامی است')
    confirmMut.mutate({
      confirmed_amount: amount,
      sarraf_account_number: confirmForm.sarraf_account_number.trim() || undefined,
      sarraf_account_holder: confirmForm.sarraf_account_holder.trim() || undefined,
    })
  }

  const canConfirm = order?.status === 'pending'
  const hasCashItem = !!order?.items?.some(it => it.settlement_type === 'cash')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">جزئیات سفارش</h2>
            <div className="font-mono text-xs text-brand mt-1">{orderNumber}</div>
            {order && (order.created_by || order.updated_by) && (
              <div className="mt-1.5">
                <UserStamp createdBy={order.created_by} updatedBy={order.updated_by} createdAt={order.created_at} inline />
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => onEdit(order)}
              className="text-xs px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all">
              ✏️ ویرایش
            </button>
            <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
          </div>
        </div>

        {isLoading || !order ? (
          <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : (
          <>
            {/* اطلاعات کلی */}
            <div className="grid grid-cols-4 gap-3 mb-5 text-xs">
              <div className="bg-white/5 rounded-xl p-3">
                <div className="text-gray-steel mb-1">مشتری</div>
                <div className="text-white font-semibold">{order.user_name || '—'}</div>
                <div className="text-gray-steel mt-0.5" dir="ltr">{order.user_phone}</div>
              </div>
              <div className="bg-white/5 rounded-xl p-3">
                <div className="text-gray-steel mb-1">وضعیت</div>
                <div className="text-white font-semibold">{order.status_display}</div>
                <div className="text-gray-steel mt-0.5">{order.order_type_display}</div>
              </div>
              <div className="bg-white/5 rounded-xl p-3">
                <div className="text-gray-steel mb-1">نحوه تسویه</div>
                <div className="text-white font-semibold">
                  {[...new Set((order.items || []).map(it => it.settlement_display).filter(Boolean))].join('، ') || order.settlement_display || '—'}
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-3">
                <div className="text-gray-steel mb-1">مبلغ {order.confirmed_amount ? 'تأییدشده' : 'سفارش'}</div>
                <div className="text-white font-semibold">{fmt(order.effective_amount)} ریال</div>
                {order.confirmed_amount > 0 && order.confirmed_amount !== order.total_amount && (
                  <div className="text-gray-steel mt-0.5 line-through">{fmt(order.total_amount)}</div>
                )}
              </div>
            </div>

            {/* نحوه ارسال و آدرس */}
            {(order.shipping_method_display || order.shipping_address) && (
              <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
                {order.shipping_method_display && (
                  <div className="bg-white/5 rounded-xl p-3">
                    <div className="text-gray-steel mb-1">نحوه ارسال</div>
                    <div className="text-white font-semibold">🚚 {order.shipping_method_display}</div>
                  </div>
                )}
                {order.shipping_address && (
                  <div className="bg-white/5 rounded-xl p-3">
                    <div className="text-gray-steel mb-1">آدرس ارسال</div>
                    <div>{order.shipping_address}</div>
                  </div>
                )}
              </div>
            )}

            {/* اقلام — تعداد واقعی قابل ارسال و تسویه هر قلم قابل ویرایش است */}
            <h3 className="text-sm font-semibold text-white mb-3">اقلام سفارش</h3>
            <div className="overflow-x-auto mb-2">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                    {['#', 'محصول', 'تعداد', 'قیمت واحد', 'جمع', 'موعد', ''].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {order.items.map((it, i) => (
                    <ItemRow key={it.id} item={it} orderNumber={orderNumber} index={i}
                      showDate={order.status !== 'pending'}
                      onChanged={() => {
                        qc.invalidateQueries(['admin-order-detail', orderNumber])
                        qc.invalidateQueries(['admin-orders'])
                      }} />
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-[10px] text-gray-steel mb-5">
              تعداد صفر یعنی حذف قلم — مبلغ کل سفارش خودکار بازمحاسبه می‌شود
            </div>

            {/* فیش‌های واریزی این سفارش */}
            <OrderReceiptsSection receipts={order.receipts} orderNumber={orderNumber} />

            {(order.customer_notes || order.admin_notes) && (
              <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
                {order.customer_notes && (
                  <div className="bg-white/5 rounded-xl p-3">
                    <div className="text-gray-steel mb-1">یادداشت مشتری</div>
                    <div>{order.customer_notes}</div>
                  </div>
                )}
                {order.admin_notes && (
                  <div className="bg-white/5 rounded-xl p-3">
                    <div className="text-gray-steel mb-1">یادداشت ادمین</div>
                    <div>{order.admin_notes}</div>
                  </div>
                )}
              </div>
            )}

            {/* اطلاعات رد سفارش */}
            {order.status === 'rejected' && (
              <div className="border border-red-500/30 bg-red-500/10 rounded-xl p-4 mb-5 text-xs">
                <div className="text-red-400 font-semibold mb-2">✗ این پیش‌فاکتور رد شده است</div>
                <div className="text-gray-steel mb-1">علت رد: <span className="text-white">{order.reject_reason || '—'}</span></div>
                <div className="text-gray-steel">تاریخ رد: <span className="text-white">{formatDate(order.rejected_at, { withTime: true })}</span></div>
                {user?.is_superuser === true && (
                  <button onClick={handleDelete} disabled={deleteMut.isPending}
                    className="mt-3 text-xs px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 transition-colors font-semibold disabled:opacity-50">
                    {deleteMut.isPending ? 'در حال حذف...' : '🗑 حذف کامل'}
                  </button>
                )}
              </div>
            )}

            {/* تأیید سفارش استعلامی */}
            {canConfirm && (
              <div className="border border-brand/30 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-white mb-3">✅ تأیید سفارش استعلامی</h3>
                {hasCashItem && (
                  <div className="grid grid-cols-1 gap-3">
                    <div>
                      <label className="label text-xs mb-1 block">مبلغ نهایی (ریال) *</label>
                      <input type="number" min="1" value={confirmForm.confirmed_amount}
                        onChange={e => setConfirmForm(f => ({ ...f, confirmed_amount: e.target.value }))}
                        className="input text-sm" dir="ltr" placeholder={String(cashSum || order.total_amount)} />
                      {cashSum > 0 && (
                        <div className="text-[10px] text-gray-steel mt-1">
                          پیش‌فرض = جمع اقلام نقدی ({fmt(cashSum)} ریال) — قابل تغییر است
                        </div>
                      )}
                    </div>
                  </div>
                )}
                {hasCashItem && (
                  <>
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      <div>
                        <label className="label text-xs mb-1 block">شماره حساب/کارت صراف *</label>
                        <input value={confirmForm.sarraf_account_number}
                          onChange={e => setConfirmForm(f => ({ ...f, sarraf_account_number: e.target.value }))}
                          className="input text-sm font-mono" dir="ltr" placeholder="6037-XXXX-XXXX-XXXX" />
                      </div>
                      <div>
                        <label className="label text-xs mb-1 block">نام صراف / صاحب حساب *</label>
                        <input value={confirmForm.sarraf_account_holder}
                          onChange={e => setConfirmForm(f => ({ ...f, sarraf_account_holder: e.target.value }))}
                          className="input text-sm" placeholder="مثلاً: صرافی پارسیان — علی رضایی" />
                      </div>
                    </div>
                    <div className="text-[10px] text-amber-400 mt-2">⚠️ این سفارش قلم نقدی دارد — وارد کردن حساب صراف الزامی است</div>
                  </>
                )}
                <button onClick={handleConfirm} disabled={confirmMut.isPending}
                  className="btn-primary text-sm px-6 py-2.5 mt-4 disabled:opacity-50">
                  {confirmMut.isPending ? 'در حال تأیید...' : (hasCashItem ? '✓ تأیید و ارسال لینک پرداخت' : '✓ تأیید سفارش')}
                </button>
                <button onClick={() => setRejectOpen(true)}
                  className="mr-2 text-sm px-6 py-2.5 mt-4 rounded-xl bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25 transition-colors font-semibold">
                  ✗ رد پیش‌فاکتور
                </button>
              </div>
            )}
          </>
        )}
      </div>
      {rejectOpen && <RejectOrderModal orderNumber={orderNumber} onClose={() => setRejectOpen(false)} />}
    </div>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
export default function AdminOrdersPage() {
  // فیلتر اولیه از URL — لینک بج منو با ?status=pending مستقیم به سفارش‌های در انتظار می‌آید
  const [searchParams] = useSearchParams()
  const [selected, setSelected] = useState(null)
  // لینک مستقیم به مودال جزئیات یک سفارش: ?order=OR-1008
  const [detailOf, setDetailOf] = useState(searchParams.get('order') || null)
  const [search, setSearch] = useState('')
  const [dueOnly, setDueOnly] = useState(false)
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ['admin-orders', statusFilter],
    queryFn: () => api.get('/orders/admin/orders/', {
      params: {
        // «ارسال شده» وضعیت سفارش نیست — روی وضعیت ارسال فیلتر می‌شود
        status: statusFilter && statusFilter !== 'shipped' ? statusFilter : undefined,
        delivery_status: statusFilter === 'shipped' ? 'shipped' : undefined,
      }
    }).then(r => r.data),
    refetchInterval: 10000,
    refetchOnWindowFocus: 'always',
  })

  const { data: badges } = useQuery({
    queryKey: ['admin-badges'],
    queryFn: () => api.get('/users/admin-badges/').then(r => r.data),
    refetchInterval: 60000,
  })
  const dueCount = badges?.orders_due ?? orders.filter(o => o.is_settlement_due).length

  const filtered = orders.filter(o =>
    (!dueOnly || o.is_settlement_due) &&
    (!search || o.order_number.includes(search) ||
    o.user_name?.includes(search) || o.user_phone?.includes(search))
  )

  const orderLabel = (val) => ORDER_STATUS.find(s => s.value === val)

  return (
    <div className="container-main py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">مدیریت سفارشات</h1>
        <div className="text-xs text-gray-steel">بروزرسانی هر ۱۰ ثانیه</div>
      </div>

      {/* هشدار سررسید تسویه */}
      {dueCount > 0 && (
        <button onClick={() => setDueOnly(d => !d)}
          className={`w-full mb-6 rounded-xl px-4 py-3 text-sm font-semibold text-right transition-all border
            ${dueOnly ? 'bg-red-500/25 border-red-500/50' : 'bg-red-500/15 border-red-500/30 hover:bg-red-500/20'} text-red-400`}>
          ⚠️ {fmt(dueCount)} سفارش به موعد تسویه رسیده — برای مشاهده کلیک کنید
        </button>
      )}

      {/* فیلترها */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="جستجو (شماره سفارش، نام، موبایل)..."
          className="input text-sm col-span-2" />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input text-sm">
          <option value="">همه وضعیت‌ها</option>
          {STATUS_CARDS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {/* آمار سریع — هم‌راستا با فیلتر وضعیت */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        {STATUS_CARDS.map(s => {
          const count = s.delivery
            ? orders.filter(o => (o.delivery_status || 'pending') === s.value).length
            : orders.filter(o => o.status === s.value).length
          return (
            <button key={s.value}
              onClick={() => setStatusFilter(statusFilter === s.value ? '' : s.value)}
              className={`card p-3 text-center cursor-pointer transition-all ${statusFilter === s.value ? 'border-brand/50' : ''}`}>
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
                {['شماره سفارش', 'مشتری', 'موبایل', 'مبلغ', 'نحوه تسویه', 'نحوه ارسال', 'وضعیت سفارش', 'آخرین تغییر'].map(h => (
                  <th key={h} style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((o, i) => {
                const os = orderLabel(o.status)
                // پیش‌فاکتور همکار: فقط تا قبل از تأیید — بعد از تأیید: نقدی→منتظر پرداخت، اعتباری→منتظر ارسال
                const preInvoice = o.customer_is_partner && ['pending', 'confirmed'].includes(o.status)
                return (
                  <tr key={o.order_number} onClick={() => setDetailOf(o.order_number)}
                    className="cursor-pointer hover:bg-white/5 transition-colors"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="font-mono text-xs text-brand">{o.order_number}</span>
                      <div className="text-[10px] text-gray-steel mt-0.5">{fmt(o.items_count)} قلم</div>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-primary)', fontSize: 12 }}>{o.user_name || '—'}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{o.user_phone || '—'}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {fmt(o.effective_amount || o.total_amount)} ریال
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      {/* سفارش‌ها از checkout به تفکیک نقدی/اعتباری ثبت می‌شوند — تسویه سطح سفارش قابل اتکاست */}
                      {o.settlement_type === 'cash' ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-green-500/15 text-green-400">نقدی</span>
                      ) : (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">اعتباری</span>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-secondary)' }}>
                      {o.shipping_method_display || '—'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: preInvoice ? '#FBC02D' : os?.color, background: (preInvoice ? '#FBC02D' : (os?.color || '#fff')) + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>
                        {preInvoice ? 'پیش‌فاکتور' : (os?.label || o.status)}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>
                      {o.updated_by || '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected && <EditOrderModal order={selected} onClose={() => setSelected(null)} />}
      {detailOf && (
        <OrderDetailModal
          orderNumber={detailOf}
          onClose={() => setDetailOf(null)}
          onEdit={(o) => { setDetailOf(null); setSelected(o) }}
        />
      )}
    </div>
  )
}
