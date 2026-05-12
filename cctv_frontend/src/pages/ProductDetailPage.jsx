import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../services/catalog'
import { orderService } from '../services/orders'
import useAuthStore from '../store/useAuthStore'
import useCartStore from '../store/useCartStore'
import { PageLoader, ErrorMessage } from '../components/ui'

function SpecsTable({ specs }) {
  if (!specs || specs.length === 0) return null
  return (
    <div className="card p-5">
      <h3 className="font-bold text-sm mb-4 text-white flex items-center gap-2">
        <span className="w-1 h-4 bg-brand rounded-full inline-block"></span>
        مشخصات فنی
      </h3>
      <div className="divide-y divide-gray-100 dark:divide-white/5">
        {specs.map((spec, i) => (
          <div key={i} className="flex items-center justify-between py-2.5">
            <span className="text-sm text-gray-steel">{spec.label}</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">{spec.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function VariantSelector({ variants, selected, onSelect }) {
  if (!variants || variants.length <= 1) return null
  return (
    <div>
      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">انتخاب نوع:</div>
      <div className="grid grid-cols-2 gap-2">
        {variants.map(v => (
          <button key={v.id} onClick={() => onSelect(v)}
            className={`p-3 rounded-xl border text-sm transition-all text-right
              ${selected?.id === v.id
                ? 'border-brand bg-brand/10 text-brand dark:text-cyan'
                : 'border-gray-200 dark:border-white/10 hover:border-brand/50'}`}>
            <div className="font-mono text-xs text-gray-steel">{v.sku}</div>
            {v.name_suffix && <div className="mt-1 font-medium">{v.name_suffix}</div>}
            <div className={`mt-1.5 font-bold font-mono text-sm
              ${v.is_in_stock ? 'text-brand dark:text-cyan' : 'text-gray-400 line-through'}`}>
              {v.is_in_stock ? Number(v.final_price).toLocaleString('fa-IR') + ' تومان' : 'ناموجود'}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ProductDetailPage() {
  const { slug } = useParams()
  const { isAuthenticated, isPartner } = useAuthStore()
  const { increment } = useCartStore()
  const [selectedVariant, setSelectedVariant] = useState(null)
  const [qty, setQty] = useState(1)
  const [adding, setAdding] = useState(false)
  const [added, setAdded] = useState(false)
  const [activeImage, setActiveImage] = useState(0)

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ['product', slug],
    queryFn: () => catalogService.getProduct(slug),
    onSuccess: (p) => { if (p.variants?.[0]) setSelectedVariant(p.variants[0]) },
  })

  if (isLoading) return <PageLoader />
  if (isError || !product) return (
    <div className="container-main py-20">
      <ErrorMessage message="محصول یافت نشد" />
    </div>
  )

  const variant = selectedVariant || product.variants?.[0]
  const inStock = variant?.is_in_stock && variant?.available_stock > 0
  const isUserPartner = isAuthenticated() && isPartner()

  const displayPrice = isUserPartner && variant?.partner_price
    ? variant.partner_price
    : variant?.final_price

  const handleAdd = async () => {
    if (!variant || !inStock) return
    setAdding(true)
    try {
      if (isPartner()) {
        await orderService.addToInquiryCart(variant.id, qty)
      } else {
        await orderService.addToCart(variant.id, qty)
      }
      increment()
      setAdded(true)
      setTimeout(() => setAdded(false), 2000)
    } catch (e) {
      console.error(e)
    } finally {
      setAdding(false)
    }
  }

  const images = product.images || []
  const specs  = product.specs || []

  return (
    <div className="container-main py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-gray-steel mb-8">
        <Link to="/" className="hover:text-brand transition-colors">خانه</Link>
        <span>/</span>
        <Link to="/products" className="hover:text-brand transition-colors">محصولات</Link>
        {product.category && (
          <>
            <span>/</span>
            <Link to={`/products?category=${product.category.id}`}
              className="hover:text-brand transition-colors">{product.category.name}</Link>
          </>
        )}
        <span>/</span>
        <span className="text-gray-900 dark:text-white truncate max-w-[200px]">{product.name}</span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* تصاویر */}
        <div className="space-y-3">
          <div className="card overflow-hidden aspect-square bg-gradient-to-br from-navy to-steel">
            {images[activeImage] ? (
              <img src={images[activeImage].image} alt={product.name}
                className="w-full h-full object-contain p-8" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-6xl">📷</div>
            )}
          </div>
          {images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto">
              {images.map((img, i) => (
                <button key={i} onClick={() => setActiveImage(i)}
                  className={`flex-shrink-0 w-16 h-16 rounded-lg border-2 overflow-hidden transition-all
                    ${activeImage === i ? 'border-brand' : 'border-transparent opacity-60 hover:opacity-100'}`}>
                  <img src={img.image} alt="" className="w-full h-full object-contain p-1" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* اطلاعات محصول */}
        <div className="space-y-5">
          <div>
            {product.brand && (
              <div className="text-xs font-mono text-brand dark:text-cyan mb-1 uppercase tracking-wider">
                {product.brand}
              </div>
            )}
            <h1 className="font-display font-bold text-2xl text-gray-900 dark:text-white leading-snug">
              {product.name}
            </h1>
            {product.model_number && (
              <div className="font-mono text-sm text-gray-steel mt-1">#{product.model_number}</div>
            )}
            {product.short_description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 leading-relaxed">
                {product.short_description}
              </p>
            )}
          </div>

          {/* قیمت */}
          {variant && (
            <div className="card p-4 bg-gradient-to-l from-brand/5 to-transparent">
              {variant.is_in_stock ? (
                <div>
                  {isUserPartner && variant.partner_price && variant.partner_discount_percent > 0 ? (
                    <>
                      <div className="text-xs text-gray-steel mb-1">قیمت همکار</div>
                      <div className="text-2xl font-display font-bold text-cyan">
                        {Number(variant.partner_price).toLocaleString('fa-IR')}
                        <span className="text-sm font-normal text-gray-steel mr-1">تومان</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-steel line-through">
                          {Number(variant.final_price).toLocaleString('fa-IR')} تومان
                        </span>
                        <span className="text-xs bg-alert-green/10 text-alert-green px-2 py-0.5 rounded-full">
                          {variant.partner_discount_percent}٪ تخفیف
                        </span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-xs text-gray-steel mb-1">
                        {isUserPartner ? 'قیمت همکار' : 'قیمت فروش'}
                      </div>
                      <div className="text-2xl font-display font-bold text-brand dark:text-cyan">
                        {Number(displayPrice).toLocaleString('fa-IR')}
                        <span className="text-sm font-normal text-gray-steel mr-1">تومان</span>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="text-alert-red font-medium">ناموجود</div>
              )}
            </div>
          )}

          <VariantSelector variants={product.variants} selected={selectedVariant} onSelect={setSelectedVariant} />

          {/* تعداد + افزودن */}
          {isAuthenticated() && (
            <div className="flex items-center gap-3">
              <div className="flex items-center border border-gray-200 dark:border-white/10 rounded-xl overflow-hidden">
                <button onClick={() => setQty(q => Math.max(1, q - 1))}
                  className="px-3 py-2 hover:bg-brand/10 transition-colors text-lg leading-none">−</button>
                <input
                  type="number" min="1" max={variant?.available_stock || 9999}
                  value={qty}
                  onChange={e => {
                    const v = parseInt(e.target.value) || 1
                    setQty(Math.min(Math.max(1, v), variant?.available_stock || 9999))
                  }}
                  className="w-20 py-2 text-sm font-mono text-center bg-transparent border-x border-gray-200 dark:border-white/10 focus:outline-none"
                  dir="ltr"
                />
                <button onClick={() => setQty(q => Math.min(variant?.available_stock || 9999, q + 1))}
                  className="px-3 py-2 hover:bg-brand/10 transition-colors text-lg leading-none">+</button>
              </div>

              <button onClick={handleAdd} disabled={adding || !inStock}
                className={`flex-1 py-3 rounded-xl font-medium text-sm transition-all
                  ${added ? 'bg-alert-green text-white'
                    : inStock ? 'bg-brand text-white hover:bg-brand-light shadow-sm'
                    : 'bg-gray-200 dark:bg-white/5 text-gray-400 cursor-not-allowed'}`}>
                {adding ? '...' : added ? '✓ اضافه شد!'
                  : !inStock ? 'ناموجود'
                  : isPartner() ? '+ افزودن به سبد استعلام'
                  : '+ افزودن به سبد خرید'}
              </button>
            </div>
          )}

          {!isAuthenticated() && (
            <Link to="/auth/login"
              className="flex items-center justify-center py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-light transition-colors">
              برای خرید وارد شوید
            </Link>
          )}

          {/* دیتاشیت */}
          {product.has_datasheet && product.datasheet_pdf && (
            <a href={product.datasheet_pdf} target="_blank" rel="noreferrer"
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl
                bg-brand/10 text-brand dark:text-cyan border border-brand/20
                hover:bg-brand/20 transition-colors text-sm font-medium">
              📄 دانلود دیتاشیت
            </a>
          )}
        </div>
      </div>

      {specs.length > 0 && (
        <div className="mt-10"><SpecsTable specs={specs} /></div>
      )}

      {product.description && (
        <section className="mt-8">
          <h2 className="font-display font-bold text-xl text-white mb-4">توضیحات</h2>
          <div className="card p-6 text-sm text-gray-700 dark:text-gray-300 leading-loose whitespace-pre-line">
            {product.description}
          </div>
        </section>
      )}

      {product.compatible_with?.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display font-bold text-xl text-white mb-4">محصولات سازگار</h2>
          <div className="flex flex-wrap gap-2">
            {product.compatible_with.map(p => (
              <Link key={p.id} to={`/products/${p.slug}`}
                className="px-4 py-2 rounded-xl border border-brand/20 bg-brand/5
                  text-brand dark:text-cyan text-sm hover:bg-brand/10 transition-colors">
                {p.name}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}