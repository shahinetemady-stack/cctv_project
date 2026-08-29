import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import api from '../services/api'
import { orderService } from '../services/orders'
import useCartStore from '../store/useCartStore'
import { mediaUrl as imgUrl } from '../utils/media'
import { formatPrice, formatNumber } from '../utils/format'
import Seo from '../components/Seo'

export default function PackageDetailPage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { increment } = useCartStore()
  const { data: pkg, isLoading } = useQuery({
    queryKey: ['package-detail', slug],
    queryFn: () => api.get(`/catalog/packages/${slug}/`).then(r => r.data),
  })

  const minQty = pkg?.min_quantity || 1
  const [qty, setQty] = useState(0) // 0 یعنی هنوز مقداردهی نشده — بعد از لود با minQty پر می‌شود
  const [adding, setAdding] = useState(false)
  const [added, setAdded] = useState(false)

  const bundles = qty || minQty

  const handleAdd = async () => {
    setAdding(true)
    try {
      await orderService.addPackageToCart(pkg.id, bundles)
      increment()
      setAdded(true)
      setTimeout(() => setAdded(false), 2000)
    } catch (e) {
      if (e.response?.status === 401) {
        toast.info('برای خرید ابتدا وارد حساب کاربری شوید')
        navigate('/login')
      } else {
        toast.error(e.response?.data?.error || 'خطا در افزودن به سبد خرید')
      }
    } finally {
      setAdding(false)
    }
  }

  if (isLoading) return (
    <div className="container-main py-20 text-center text-gray-steel">در حال بارگذاری...</div>
  )
  if (!pkg) return (
    <div className="container-main py-20 text-center text-gray-steel">پکیج یافت نشد</div>
  )

  // ─── SEO/GEO — همان الگوی ProductDetailPage ─────────────────
  const seoTitle = pkg.meta_title || `${pkg.name} | دوربینکار`
  const seoDescription = pkg.meta_description || pkg.description?.slice(0, 160)

  return (
    <div className="container-main py-12 max-w-4xl">
      <Seo
        title={seoTitle}
        description={seoDescription}
        keywords={pkg.keywords}
        canonical={`/packages/${pkg.slug}`}
        image={pkg.image}
        geoTags={pkg.geo_tags}
      />
      <div className="mb-6">
        <Link to="/packages" className="text-sm text-gray-steel hover:text-white">← همه پکیج‌ها</Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 lg:gap-8">
        {/* اطلاعات پکیج */}
        <div className="lg:col-span-3">
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
                    تعداد: {formatNumber(item.quantity)} عدد | قیمت واحد: {formatPrice(item.unit_price)}
                  </div>
                </div>
                <div className="text-sm font-bold text-white">{formatPrice(item.subtotal)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* قیمت و خرید */}
        <div className="lg:col-span-2">
          <div className="card p-5 sticky top-24">
            <div className="text-center mb-4">
              <span className="text-2xl font-bold text-red-400 bg-red-500/10 px-4 py-1 rounded-full">
                {pkg.discount_percent}% تخفیف
              </span>
            </div>
            <div className="space-y-3 mb-5">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-steel">قیمت اصلی:</span>
                <span className="text-sm text-gray-steel line-through">{formatPrice(pkg.original_price)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-green-400">صرفه‌جویی:</span>
                <span className="text-sm text-green-400 font-bold">{formatPrice(pkg.savings)}</span>
              </div>
              <div className="flex items-center justify-between border-t border-white/10 pt-3">
                <span className="font-bold text-white">قیمت پکیج:</span>
                <span className="text-2xl font-bold text-brand">{formatPrice(pkg.final_price)}</span>
              </div>
              {pkg.min_quantity > 1 && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-steel">حداقل تعداد سفارش:</span>
                  <span className="text-sm font-bold text-amber-400">{formatNumber(pkg.min_quantity)} بسته</span>
                </div>
              )}
            </div>

            {/* انتخاب تعداد بسته */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-steel">تعداد بسته:</span>
              <div className="flex items-center border border-white/10 rounded-xl overflow-hidden">
                <button onClick={() => setQty(Math.max(minQty, bundles - 1))}
                  disabled={bundles <= minQty}
                  className="px-3 py-1.5 hover:bg-brand/10 transition-colors disabled:opacity-40">−</button>
                <span className="px-4 py-1.5 text-sm font-mono min-w-[2.5rem] text-center">{formatNumber(bundles)}</span>
                <button onClick={() => setQty(bundles + 1)}
                  className="px-3 py-1.5 hover:bg-brand/10 transition-colors">+</button>
              </div>
            </div>

            <button onClick={handleAdd} disabled={adding}
              className="btn-primary w-full py-3 text-sm font-semibold disabled:opacity-50">
              {adding ? 'در حال افزودن...' : added ? '✓ به سبد اضافه شد' : 'افزودن پکیج به سبد خرید'}
            </button>
            <p className="text-xs text-gray-steel text-center mt-3">
              با خرید این پکیج {formatPrice(pkg.savings)} صرفه‌جویی می‌کنید
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
