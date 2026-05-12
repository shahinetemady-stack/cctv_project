import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { orderService, paymentService } from '../services/orders'
import useCartStore from '../store/useCartStore'
import { PageLoader, EmptyState } from '../components/ui'
import { formatPrice } from '../utils/format'

function CartItem({ item, onRemove, onUpdate }) {
  const [qty, setQty] = useState(item.quantity)
  const [saving, setSaving] = useState(false)

  const handleQtyChange = async (newQty) => {
    setQty(newQty)
    setSaving(true)
    try { await onUpdate(item.variant, newQty) } finally { setSaving(false) }
  }

  return (
    <div className="card p-4 flex items-center gap-4">
      {/* تصویر */}
      <div className="w-16 h-16 rounded-xl bg-navy flex-shrink-0 overflow-hidden">
        {item.variant_detail?.product?.main_image ? (
          <img src={item.variant_detail.product.main_image.image} alt="" className="w-full h-full object-contain p-2" />
        ) : <div className="w-full h-full flex items-center justify-center text-xl">📷</div>}
      </div>

      {/* اطلاعات */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
          {item.variant_name || item.variant_detail?.product?.name}
        </div>
        <div className="text-xs text-gray-steel font-mono">{item.variant_sku}</div>
        <div className="text-sm font-bold text-brand dark:text-cyan mt-1">
          {formatPrice(item.unit_price || item.variant_detail?.final_price)}
        </div>
      </div>

      {/* تعداد */}
      <div className="flex items-center border border-gray-200 dark:border-white/10 rounded-xl overflow-hidden">
        <button onClick={() => handleQtyChange(Math.max(1, qty - 1))}
          disabled={qty === 1 || saving} className="px-2 py-1 hover:bg-brand/10 transition-colors">−</button>
        <span className="px-3 py-1 text-sm font-mono min-w-[2rem] text-center">
          {saving ? '...' : qty}
        </span>
        <button onClick={() => handleQtyChange(qty + 1)}
          disabled={saving} className="px-2 py-1 hover:bg-brand/10 transition-colors">+</button>
      </div>

      {/* جمع */}
      <div className="text-sm font-bold text-right min-w-[80px]">
        {formatPrice((item.unit_price || item.variant_detail?.final_price || 0) * qty)}
      </div>

      {/* حذف */}
      <button onClick={() => onRemove(item.variant)}
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
  const [checkingOut, setCheckingOut] = useState(false)
  const [address, setAddress] = useState("")
  const [shippingMethod, setShippingMethod] = useState("post")
  const [freightCompany, setFreightCompany] = useState("")

  const { data: cart, isLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: orderService.getCart,
    onSuccess: (data) => setCount(data?.items?.length || 0),
  })

  const remove = async (variantId) => {
    await orderService.removeFromCart(variantId)
    qc.invalidateQueries(['cart'])
  }

  const update = async (variantId, qty) => {
    await orderService.addToCart(variantId, qty)
    qc.invalidateQueries(['cart'])
  }

  const handleCheckout = async () => {
    setCheckingOut(true)
    try {
      const order = await orderService.checkout(address, shippingMethod, freightCompany)
      // درخواست لینک پرداخت
      try {
        const pay = await paymentService.requestPayment(order.order_number)
        if (pay.redirect_url) {
          window.location.href = pay.redirect_url
          return
        }
      } catch (payErr) {
        // درگاه هنوز فعال نشده - سفارش ثبت شد
      }
      navigate(`/account/orders?new=${order.order_number}`)
    } catch (e) {
      console.error(e)
      alert('خطا در ثبت سفارش. لطفاً دوباره تلاش کنید.')
    } finally {
      setCheckingOut(false)
    }
  }

  if (isLoading) return <PageLoader />

  const items = cart?.items || []

  return (
    <div className="container-main py-8 max-w-4xl">
      <h1 className="font-display font-bold text-2xl text-white mb-8">سبد خرید</h1>

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
              <div className="flex justify-between font-bold text-base border-t border-gray-100 dark:border-white/5 pt-3">
                <span>جمع کل</span>
                <span className="text-brand dark:text-cyan">{formatPrice(cart?.total_price)}</span>
              </div>
            </div>

            <div>
              <label className="label text-xs">روش ارسال</label>
              <div className="grid grid-cols-3 gap-2 mt-1">
                {[
                  {value: 'post', label: '📮 پست'},
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
              {checkingOut ? 'در حال ثبت سفارش...' : '✅ ثبت و پرداخت سفارش'}
            </button>

            <p className="text-[11px] text-gray-steel text-center">
              سفارش ثبت شده و برای پرداخت آماده می‌شود
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
