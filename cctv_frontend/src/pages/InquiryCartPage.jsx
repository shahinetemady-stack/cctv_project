import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { orderService } from '../services/orders'
import useCartStore from '../store/useCartStore'
import { PageLoader, EmptyState } from '../components/ui'

export default function InquiryCartPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { setInquiryCount } = useCartStore()
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const { data: cart, isLoading } = useQuery({
    queryKey: ['inquiry-cart'],
    queryFn: orderService.getInquiryCart,
    onSuccess: (d) => setInquiryCount(d?.items?.length || 0),
  })

  const handleRemove = async (variantId) => {
    await orderService.removeFromInquiryCart(variantId)
    qc.invalidateQueries(['inquiry-cart'])
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const order = await orderService.submitInquiry(notes)
      setSubmitted(true)
      qc.invalidateQueries(['inquiry-cart'])
      setTimeout(() => navigate(`/account/orders`), 2000)
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading) return <PageLoader />

  const items = cart?.items || []

  if (submitted) return (
    <div className="container-main py-20 text-center max-w-md">
      <div className="text-5xl mb-4">✅</div>
      <h2 className="font-display font-bold text-2xl text-white mb-3">استعلام ثبت شد</h2>
      <p className="text-gray-steel text-sm">
        کارشناس ما تا ۱۵ دقیقه دیگر با شما تماس می‌گیرد.
      </p>
    </div>
  )

  return (
    <div className="container-main py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="font-display font-bold text-2xl text-white">سبد استعلام</h1>
        <p className="text-sm text-gray-steel mt-1">
          پس از ثبت، کارشناس ظرف ۱۵ دقیقه قیمت نهایی را تأیید می‌کند
        </p>
      </div>

      {items.length === 0 ? (
        <EmptyState icon="📋" title="سبد استعلام خالی است"
          action={<Link to="/products" className="btn-primary">مشاهده محصولات</Link>}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* لیست */}
          <div className="lg:col-span-2 space-y-3">
            {items.map(item => (
              <div key={item.id} className="card p-4 flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-navy flex-shrink-0 flex items-center justify-center text-2xl">
                  📷
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">
                    {item.variant_detail?.product?.name || `محصول #${item.variant}`}
                  </div>
                  <div className="text-xs text-gray-steel mt-0.5">
                    تعداد: {item.quantity.toLocaleString('fa-IR')}
                  </div>
                  <div className="text-xs text-cyan mt-0.5 font-mono">
                    {item.variant_detail?.sku}
                  </div>
                </div>
                <button onClick={() => handleRemove(item.variant)}
                  className="p-1.5 rounded-lg text-alert-red/50 hover:text-alert-red hover:bg-alert-red/10 transition-all">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* ثبت استعلام */}
          <div className="card p-6 h-fit space-y-4 sticky top-24">
            <h2 className="font-bold text-base">ثبت استعلام</h2>

            <div>
              <label className="label">یادداشت (اختیاری)</label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={4}
                placeholder="توضیحات اضافی، موارد خاص..."
                className="input resize-none"
              />
            </div>

            <div className="bg-brand/5 border border-brand/20 rounded-xl p-3 text-xs text-gray-steel space-y-1">
              <div>🕐 تأیید ظرف ۱۵ دقیقه</div>
              <div>💰 قیمت نهایی توسط کارشناس</div>
              <div>⏳ رزرو موجودی ۲ ساعته</div>
            </div>

            <button onClick={handleSubmit} disabled={submitting || items.length === 0}
              className="btn-primary w-full py-3">
              {submitting ? '...' : '📤 ثبت استعلام'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
