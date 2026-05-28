import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import api from '../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function imgUrl(url) {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `${import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000'}${url}`
}

export default function PackageDetailPage() {
  const { slug } = useParams()
  const { data: pkg, isLoading } = useQuery({
    queryKey: ['package-detail', slug],
    queryFn: () => api.get(`/catalog/packages/${slug}/`).then(r => r.data),
  })

  if (isLoading) return (
    <div className="container-main py-20 text-center text-gray-steel">در حال بارگذاری...</div>
  )
  if (!pkg) return (
    <div className="container-main py-20 text-center text-gray-steel">پکیج یافت نشد</div>
  )

  return (
    <div className="container-main py-12 max-w-4xl">
      <div className="mb-6">
        <Link to="/packages" className="text-sm text-gray-steel hover:text-white">← همه پکیج‌ها</Link>
      </div>

      <div className="grid grid-cols-5 gap-8">
        {/* اطلاعات پکیج */}
        <div className="col-span-3">
          {pkg.image && (
        <img src={imgUrl(pkg.image)} alt={pkg.name}
          className="w-full h-56 object-cover rounded-2xl mb-6 bg-white/5" />
      )}
      <h1 className="font-display font-bold text-2xl text-white mb-2">{pkg.name}</h1>
          {pkg.description && (
            <p className="text-gray-steel text-sm mb-6">{pkg.description}</p>
          )}

          <h2 className="font-semibold text-white mb-4">محصولات داخل پکیج:</h2>
          <div className="space-y-3">
            {pkg.items?.map((item, i) => (
              <div key={i} className="card p-4 flex items-center gap-4">
                {item.image && (
                  <img src={imgUrl(item.image)} alt={item.product_name}
                    className="w-16 h-16 object-contain rounded-lg bg-white/5 flex-shrink-0" />
                )}
                <div className="flex-1">
                  <Link to={`/products/${item.product_slug}`}
                    className="text-sm font-semibold text-white hover:text-brand transition-colors">
                    {item.product_name}
                  </Link>
                  <div className="text-xs text-gray-steel mt-1">
                    تعداد: {item.quantity} عدد | قیمت واحد: {fmt(item.unit_price)} ت
                  </div>
                  <div className={`text-xs mt-1 ${item.stock > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {item.stock > 0 ? `موجود (${item.stock} عدد)` : 'ناموجود'}
                  </div>
                </div>
                <div className="text-sm font-bold text-white">{fmt(item.subtotal)} ت</div>
              </div>
            ))}
          </div>
        </div>

        {/* قیمت و خرید */}
        <div className="col-span-2">
          <div className="card p-5 sticky top-24">
            <div className="text-center mb-4">
              <span className="text-2xl font-bold text-red-400 bg-red-500/10 px-4 py-1 rounded-full">
                {pkg.discount_percent}% تخفیف
              </span>
            </div>
            <div className="space-y-3 mb-5">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-steel">قیمت اصلی:</span>
                <span className="text-sm text-gray-steel line-through">{fmt(pkg.original_price)} ت</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-green-400">صرفه‌جویی:</span>
                <span className="text-sm text-green-400 font-bold">{fmt(pkg.savings)} ت</span>
              </div>
              <div className="flex items-center justify-between border-t border-white/10 pt-3">
                <span className="font-bold text-white">قیمت پکیج:</span>
                <span className="text-2xl font-bold text-brand">{fmt(pkg.final_price)} ت</span>
              </div>
            </div>
            <button className="btn-primary w-full py-3 text-sm font-semibold">
              افزودن پکیج به سبد خرید
            </button>
            <p className="text-xs text-gray-steel text-center mt-3">
              با خرید این پکیج {fmt(pkg.savings)} تومان صرفه‌جویی می‌کنید
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
