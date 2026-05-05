import { useSearchParams, Link } from 'react-router-dom'

export default function PaymentResultPage({ success }) {
  const [params] = useSearchParams()
  const orderNum = params.get('order')
  const ref = params.get('ref')
  const error = params.get('error')

  if (success) return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <div className="text-center max-w-sm">
        <div className="w-20 h-20 bg-alert-green/10 rounded-full flex items-center justify-center
          mx-auto mb-6 text-4xl">✅</div>
        <h1 className="font-display font-bold text-2xl text-white mb-3">پرداخت موفق</h1>
        <p className="text-gray-steel text-sm mb-2">سفارش شما با موفقیت ثبت شد</p>
        {orderNum && <p className="font-mono text-xs text-brand mb-1">سفارش: {orderNum}</p>}
        {ref && <p className="font-mono text-xs text-gray-steel">پیگیری: {ref}</p>}
        <div className="flex gap-3 justify-center mt-8">
          <Link to="/account/orders" className="btn-primary">مشاهده سفارش‌ها</Link>
          <Link to="/" className="btn-ghost">بازگشت به خانه</Link>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <div className="text-center max-w-sm">
        <div className="w-20 h-20 bg-alert-red/10 rounded-full flex items-center justify-center
          mx-auto mb-6 text-4xl">❌</div>
        <h1 className="font-display font-bold text-2xl text-white mb-3">پرداخت ناموفق</h1>
        <p className="text-gray-steel text-sm mb-2">{error || 'مشکلی در پرداخت رخ داد'}</p>
        {orderNum && <p className="font-mono text-xs text-brand">سفارش: {orderNum}</p>}
        <div className="flex gap-3 justify-center mt-8">
          <Link to={`/account/orders`} className="btn-primary">تلاش مجدد</Link>
          <Link to="/" className="btn-ghost">بازگشت</Link>
        </div>
      </div>
    </div>
  )
}
