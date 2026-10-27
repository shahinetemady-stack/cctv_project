import { useState } from 'react'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { orderService, paymentService } from '../services/orders'
import useCartStore from '../store/useCartStore'
import useAuthStore from '../store/useAuthStore'
import { PageLoader, EmptyState } from '../components/ui'
import OverdueBanner from '../components/OverdueBanner'
import Seo from '../components/Seo'
import { formatPrice, formatNumber } from '../utils/format'

// سقف خرید مستقیم با پرداخت آنلاین (ریال) — هم‌راستا با DIRECT_PURCHASE_MAX_RIAL بک‌اند
const DIRECT_MAX_RIAL = 200_000_000

function CartItem({ item, onRemove, onUpdate }) {
  const [qty, setQty] = useState(item.quantity)
  const [saving, setSaving] = useState(false)
  const isPkg = !!item.is_package
  const minQty = isPkg ? (item.package_min_quantity || 1) : 1

  const handleQtyChange = async (newQty) => {
    setQty(newQty)
    setSaving(true)
    try { await onUpdate(item.variant, item.package, newQty) }
    catch { setQty(item.quantity) }
    finally { setSaving(false) }
  }

  return (
    <div className="card p-4 flex items-center gap-4">
      {/* تصویر */}
      <div className="w-16 h-16 rounded-xl bg-navy flex-shrink-0 overflow-hidden">
        {(item.package_image || item.variant_image) ? (
          <img src={item.package_image || item.variant_image} alt="" className="w-full h-full object-contain p-2" />
        ) : <div className="w-full h-full flex items-center justify-center text-xl">📷</div>}
      </div>

      {/* اطلاعات */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
          {isPkg ? (
            <Link to={`/packages/${item.package_slug}`} className="hover:text-brand transition-colors">
              {item.package_name}
            </Link>
          ) : item.variant_name}
        </div>
        {isPkg ? (
          <span className="inline-block mt-1 text-[10px] bg-brand/10 text-brand px-2 py-0.5 rounded-full">
            پکیج — {formatNumber(item.quantity)} بسته
          </span>
        ) : (
          <div className="text-xs text-gray-steel font-mono">{item.variant_sku}</div>
        )}
        {!isPkg && item.settlement_type !== 'cash' && (
          <span className="inline-block mt-1 text-[10px] bg-brand/10 text-brand px-2 py-0.5 rounded-full">
            {item.settlement_display}
          </span>
        )}
        <div className="text-sm font-bold text-brand dark:text-cyan mt-1">
          {formatPrice(item.unit_price || item.variant_detail?.pricing?.price || item.variant_detail?.final_price)}
        </div>
      </div>

      {/* تعداد */}
      <div className="flex items-center border border-gray-200 dark:border-white/10 rounded-xl overflow-hidden">
        <button onClick={() => handleQtyChange(Math.max(minQty, qty - 1))}
          disabled={qty <= minQty || saving} className="px-2 py-1 hover:bg-brand/10 transition-colors">−</button>
        <span className="px-3 py-1 text-sm font-mono min-w-[2rem] text-center">
          {saving ? '...' : qty}
        </span>
        <button onClick={() => handleQtyChange(qty + 1)}
          disabled={saving} className="px-2 py-1 hover:bg-brand/10 transition-colors">+</button>
      </div>

      {/* جمع */}
      <div className="text-sm font-bold text-right min-w-[80px]">
        {formatPrice((item.unit_price || item.variant_detail?.pricing?.price || item.variant_detail?.final_price || 0) * qty)}
      </div>

      {/* حذف */}
      <button onClick={() => onRemove(item.variant, item.package)}
        className="p-1.5 rounded-lg text-alert-red/50 hover:text-alert-red hover:bg-alert-red/10 transition-all">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

export default function CartPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { setCount } = useCartStore()
  const { isPartner } = useAuthStore()
  const [checkingOut, setCheckingOut] = useState(false)
  const [address, setAddress] = useState("")
  const [shippingMethod, setShippingMethod] = useState("courier")
  const [freightCompany, setFreightCompany] = useState("")

  const { data: cart, isLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: orderService.getCart,
    enabled: !isPartner(),
    onSuccess: (data) => setCount(data?.items?.length || 0),
  })

  const remove = async (variantId, packageId) => {
    if (packageId) await orderService.removePackageFromCart(packageId)
    else await orderService.removeFromCart(variantId)
    qc.invalidateQueries(['cart'])
  }

  const update = async (variantId, packageId, qty) => {
    try {
      if (packageId) await orderService.addPackageToCart(packageId, qty)
      else await orderService.addToCart(variantId, qty)
      qc.invalidateQueries(['cart'])
    } catch (e) {
      console.error(e)
      toast.error(e.response?.data?.error || 'خطا در بروزرسانی سبد. لطفاً دوباره تلاش کنید.')
      qc.invalidateQueries(['cart'])
      throw e
    }
  }

  const handleCheckout = async () => {
    setCheckingOut(true)
    try {
      const order = await orderService.checkout(address, shippingMethod, freightCompany)
      if (order.split && order.orders?.length > 1) {
        toast.info(
          `به دلیل تفاوت روند تسویه، سفارش شما به دو سفارش تقسیم شد: ${order.orders.map(o => o.order_number).join(' و ')}`,
          { duration: 6000 }
        )
      }
      if (order.overdue_warning?.count > 0) {
        toast.warning(
          `شما ${Number(order.overdue_warning.count).toLocaleString('fa-IR')} قلم تسویه معوقه به مبلغ ${formatPrice(order.overdue_warning.total)} دارید. سفارش شما در اولویت بررسی قرار می‌گیرد.`
        )
      }
      // سفارش بستانکارها همین‌جا از حسابشان تسویه شده — بدون درگاه
      if (order.status === 'paid') {
        toast.success('سفارش شما از بستانکاری حساب‌تان تسویه شد و نیازی به پرداخت نیست.', { duration: 6000 })
      }
      // سفارش نقدی تا سقف، همین‌جا تأیید شده — مستقیم به درگاه بانک
      if (order.status === 'awaiting_payment' && !order.split) {
        try {
          const res = await paymentService.requestPayment(order.order_number)
          window.location.href = res.redirect_url
          return
        } catch (payErr) {
          toast.error(payErr?.response?.data?.error || 'خطا در اتصال به درگاه — از صفحه سفارش‌ها دوباره تلاش کنید.')
        }
      }
      navigate(`/account/orders?new=${order.order_number}`)
    } catch (e) {
      console.error(e)
      toast.error(e.response?.data?.error || 'خطا در ثبت سفارش. لطفاً دوباره تلاش کنید.')
    } finally {
      setCheckingOut(false)
    }
  }

  // همکارها سبد استعلام دارند، نه سبد خرید عادی
  if (isPartner()) return <Navigate to="/inquiry-cart" replace />

  if (isLoading) return <PageLoader />

  const items = cart?.items || []
  const overCap = (cart?.total_price || 0) > DIRECT_MAX_RIAL

  return (
    <div className="container-main py-8 max-w-4xl">
      <Seo title="سبد خرید" noindex />
      <h1 className="font-display font-bold text-2xl text-white mb-8">سبد خرید</h1>

      <OverdueBanner />

      {items.length === 0 ? (
        <EmptyState icon="🛒" title="سبد خرید خالی است"
          action={<Link to="/products" className="btn-primary">مشاهده محصولات</Link>}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* لیست آیتم‌ها */}
          <div className="lg:col-span-2 space-y-3">
            {items.map(item => (
              <CartItem key={item.id} item={item}
                onRemove={remove} onUpdate={update} />
            ))}
          </div>

          {/* خلاصه سفارش */}
          <div className="card p-6 h-fit space-y-4 sticky top-24">
            <h2 className="font-bold text-base">خلاصه سفارش</h2>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-steel">تعداد آیتم</span>
                <span>{items.length.toLocaleString('fa-IR')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-steel">نحوه تسویه</span>
                <span>نقدی — پرداخت آنلاین</span>
              </div>
              <div className="flex justify-between font-bold text-base border-t border-gray-100 dark:border-white/5 pt-3">
                <span>جمع کل</span>
                <span className="text-brand dark:text-cyan">{formatPrice(cart?.total_price)}</span>
              </div>
            </div>

            {overCap ? (
              <div className="rounded-xl border border-gold/30 bg-gold/5 p-3 text-xs leading-6 text-gray-700 dark:text-gray-300">
                سقف خرید مستقیم با پرداخت آنلاین {formatPrice(DIRECT_MAX_RIAL)} است.
                برای خرید بیشتر با فروشگاه تماس بگیرید.
              </div>
            ) : (
              <>
            <div>
              <label className="label text-xs">روش ارسال</label>
              <div className="grid grid-cols-2 gap-2 mt-1">
                {[
                  {value: 'courier', label: '🛵 پیک'},
                  {value: 'freight', label: '🚛 باربری'},
                ].map(m => (
                  <button key={m.value} type="button"
                    onClick={() => setShippingMethod(m.value)}
                    className={`py-2 rounded-lg border text-xs transition-all
                      ${shippingMethod === m.value
                        ? 'border-brand bg-brand/10 text-brand dark:text-cyan'
                        : 'border-gray-200 dark:border-white/10 hover:border-brand/30'}`}>
                    {m.label}
                  </button>
                ))}
              </div>
              {shippingMethod === 'freight' && (
                <input
                  value={freightCompany}
                  onChange={e => setFreightCompany(e.target.value)}
                  placeholder="نام باربری (اختیاری)"
                  className="input text-sm mt-2"
                />
              )}
            </div>

            <div>
              <label className="label text-xs">آدرس تحویل (اختیاری)</label>
              <textarea
                value={address}
                onChange={e => setAddress(e.target.value)}
                rows={2}
                className="input text-sm resize-none"
                placeholder="آدرس کامل..."
              />
            </div>

            <button
              onClick={handleCheckout}
              disabled={checkingOut}
              className="btn-primary w-full py-3 text-base"
            >
              {checkingOut ? 'در حال ثبت سفارش...' : '✅ ثبت سفارش و پرداخت آنلاین'}
            </button>

            <p className="text-[11px] text-gray-steel text-center">
              بلافاصله بعد از ثبت سفارش به درگاه بانک ملت هدایت می‌شوید
            </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
