import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import useCompareStore from '../store/useCompareStore'
import useAuthStore from '../store/useAuthStore'
import useCartStore from '../store/useCartStore'
import { orderService } from '../services/orders'
import { PageLoader, ErrorMessage, EmptyState } from '../components/ui'
import Seo from '../components/Seo'
import { useState } from 'react'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function ComparePage() {
  const { items, remove, clear } = useCompareStore()
  const { isAuthenticated, isPartner } = useAuthStore()
  const { increment } = useCartStore()
  const [addingSlug, setAddingSlug] = useState(null)
  const [searchParams] = useSearchParams()

  // ?slugs=a,b,c — لینک قابل اشتراک مقایسه (بدون نیاز به استور)
  const urlSlugs = (searchParams.get('slugs') || '').split(',').filter(Boolean)
  const sharedMode = urlSlugs.length >= 2
  const slugs = sharedMode ? urlSlugs : items.map(i => i.slug)
  const { data: products, isLoading, isError } = useQuery({
    queryKey: ['compare', slugs],
    queryFn: () => api.get('/catalog/products/compare/', { params: { slugs: slugs.join(',') } }).then(r => r.data),
    enabled: slugs.length >= 2,
  })

  const handleAddToCart = async (product) => {
    const variant = product.variants?.[0]
    if (!variant) return
    setAddingSlug(product.slug)
    try {
      if (isPartner()) {
        const tier = useAuthStore.getState().user?.profile?.partner_tier
        await orderService.addToInquiryCart(variant.id, 1, tier === 'silver' ? 'month1' : 'credit')
      } else {
        await orderService.addToCart(variant.id)
      }
      increment()
    } catch (e) {
      console.error(e)
    } finally {
      setAddingSlug(null)
    }
  }

  if (slugs.length === 0) {
    return (
      <div className="container-main py-10">
        <Seo title="مقایسه محصولات" />
        <EmptyState
          icon="⚖"
          title="محصولی برای مقایسه انتخاب نشده"
          description="از صفحه دسته‌بندی یا صفحه محصول، با دکمه ⚖ بین ۲ تا ۴ محصول هم‌دسته را به مقایسه اضافه کنید."
          action={<Link to="/products" className="btn-primary text-sm px-6 py-2">مشاهده محصولات</Link>}
        />
      </div>
    )
  }

  // فقط ۱ محصول انتخاب شده — نمایش همان + راهنمای قدم بعد
  if (slugs.length === 1 && !sharedMode) {
    const it = items[0]
    return (
      <div className="container-main py-10 max-w-2xl">
        <Seo title="مقایسه محصولات" />
        <h1 className="font-display font-bold text-2xl text-white mb-6">⚖ مقایسه محصولات</h1>
        <div className="card p-5">
          <div className="text-sm text-gray-steel mb-4">محصول انتخاب‌شده برای مقایسه (۱ از حداکثر ۴):</div>
          <div className="flex items-center gap-4 bg-white/5 rounded-xl p-4">
            {it.image ? (
              <img src={it.image} alt={it.name} className="w-16 h-16 object-contain rounded-lg" />
            ) : (
              <div className="w-16 h-16 flex items-center justify-center text-3xl text-gray-steel">📦</div>
            )}
            <div className="flex-1">
              <Link to={`/products/${it.slug}`} className="text-sm font-semibold text-white hover:text-brand transition-colors">
                {it.name}
              </Link>
              {it.min_price && (
                <div className="text-xs text-brand dark:text-cyan font-mono mt-1">{fmt(it.min_price)} ریال</div>
              )}
            </div>
            <button onClick={() => remove(it.slug)}
              className="text-xs text-gray-steel hover:text-red-400 transition-colors">✕ حذف</button>
          </div>

          <div className="mt-6 p-4 rounded-xl border border-brand/30 bg-brand/5 text-center">
            <div className="text-sm text-white mb-1">برای شروع مقایسه، حداقل یک محصول دیگر از همین دسته لازم است</div>
            <div className="text-xs text-gray-steel mb-4">روی دکمه ⚖ کنار محصول بعدی بزنید تا اینجا کنار هم نمایش داده شوند</div>
            <Link to={`/products?category=${it.category_id}`} className="btn-primary text-sm px-6 py-2 inline-block">
              ⚖ انتخاب محصول بعدی از همین دسته
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) return <PageLoader />
  if (isError) return <div className="container-main py-20"><ErrorMessage message="خطا در بارگذاری مقایسه" retry={() => location.reload()} /></div>

  // اجتماع برچسب‌های مشخصات به ترتیب ظاهرشدن
  const labels = []
  for (const p of products) {
    for (const s of p.specs || []) {
      if (!labels.includes(s.label)) labels.push(s.label)
    }
  }
  const specOf = (p, label) => (p.specs || []).find(s => s.label === label)?.value || '—'

  const th = { padding: '10px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }
  const td = { padding: '12px', verticalAlign: 'top' }

  return (
    <div className="container-main py-8 max-w-6xl">
      <Seo title="مقایسه محصولات" />
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">⚖ مقایسه محصولات</h1>
        {!sharedMode && (
          <button onClick={clear} className="text-xs text-gray-steel hover:text-red-400 transition-colors">
            🗑 پاک کردن همه
          </button>
        )}
      </div>

      <div className="card overflow-x-auto">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 640 }}>
          <tbody>
            {/* تصویر + نام */}
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <td style={{ ...td, ...th }}>محصول</td>
              {products.map(p => {
                const img = p.images?.find(i => i.is_primary)?.image || p.images?.[0]?.image
                return (
                  <td key={p.slug} style={{ ...td, minWidth: 180 }}>
                    <Link to={`/products/${p.slug}`} className="block group">
                      {img ? (
                        <img src={img} alt={p.name} className="w-28 h-28 object-contain mx-auto group-hover:scale-105 transition-transform" />
                      ) : (
                        <div className="w-28 h-28 flex items-center justify-center text-4xl text-gray-steel mx-auto">📦</div>
                      )}
                      <div className="text-center text-sm font-semibold text-white mt-2 group-hover:text-brand transition-colors leading-snug">
                        {p.name}
                      </div>
                      {p.model_number && (
                        <div dir="ltr" className="text-center text-xs font-mono text-gray-steel mt-1">{p.model_number}</div>
                      )}
                    </Link>
                    <div className="text-center mt-2">
                      {!sharedMode && (
                        <button onClick={() => remove(p.slug)}
                          className="text-[10px] text-gray-steel hover:text-red-400 transition-colors">
                          ✕ حذف
                        </button>
                      )}
                    </div>
                  </td>
                )
              })}
            </tr>

            {/* قیمت */}
            <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: 'rgba(255,255,255,0.02)' }}>
              <td style={{ ...td, ...th }}>قیمت</td>
              {products.map(p => {
                const price = p.variants?.[0]?.pricing?.price ?? p.variants?.[0]?.final_price
                return (
                  <td key={p.slug} style={{ ...td, textAlign: 'center' }}>
                    {price ? (
                      <span className="font-bold text-brand dark:text-cyan font-mono">
                        {fmt(price)} <span className="text-[10px] font-normal text-gray-steel">ریال</span>
                      </span>
                    ) : '—'}
                  </td>
                )
              })}
            </tr>

            {/* موجودی */}
            <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)' }}>
              <td style={{ ...td, ...th }}>موجودی</td>
              {products.map(p => {
                const stock = p.variants?.[0]?.available_stock ?? 0
                return (
                  <td key={p.slug} style={{ ...td, textAlign: 'center' }}>
                    {stock > 0
                      ? <span className="badge-green text-[10px]">موجود ({fmt(stock)})</span>
                      : <span className="badge-red text-[10px]">ناموجود</span>}
                  </td>
                )
              })}
            </tr>

            {/* سبد خرید */}
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)' }}>
              <td style={{ ...td, ...th }}>خرید</td>
              {products.map(p => {
                const stock = p.variants?.[0]?.available_stock ?? 0
                return (
                  <td key={p.slug} style={{ ...td, textAlign: 'center' }}>
                    {isAuthenticated() && stock > 0 && (
                      <button onClick={() => handleAddToCart(p)} disabled={addingSlug === p.slug}
                        className="btn-secondary text-xs px-4 py-1.5">
                        {addingSlug === p.slug ? '...' : '+ سبد'}
                      </button>
                    )}
                  </td>
                )
              })}
            </tr>

            {/* مشخصات فنی */}
            {labels.map((label, li) => (
              <tr key={label} style={{
                borderBottom: '0.5px solid rgba(255,255,255,0.05)',
                background: li % 2 ? 'rgba(255,255,255,0.02)' : 'transparent',
              }}>
                <td style={{ ...td, ...th }}>{label}</td>
                {products.map(p => (
                  <td key={p.slug} style={{ ...td, textAlign: 'center', color: 'var(--color-text-primary)', fontSize: 12 }}>
                    {specOf(p, label)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
