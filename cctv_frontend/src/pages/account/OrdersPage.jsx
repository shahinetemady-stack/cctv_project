import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { orderService, paymentService } from '../../services/orders'
import { PageLoader } from '../../components/ui'
import Seo from '../../components/Seo'
import AmountInput from '../../components/ui/AmountInput'
import useAuthStore from '../../store/useAuthStore'
import { formatPrice } from '../../utils/format'
import { formatDate, todayTehran } from '../../utils/date'
import { mediaUrl } from '../../utils/media'

const STATUS = {
  pending:          { label: 'در انتظار تأیید',    color: '#FF9500', bg: 'rgba(255,149,0,0.1)' },
  confirmed:        { label: 'تأیید شده',           color: '#0066FF', bg: 'rgba(0,102,255,0.1)' },
  awaiting_payment: { label: 'در انتظار پرداخت',   color: '#8B5CF6', bg: 'rgba(139,92,246,0.1)' },
  paid:             { label: 'پرداخت شده',          color: '#00C896', bg: 'rgba(0,200,150,0.1)' },
  ready_to_ship:    { label: 'منتظر ارسال',         color: '#00C896', bg: 'rgba(0,200,150,0.1)' },
  shipped:          { label: 'ارسال شده',           color: '#0066FF', bg: 'rgba(0,102,255,0.1)' },
  cancelled:        { label: 'لغو شده',             color: '#FF3B3B', bg: 'rgba(255,59,59,0.1)' },
}

const SHIPPING = { post: '📮 پست', courier: '🛵 پیک', freight: '🚛 باربری' }
const PAYMENT_METHOD = { cash: 'نقد', transfer: 'کارت به کارت', online: 'آنلاین', check: 'چک' }

const RECEIPT_STATUS = {
  pending:  { label: 'در انتظار بررسی', cls: 'bg-amber-500/15 text-amber-400 border border-amber-500/30' },
  approved: { label: 'تأیید شد',        cls: 'bg-green-500/15 text-green-400 border border-green-500/30' },
  rejected: { label: 'رد شد',           cls: 'bg-red-500/15 text-red-400 border border-red-500/30' },
}

// تاریخ امروز به فرمت YYYY-MM-DD (محلی، نه UTC)
const todayStr = todayTehran

// مبلغ قابل پرداخت سفارش — اولویت با مانده اقلام تسویه، بعد مبلغ تأییدشده، بعد جمع سفارش
function payableAmount(order) {
  const lines = order.settlement_lines || []
  const remaining = lines.reduce((s, l) => s + Number(l.remaining_amount || 0), 0)
  if (lines.length > 0) return formatPrice(remaining)
  if (order.confirmed_amount) return formatPrice(order.confirmed_amount)
  return `${Number(order.total_amount || 0).toLocaleString('fa-IR')} ریال`
}

// ─── کارت اطلاعات واریز صراف ─────────────────────────────────
function SarrafCard({ order }) {
  if (!order.sarraf_account_number) return null

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(order.sarraf_account_number)
      toast.success('شماره حساب کپی شد')
    } catch {
      toast.error('کپی ناموفق بود')
    }
  }

  return (
    <div className="rounded-lg border border-brand/25 bg-brand/5 px-3 py-2.5 mb-2">
      <div className="text-xs text-brand dark:text-cyan font-medium mb-1.5">💳 اطلاعات واریز</div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-mono text-sm text-white tracking-wider" dir="ltr">{order.sarraf_account_number}</span>
        <button onClick={copy}
          className="text-[10px] px-2 py-1 rounded-lg border border-brand/30 text-brand dark:text-cyan hover:bg-brand/10 transition-colors">
          📋 کپی
        </button>
      </div>
      {order.sarraf_account_holder && (
        <div className="text-xs text-gray-steel mt-1">صاحب حساب: {order.sarraf_account_holder}</div>
      )}
      <div className="text-xs text-gray-steel mt-1">
        مبلغ قابل پرداخت: <span className="text-white font-bold">{payableAmount(order)}</span>
      </div>
    </div>
  )
}

// ─── اقلام تسویه ──────────────────────────────────────────────
function SettlementLines({ order }) {
  const lines = order.settlement_lines || []
  if (lines.length === 0) return null

  return (
    <div className="rounded-lg bg-white/5 px-3 py-2.5 mb-2">
      <div className="text-xs text-gray-steel font-medium mb-2">اقلام تسویه</div>
      <div className="space-y-1.5">
        {lines.map(l => (
          <div key={l.id}
            className={`text-xs rounded-lg px-2.5 py-2 ${l.is_overdue ? 'bg-red-500/10 border border-red-500/25' : 'bg-white/5'}`}>
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className={l.is_overdue ? 'text-red-400 font-medium' : 'text-gray-300'}>
                {l.settlement_display}
              </span>
              {l.is_overdue && (
                <span className="text-[10px] text-red-400 font-bold">
                  ⚠️ {Number(l.days_overdue).toLocaleString('fa-IR')} روز گذشته
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-gray-steel flex-wrap">
              <span>مبلغ: {formatPrice(l.amount)}</span>
              <span>پرداخت‌شده: {formatPrice(l.paid_amount)}</span>
              <span className={l.is_overdue ? 'text-red-400' : 'text-white'}>مانده: {formatPrice(l.remaining_amount)}</span>
              {l.due_date && <span>سررسید: {formatDate(l.due_date)}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── فرم ثبت فیش واریزی ──────────────────────────────────────
function ReceiptForm({ order, onDone }) {
  const qc = useQueryClient()
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [amount, setAmount] = useState('')
  const [paidAt, setPaidAt] = useState(todayStr())
  const [trackingCode, setTrackingCode] = useState('')
  const [saving, setSaving] = useState(false)

  const pickImage = (e) => {
    const f = e.target.files?.[0] || null
    setImage(f)
    setPreview(f ? URL.createObjectURL(f) : null)
  }

  const submit = async () => {
    if (!image) return toast.error('تصویر فیش واریزی الزامی است')
    if (!Number(amount) || Number(amount) <= 0) return toast.error('مبلغ واریز را وارد کنید')
    if (!paidAt) return toast.error('تاریخ واریز را وارد کنید')
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('image', image)
      fd.append('amount', String(Number(amount)))
      fd.append('paid_at', paidAt)
      if (trackingCode.trim()) fd.append('tracking_code', trackingCode.trim())
      await orderService.uploadReceipt(order.order_number, fd)
      toast.success('فیش واریزی ثبت شد و در انتظار بررسی است')
      qc.invalidateQueries(['my-receipts'])
      onDone?.()
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ثبت فیش واریزی')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-3 mb-2 space-y-3">
      <div className="text-xs font-medium text-white">ثبت فیش واریزی</div>

      <div>
        <label className="label text-xs mb-1 block">تصویر فیش *</label>
        <input type="file" accept="image/*" capture="environment" onChange={pickImage}
          className="block w-full text-xs text-gray-steel file:ml-3 file:rounded-lg file:border-0 file:bg-brand/15 file:text-brand file:px-3 file:py-2 file:text-xs hover:file:bg-brand/25" />
        <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
          عکس واضح و خوانا از فیش بگیرید — کادر عمودی (موبایل) مناسب است — حجم تا ۲ مگابایت.
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
          className="input text-sm font-mono" dir="ltr" placeholder="شماره پیگیری تراکنش" />
      </div>

      <button onClick={submit} disabled={saving}
        className="btn-primary w-full py-2.5 text-sm disabled:opacity-50">
        {saving ? 'در حال ارسال...' : '📤 ثبت فیش'}
      </button>
    </div>
  )
}

// ─── فیش‌های واریزی من (برای یک سفارش) ───────────────────────
function MyReceipts({ receipts }) {
  if (!receipts.length) return null

  return (
    <div className="rounded-lg bg-white/5 px-3 py-2.5 mb-2">
      <div className="text-xs text-gray-steel font-medium mb-2">فیش‌های من</div>
      <div className="space-y-2">
        {receipts.map(r => {
          const st = RECEIPT_STATUS[r.status] || { label: r.status, cls: 'bg-white/10 text-gray-300' }
          const img = mediaUrl(r.image_url || r.image)
          return (
            <div key={r.id} className="flex items-center gap-3 text-xs">
              {img && (
                <a href={img} target="_blank" rel="noreferrer">
                  <img src={img} alt="فیش" className="w-12 h-12 rounded-lg object-cover border border-white/10" />
                </a>
              )}
              <div className="flex-1 min-w-0">
                <div className="text-white font-medium">{formatPrice(r.amount)}</div>
                <div className="text-gray-steel mt-0.5">
                  {formatDate(r.paid_at)}
                  {r.tracking_code && <span className="font-mono" dir="ltr"> — {r.tracking_code}</span>}
                </div>
                {r.status === 'rejected' && r.reject_reason && (
                  <div className="text-red-400 mt-0.5">علت رد: {r.reject_reason}</div>
                )}
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap ${st.cls}`}>{st.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ProformaInvoice({ order, onClose }) {
  const { user } = useAuthStore()
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="p-8" dir="rtl" style={{fontFamily:'Arial,sans-serif',color:'#000'}}>
          {/* هدر */}
          <div style={{display:'flex',justifyContent:'space-between',marginBottom:24,borderBottom:'2px solid #0066FF',paddingBottom:16}}>
            <div>
              <div style={{fontSize:20,fontWeight:'bold',color:'#0066FF'}}>فروشگاه قطعات دوربین مداربسته</div>
              <div style={{fontSize:11,color:'#666',marginTop:4}}>cctvparts.ir</div>
            </div>
            <div style={{textAlign:'left'}}>
              <div style={{fontSize:15,fontWeight:'bold'}}>پیش‌فاکتور</div>
              <div style={{fontSize:11,color:'#666'}}>شماره: {order.order_number}</div>
              <div style={{fontSize:11,color:'#666'}}>تاریخ: {new Date(order.created_at).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}</div>
            </div>
          </div>

          {/* اطلاعات مشتری */}
          <div style={{background:'#f8f9fa',borderRadius:8,padding:16,marginBottom:20,fontSize:12}}>
            <div style={{fontWeight:'bold',marginBottom:8}}>اطلاعات خریدار</div>
            <div>نام: {user?.first_name} {user?.last_name}</div>
            <div>موبایل: {user?.phone}</div>
            {order.shipping_address && <div>آدرس: {order.shipping_address}</div>}
            {order.shipping_method && (
              <div>روش ارسال: {SHIPPING[order.shipping_method] || order.shipping_method}
                {order.freight_company && ` — ${order.freight_company}`}
              </div>
            )}
          </div>

          {/* جدول */}
          <table style={{width:'100%',borderCollapse:'collapse',marginBottom:20,fontSize:12}}>
            <thead>
              <tr style={{background:'#0066FF',color:'white'}}>
                <th style={{padding:'8px 12px',textAlign:'right'}}>ردیف</th>
                <th style={{padding:'8px 12px',textAlign:'right'}}>محصول</th>
                <th style={{padding:'8px 12px',textAlign:'center'}}>تعداد</th>
                <th style={{padding:'8px 12px',textAlign:'left'}}>قیمت واحد</th>
                <th style={{padding:'8px 12px',textAlign:'left'}}>جمع</th>
              </tr>
            </thead>
            <tbody>
              {order.items?.map((item, i) => (
                <tr key={item.id} style={{background: i%2===0?'#fff':'#f8f9fa'}}>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee'}}>{i+1}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee'}}>{item.variant_name || item.variant_sku}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee',textAlign:'center'}}>{item.quantity}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee',textAlign:'left'}}>{Number(item.unit_price||0).toLocaleString('fa-IR')}</td>
                  <td style={{padding:'8px 12px',borderBottom:'1px solid #eee',textAlign:'left',fontWeight:'bold'}}>{Number((item.unit_price||0)*item.quantity).toLocaleString('fa-IR')}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* جمع کل */}
          <div style={{display:'flex',justifyContent:'flex-end',marginBottom:16}}>
            <div style={{background:'#0066FF',color:'white',borderRadius:8,padding:'12px 24px',textAlign:'left'}}>
              <div style={{fontSize:11,opacity:0.8}}>جمع کل</div>
              <div style={{fontSize:18,fontWeight:'bold'}}>{Number(order.total_amount||0).toLocaleString('fa-IR')} ریال</div>
            </div>
          </div>

          {/* اطلاعات پرداخت */}
          {(order.status === 'paid' || order.paid_amount) && (
            <div style={{background:'#e8f5e9',borderRadius:8,padding:12,marginBottom:12,fontSize:12}}>
              <div style={{fontWeight:'bold',marginBottom:6,color:'#2e7d32'}}>✅ اطلاعات پرداخت</div>
              {order.paid_amount && <div>مبلغ پرداخت شده: {Number(order.paid_amount).toLocaleString('fa-IR')} ریال</div>}
              {order.payment_method && <div>روش پرداخت: {PAYMENT_METHOD[order.payment_method] || order.payment_method}</div>}
              {order.paid_at && <div>تاریخ پرداخت: {new Date(order.paid_at).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}</div>}
            </div>
          )}

          {/* اطلاعات ارسال */}
          {order.tracking_code && (
            <div style={{background:'#e3f2fd',borderRadius:8,padding:12,marginBottom:12,fontSize:12}}>
              <div style={{fontWeight:'bold',marginBottom:6,color:'#1565c0'}}>📦 اطلاعات ارسال</div>
              <div>کد رهگیری: <span style={{fontFamily:'monospace',fontSize:14}}>{order.tracking_code}</span></div>
              {order.shipping_method && <div>روش ارسال: {SHIPPING[order.shipping_method]}</div>}
            </div>
          )}

          <div style={{marginTop:16,fontSize:10,color:'#999',textAlign:'center',borderTop:'1px solid #eee',paddingTop:12}}>
            این پیش‌فاکتور به صورت الکترونیکی صادر شده — cctvparts.ir
          </div>
        </div>

        <div className="flex gap-3 p-4 border-t">
          <button onClick={() => window.print()}
            className="flex-1 bg-blue-600 text-white rounded-xl py-2.5 text-sm font-medium hover:bg-blue-700">
            🖨️ چاپ / دانلود PDF
          </button>
          <button onClick={onClose} className="px-6 border border-gray-200 rounded-xl text-sm hover:bg-gray-50">
            بستن
          </button>
        </div>
      </div>
    </div>
  )
}

const SETTLEMENT_TERMS = {
  cash:   'نقدی',
  credit: 'اعتباری · ۱۸ روزه',
  month1: 'اعتباری · ۳۰ روزه',
  month2: 'اعتباری · ۶۰ روزه',
}

export default function OrdersPage() {
  const [params] = useSearchParams()
  const newOrder = params.get('new')
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [receiptFormFor, setReceiptFormFor] = useState(null)
  const [payingFor, setPayingFor] = useState(null)

  // هدایت به درگاه به‌پرداخت ملت برای سفارش‌های خرید مستقیم در انتظار پرداخت
  const handleOnlinePay = async (order) => {
    setPayingFor(order.order_number)
    try {
      const res = await paymentService.requestPayment(order.order_number)
      window.location.href = res.redirect_url
    } catch (e) {
      toast.error(e?.response?.data?.error || 'خطا در اتصال به درگاه پرداخت')
      setPayingFor(null)
    }
  }

  const { data, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: orderService.getOrders,
  })

  const { data: receiptsData } = useQuery({
    queryKey: ['my-receipts'],
    queryFn: orderService.getMyReceipts,
  })

  if (isLoading) return <PageLoader />
  const orders = data?.results || data || []
  const allReceipts = receiptsData?.results || receiptsData || []

  return (
    <div className="container-main py-8 max-w-3xl">
      <Seo title="سفارش‌های من" noindex />
      {selectedOrder && <ProformaInvoice order={selectedOrder} onClose={() => setSelectedOrder(null)} />}

      <h1 className="font-display font-bold text-2xl text-white mb-6">سفارش‌های من</h1>

      {newOrder && (
        <div className="card p-4 bg-green-500/10 border border-green-500/20 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-2xl">✅</span>
            <div>
              <div className="font-bold text-green-400">سفارش ثبت شد!</div>
              <div className="text-sm text-gray-steel mt-1">شماره: <span className="font-mono text-white">{newOrder}</span></div>
              <div className="text-sm text-gray-steel">با شما تماس می‌گیریم و پرداخت را هماهنگ می‌کنیم.</div>
            </div>
          </div>
        </div>
      )}

      {orders.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-4">📦</div>
          <div className="text-gray-steel">هنوز سفارشی ثبت نکرده‌اید</div>
          <Link to="/products" className="btn-primary mt-4 inline-block">مشاهده محصولات</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map(order => {
            const st = STATUS[order.status] || {label: order.status, color:'#888', bg:'#f0f0f0'}
            // فیش واریزی فقط برای سفارش‌های نقدی — اعتباری‌ها سررسید دارند و فیش نمی‌خواهند
            const types = [...new Set((order.items || []).map(i => i.settlement_type).filter(Boolean))]
            const isCashOrder = types.length > 0 && types.every(t => t === 'cash')
            return (
              <div key={order.id} className="card p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <div className="font-mono text-sm text-white">{order.order_number}</div>
                      {types.length > 0 && (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${isCashOrder ? 'bg-green-500/15 text-green-400' : 'bg-amber-500/15 text-amber-400'}`}>
                          {isCashOrder ? 'نقدی' : 'اعتباری'}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-steel mt-0.5">{new Date(order.created_at).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}</div>
                  </div>
                  <span className="text-xs px-3 py-1 rounded-full font-medium"
                    style={{color:st.color, background:st.bg}}>{st.label}</span>
                </div>

                {/* آیتم‌ها */}
                <div className="divide-y divide-white/5 mb-3">
                  {order.items?.slice(0,3).map(item => (
                    <div key={item.id} className="py-2 flex items-center justify-between text-sm">
                      <span className="text-gray-300 truncate">
                        {item.variant_name || item.variant_sku}
                        {SETTLEMENT_TERMS[item.settlement_type] && (
                          <span className="block text-[10px] text-gray-steel mt-0.5">{SETTLEMENT_TERMS[item.settlement_type]}</span>
                        )}
                      </span>
                      <span className="text-gray-steel flex-shrink-0 mr-2">×{item.quantity}</span>
                    </div>
                  ))}
                  {order.items?.length > 3 && (
                    <div className="py-2 text-xs text-gray-steel">+{order.items.length-3} محصول دیگر</div>
                  )}
                </div>

                {/* اطلاعات پرداخت */}
                {(order.status === 'paid' || order.paid_amount) && (
                  <div className="bg-green-500/10 rounded-lg px-3 py-2 mb-2">
                    <div className="text-xs text-green-400 font-medium mb-1">✅ پرداخت شده</div>
                    {order.paid_amount && (
                      <div className="text-xs text-gray-steel">
                        مبلغ: {Number(order.paid_amount).toLocaleString('fa-IR')} ریال
                        {order.payment_method && ` — ${PAYMENT_METHOD[order.payment_method]}`}
                      </div>
                    )}
                  </div>
                )}

                {/* اطلاعات ارسال */}
                {order.shipping_method && (
                  <div className="bg-blue-500/10 rounded-lg px-3 py-2 mb-2">
                    <div className="text-xs text-blue-400 font-medium mb-1">
                      {SHIPPING[order.shipping_method] || order.shipping_method}
                      {order.freight_company && ` — ${order.freight_company}`}
                    </div>
                    {order.tracking_code && (
                      <div className="text-xs text-gray-steel">
                        کد رهگیری: <span className="font-mono text-green-400">{order.tracking_code}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* اطلاعات واریز + اقلام تسویه + فیش‌ها */}
                <SarrafCard order={order} />
                <SettlementLines order={order} />
                <MyReceipts receipts={allReceipts.filter(r => r.order_number === order.order_number)} />
                {order.status === 'awaiting_payment' && isCashOrder && receiptFormFor === order.order_number && (
                  <ReceiptForm order={order} onDone={() => setReceiptFormFor(null)} />
                )}

                <div className="flex items-center justify-between pt-3 border-t border-white/5">
                  <span className="font-bold text-brand dark:text-cyan text-sm">
                    {Number(order.total_amount||0).toLocaleString('fa-IR')} ریال
                  </span>
                  <div className="flex gap-2 flex-wrap">
                    {order.status === 'awaiting_payment' && order.order_type === 'direct_purchase' && !order.is_payment_expired && (
                      <button
                        onClick={() => handleOnlinePay(order)}
                        disabled={payingFor === order.order_number}
                        className="btn-gold text-xs px-4 py-2 disabled:opacity-50">
                        {payingFor === order.order_number ? 'در حال اتصال به بانک…' : '💳 پرداخت آنلاین'}
                      </button>
                    )}
                    {order.status === 'awaiting_payment' && isCashOrder && (
                      <button
                        onClick={() => setReceiptFormFor(receiptFormFor === order.order_number ? null : order.order_number)}
                        className="text-xs px-4 py-2 rounded-xl border border-amber-500/30 text-amber-400 hover:bg-amber-500/10 transition-colors">
                        🧾 ثبت فیش واریزی
                      </button>
                    )}
                    {order.tracking_code && (
                      <Link to={`/track/${order.order_number}`}
                        className="text-xs px-4 py-2 rounded-xl border border-green-500/30 text-green-400 hover:bg-green-500/10 transition-colors">
                        🚚 رهگیری
                      </Link>
                    )}
                    <button onClick={() => setSelectedOrder(order)}
                      className="text-xs px-4 py-2 rounded-xl border border-brand/30 text-brand dark:text-cyan hover:bg-brand/10 transition-colors">
                      📄 پیش‌فاکتور
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
