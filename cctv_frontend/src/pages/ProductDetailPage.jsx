import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { catalogService } from '../services/catalog'
import api from '../services/api'
import { orderService } from '../services/orders'
import useAuthStore from '../store/useAuthStore'
import useCartStore from '../store/useCartStore'
import useCompareStore from '../store/useCompareStore'
import { ProductPackages } from '../components/PackageComponents'
import { PageLoader, ErrorMessage } from '../components/ui'
import Seo, { absoluteUrl } from '../components/Seo'
import { formatDate } from '../utils/date'
import { mediaUrl } from '../utils/media'

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
            <div className={`mt-1.5 font-bold text-sm
              ${v.is_in_stock ? 'text-brand dark:text-cyan' : 'text-gray-400 line-through'}`}>
              {v.is_in_stock ? Number(v.pricing?.price ?? v.final_price).toLocaleString('fa-IR') + ' ریال' : 'ناموجود'}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}



// ─── نمودار تغییر قیمت (۹۰ روزه) ─────────────────────────────
function PriceChart({ slug, variantId }) {
  const [hover, setHover] = useState(null) // ایندکس نقطه زیر نشانگر
  const svgRef = useRef(null)
  const { data: history = [] } = useQuery({
    queryKey: ['price-history', slug, variantId],
    queryFn: () => api.get(`/catalog/products/${slug}/price-history/`, {
      params: variantId ? { variant: variantId } : {},
    }).then(r => r.data),
    staleTime: 3600000,
  })

  if (history.length < 2) return null

  const prices = history.map(h => h.price)
  const times = history.map(h => new Date(h.date).getTime())
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const W = 500, H = 170, PL = 42, PR = 12, PT = 12, PB = 26

  // موقعیت X بر اساس تاریخ واقعی هر نقطه (نه فاصله مساوی)
  const t0 = times[0], span = (times[times.length - 1] - t0) || 1
  const points = prices.map((p, i) => [
    PL + ((times[i] - t0) / span) * (W - PL - PR),
    PT + (1 - (p - min) / range) * (H - PT - PB),
  ])

  // خطوط راهنمای محور عمودی (۴ سطح قیمت)
  const ticks = [0, 1 / 3, 2 / 3, 1].map(t => ({
    y: PT + t * (H - PT - PB),
    v: max - t * range,
  }))
  const fmtAxis = v => v >= 1e6
    ? (v / 1e6).toLocaleString('fa-IR', { maximumFractionDigits: 1 }) + ' م'
    : v.toLocaleString('fa-IR')

  const polyline = points.map(p => p.join(',')).join(' ')
  const latest = prices[prices.length - 1]
  const prev = prices[prices.length - 2]
  const change = ((latest - prev) / prev * 100).toFixed(1)
  const isUp = latest >= prev

  const handleMove = (e) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const x = (e.clientX - rect.left) * (W / rect.width)
    let best = 0, bd = Infinity
    points.forEach((p, i) => { const d = Math.abs(p[0] - x); if (d < bd) { bd = d; best = i } })
    setHover(best)
  }

  const labelIdx = [...new Set([0, Math.floor(times.length / 2), times.length - 1])]
  const lastPoint = points[points.length - 1]

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display font-bold text-xl text-white">📈 تغییر قیمت سه‌ماهه</h2>
        <span className={`text-sm font-bold px-3 py-1 rounded-full ${isUp ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
          {isUp ? '▲' : '▼'} {Math.abs(change)}%
        </span>
      </div>
      <div className="card p-4 relative">
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 180 }}
          onPointerMove={handleMove} onPointerLeave={() => setHover(null)}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FF7A1A" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#FF7A1A" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* خطوط راهنمای افقی + برچسب قیمت روی محور عمودی */}
          {ticks.map((t, i) => (
            <g key={i}>
              <line x1={PL} x2={W - PR} y1={t.y} y2={t.y}
                stroke="var(--color-border)" strokeWidth="1"
                strokeDasharray={i === 0 ? '' : '3 4'} opacity="0.6" />
              <text x={PL - 6} y={t.y + 3} textAnchor="end"
                fill="var(--color-text-secondary)" fontSize="9">{fmtAxis(t.v)}</text>
            </g>
          ))}
          {/* سایه گرادیان زیر نمودار */}
          <polygon
            points={`${points[0][0]},${H - PB} ${polyline} ${lastPoint[0]},${H - PB}`}
            fill="url(#priceGrad)" />
          {/* خط نمودار */}
          <polyline points={polyline}
            fill="none" stroke="#FF7A1A" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" />
          {/* خط عمودی نمایش لحظه + نقطه هاور */}
          {hover != null ? (
            <g>
              <line x1={points[hover][0]} x2={points[hover][0]} y1={PT} y2={H - PB}
                stroke="#9ca3af" strokeWidth="1" strokeDasharray="4 4" />
              <circle cx={points[hover][0]} cy={points[hover][1]}
                r="4.5" fill="#FF7A1A" stroke="#0b0f19" strokeWidth="2" />
            </g>
          ) : (
            <circle cx={lastPoint[0]} cy={lastPoint[1]} r="4" fill="#FF7A1A" />
          )}
          {/* برچسب‌های تاریخ شمسی */}
          {labelIdx.map(i => (
            <text key={i} x={points[i][0]} y={H - 8}
              textAnchor="middle" fill="var(--color-text-secondary)" fontSize="9">
              {formatDate(history[i].date, { short: true })}
            </text>
          ))}
        </svg>
        {/* تول‌تیپ قیمت لحظه‌ای */}
        {hover != null && (
          <div className="absolute pointer-events-none bg-gray-900 border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl z-10"
            style={{
              left: `${(points[hover][0] / W) * 100}%`,
              top: 0,
              transform: `translate(${points[hover][0] > W / 2 ? '-110%' : '15%'}, 8px)`,
            }}>
            <div className="text-gray-steel mb-0.5">{formatDate(history[hover].date)}</div>
            <div className="font-bold text-orange-400 whitespace-nowrap">
              {prices[hover].toLocaleString('fa-IR')} ریال
            </div>
          </div>
        )}
        <div className="flex justify-between text-xs text-gray-steel mt-1">
          <span>کمترین: {min.toLocaleString('fa-IR')} ریال</span>
          <span>بیشترین: {max.toLocaleString('fa-IR')} ریال</span>
        </div>
      </div>
    </section>
  )
}

// ─── ناوبری محصول قبلی/بعدی + بازگشت به لیست ──────────────────
function ProductNav({ slug }) {
  const navigate = useNavigate()
  const { data } = useQuery({
    queryKey: ['product-neighbors', slug],
    queryFn: () => api.get(`/catalog/products/${slug}/neighbors/`).then(r => r.data),
    staleTime: 60000,
  })
  const btnCls = "text-xs px-3 py-1.5 rounded-lg border border-white/10 text-gray-steel hover:text-white hover:border-brand/40 transition-colors max-w-[160px] truncate"
  const backCls = "text-xs px-3 py-1.5 rounded-lg border border-white/10 text-gray-steel hover:text-white hover:border-brand/40 transition-colors whitespace-nowrap"
  return (
    <div className="flex items-center gap-2 shrink-0">
      <button onClick={() => navigate(-1)} className={backCls} title="بازگشت به لیست محصولات">
        → بازگشت به لیست محصولات
      </button>
      {data?.prev && (
        <Link to={`/products/${data.prev.slug}`} className={btnCls} title={data.prev.name}>
          → قبلی
        </Link>
      )}
      {data?.next && (
        <Link to={`/products/${data.next.slug}`} className={btnCls} title={data.next.name}>
          بعدی ←
        </Link>
      )}
    </div>
  )
}

// ─── جایگزین‌های پیشنهادی ────────────────────────────────────
function SimilarProducts({ slug }) {
  const { data } = useQuery({
    queryKey: ['similar-products', slug],
    queryFn: () => api.get(`/catalog/products/${slug}/similar/`).then(r => r.data),
    staleTime: 60000,
  })

  if (!data?.similar?.length) return null

  return (
    <section className="mt-8">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="font-display font-bold text-xl text-white">
          {data.is_out_of_stock ? '🔄 جایگزین‌های پیشنهادی' : '📦 محصولات مشابه'}
        </h2>
        {data.is_out_of_stock && (
          <span className="text-xs bg-red-500/20 text-red-400 px-3 py-1 rounded-full">
            کالا ناموجود است
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4">
        {data.similar.map(p => (
          <Link key={p.id} to={`/products/${p.slug}`}
            className="card p-4 hover:border-brand/30 transition-all group">
            {p.image && (
              <img src={p.image} alt={p.name}
                className="w-full h-32 object-contain mb-3 rounded-lg bg-white/5" />
            )}
            <div className="text-sm font-semibold text-white group-hover:text-brand transition-colors truncate">
              {p.name}
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                p.is_available ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {p.is_available ? `موجود (${p.stock} عدد)` : 'ناموجود'}
              </span>
              {p.category && (
                <span className="text-[10px] text-gray-steel">{p.category}</span>
              )}
            </div>
            {p.sensor_name && (
              <div className="text-[10px] text-gray-steel mt-1">سنسور: {p.sensor_name}</div>
            )}
          </Link>
        ))}
      </div>
    </section>
  )
}

export default function ProductDetailPage() {
  const { slug } = useParams()
  const qc = useQueryClient()
  const { isAuthenticated, isPartner } = useAuthStore()
  const { increment } = useCartStore()
  const { add: addToCompare, remove: removeFromCompare, has: inCompare } = useCompareStore()
  const [selectedVariant, setSelectedVariant] = useState(null)
  const [qty, setQty] = useState(1)
  const [adding, setAdding] = useState(false)
  const [added, setAdded] = useState(false)
  const [activeImage, setActiveImage] = useState(0)
  const [payOption, setPayOption] = useState('credit') // گزینه پرداخت همکار پلاتینیوم
  const [qtyText, setQtyText] = useState(null) // متن خام اینپوت تعداد هنگام تایپ (null = نمایش qty)

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ['product', slug],
    queryFn: () => catalogService.getProduct(slug),
    onSuccess: (p) => { if (p.variants?.[0]) setSelectedVariant(p.variants[0]) },
  })

  // لیست دسته‌ها برای resolve کردن نام والد دسته‌ی محصول در breadcrumb
  const { data: categoriesData } = useQuery({
    queryKey: ['seo-categories'],
    queryFn: catalogService.getCategories,
    staleTime: 600000,
  })

  // اگر API به‌خاطر اسلاگ قدیمی ۳۰۱ شده، آدرس مرورگر را با اسلاگ جدید جایگزین کن
  const navigate = useNavigate()
  useEffect(() => {
    if (product?.slug && product.slug !== slug) {
      navigate(`/products/${product.slug}`, { replace: true })
    }
  }, [product?.slug, slug])

  if (isLoading) return <PageLoader />
  if (isError || !product) return (
    <div className="container-main py-20">
      <ErrorMessage message="محصول یافت نشد" />
    </div>
  )

  const variant = selectedVariant || product.variants?.[0]
  const inStock = variant?.is_in_stock && variant?.available_stock > 0
  // وضعیت دستی موجودی: به‌زودی (در راه) یا توقف تولید (ناموجود دائمی) — پیش‌فرض auto یعنی بر اساس انبار
  const availability = product.availability || 'auto'

  // قیمت فرمول بر اساس سطح همکاری — عمومی: مشتری عمومی | سیلور: یکماهه | گلد: تو حسابی | پلاتینیوم: تو حسابی + گزینه‌ها
  const pricing = variant?.pricing
  const isPlatinum = pricing?.tier === 'platinum' && !!pricing?.options
  const PRICE_LABELS = { retail: 'قیمت فروش', cash: 'قیمت نقدی', credit: 'قیمت تو حسابی', month1: 'قیمت یکماهه', month2: 'قیمت دوماهه' }
  const PAY_OPTION_LABELS = { credit: 'تو حسابی', cash: 'پرداخت در لحظه', month1: 'پرداخت یکماهه', month2: 'پرداخت دوماهه' }
  // برای پلاتینیوم قاب مثبت: اعتباری = «قیمت ویژه همکار» (نه گران‌تر)، نقدی = «تخفیف ویژه نقدی»
  // پلاتینیوم خودش روش پرداخت را انتخاب می‌کند (لیبل همان گزینه)؛ برای سطوح دیگر
  // نام ستون قیمت (یکماهه/تو حسابی) نمایش داده نمی‌شود تا ساختار قیمت‌گذاری لو نرود
  const priceLabel = isPlatinum
    ? (payOption === 'credit' ? 'قیمت ویژه همکار' : payOption === 'cash' ? 'قیمت نقدی شما' : (PRICE_LABELS[payOption] || 'قیمت فروش'))
    : (pricing?.tier ? 'قیمت همکار' : 'قیمت فروش')
  const displayPrice = isPlatinum
    ? (pricing.options[payOption] ?? Object.values(pricing.options)[0])
    : (pricing?.price ?? variant?.final_price)
  // سود انتخاب نقدی/یکماهه نسبت به اعتباری (برای بج خوشحالی)
  const platinumSaving = isPlatinum && payOption !== 'credit'
    ? Math.max(0, pricing.options.credit - pricing.options[payOption])
    : 0

  const handleAdd = async () => {
    if (!variant || !inStock) return
    setAdding(true)
    try {
      // نحوه تسویه این قلم — پلاتینیوم همان گزینه انتخابی روی صفحه؛ سیلور/گلد/عمومی همیشه نقدی
      // (ستون یکماهه/توحسابی فقط مبنای قیمت آن‌هاست و در price_for_settlement لحاظ می‌شود)
      const tier = pricing?.tier
      const settlement = tier === 'platinum' ? payOption : 'cash'
      if (isPartner()) {
        await orderService.addToInquiryCart(variant.id, qty, settlement)
        // کش سبد استعلام باطل شود — وگرنه صفحه سبد تا ۵ دقیقه نسخه قدیمی (خالی) را نشان می‌دهد
        qc.invalidateQueries(['inquiry-cart'])
      } else {
        await orderService.addToCart(variant.id, qty, settlement)
        qc.invalidateQueries(['cart'])
      }
      increment()
      setAdded(true)
      setTimeout(() => setAdded(false), 2000)
    } catch (e) {
      console.error(e)
      toast.error(e.response?.data?.error || 'خطا در افزودن به سبد. لطفاً دوباره تلاش کنید.')
    } finally {
      setAdding(false)
    }
  }

  const compared = inCompare(product.slug)
  const handleCompare = () => {
    if (compared) {
      removeFromCompare(product.slug)
    } else {
      addToCompare({
        slug: product.slug,
        name: product.name,
        category_id: product.category?.id,
        image: images.find(i => i.is_primary)?.image || images[0]?.image || null,
        min_price: displayPrice || null,
      })
    }
  }

  const images = product.images || []
  const specs  = product.specs || []

  // ─── SEO/GEO ─────────────────────────────────────────────────
  const canonical = `/products/${product.slug}`
  const mainImage = images.find(i => i.is_primary)?.image || images[0]?.image
  const seoTitle = product.meta_title || `${product.name} | دوربینکار`
  const seoDescription = product.meta_description || product.short_description || product.description?.slice(0, 160)
  // breadcrumb: خانه > (والد >) دسته > محصول
  const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData?.results || [])
  const parentCategory = product.category?.parent
    ? categories.find(c => c.id === product.category.parent)
    : null
  const breadcrumbItems = [
    { name: 'خانه', url: '/' },
    ...(parentCategory ? [{ name: parentCategory.name, url: `/categories/${parentCategory.slug}` }] : []),
    ...(product.category ? [{ name: product.category.name, url: `/categories/${product.category.slug}` }] : []),
    { name: product.name, url: canonical },
  ]
  const productLd = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    ...(mainImage && { image: absoluteUrl(mainImage) }),
    ...(seoDescription && { description: seoDescription }),
    ...(product.brand && { brand: { '@type': 'Brand', name: product.brand } }),
    ...(variant?.sku && { sku: variant.sku }),
    ...(variant?.final_price != null && {
      offers: {
        '@type': 'Offer',
        url: absoluteUrl(canonical),
        // قیمت فرمول (ریال) — یکسان با قیمت نمایشی صفحه
        price: variant.pricing?.price ?? variant.final_price,
        priceCurrency: 'IRR',
        availability: inStock
          ? 'https://schema.org/InStock'
          : 'https://schema.org/OutOfStock',
      },
    }),
  }
  const breadcrumbLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbItems.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: absoluteUrl(item.url),
    })),
  }

  return (
    <div className="container-main py-8">
      <Seo
        title={seoTitle}
        description={seoDescription}
        keywords={product.keywords}
        canonical={canonical}
        image={mainImage}
        geoTags={product.geo_tags}
        jsonLd={[productLd, breadcrumbLd]}
      />
      {/* Breadcrumb + ناوبری محصول قبلی/بعدی */}
      <div className="flex items-center justify-between gap-3 mb-8 flex-wrap">
        <nav className="flex items-center gap-2 text-xs text-gray-steel min-w-0">
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
        <ProductNav slug={product.slug} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* تصاویر */}
        <div className="space-y-3">
          <div className="card overflow-hidden aspect-square product-media-stage">
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
                  className={`flex-shrink-0 w-16 h-16 rounded-lg border-2 overflow-hidden transition-all product-media-stage
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
                  <>
                      <div className="text-xs text-gray-steel mb-1">{priceLabel}</div>
                      <div className="text-2xl font-bold text-brand dark:text-cyan">
                        {Number(displayPrice).toLocaleString('fa-IR')}
                        <span className="text-sm font-normal text-gray-steel mr-1">ریال</span>
                      </div>
                      {/* قیمت اصلی خط‌خورده وقتی واریانت تخفیف دارد */}
                      {pricing?.original_price && !isPlatinum && (
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="text-xs text-gray-steel line-through">
                            {Number(pricing.original_price).toLocaleString('fa-IR')} ریال
                          </span>
                          <span className="text-xs bg-alert-red/10 text-alert-red px-2 py-0.5 rounded-full">
                            ٪{Number(pricing.discount_percent).toLocaleString('fa-IR')} تخفیف
                          </span>
                        </div>
                      )}
                      {/* پلاتینیوم با پرداخت در لحظه — قیمت تو حسابی خط می‌خورد + مبلغ سود */}
                      {isPlatinum && payOption === 'cash' && (
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="text-xs text-gray-steel line-through">
                            {Number(pricing.options.credit).toLocaleString('fa-IR')} ریال
                          </span>
                          <span className="text-xs bg-alert-green/10 text-alert-green px-2 py-0.5 rounded-full">
                            🎉 تخفیف ویژه نقدی{platinumSaving > 0 ? ` — ${platinumSaving.toLocaleString('fa-IR')} ریال سود` : ''}
                          </span>
                        </div>
                      )}
                      {/* قاب مثبت برای خرید اعتباری */}
                      {isPlatinum && payOption === 'credit' && (
                        <div className="text-[11px] text-alert-green mt-1">
                          🤝 خرید اعتباری بدون هزینه اضافه — الان ببر، در سررسید پرداخت کن
                        </div>
                      )}
                      {/* قاب مثبت برای گزینه‌های ماهانه (یکماهه/دوماهه) */}
                      {isPlatinum && payOption.startsWith('month') && platinumSaving > 0 && (
                        <div className="text-[11px] text-alert-green mt-1">
                          📅 {platinumSaving.toLocaleString('fa-IR')} ریال ارزان‌تر از خرید اعتباری
                        </div>
                      )}
                    </>
                </div>
              ) : availability === 'coming_soon' ? (
                <div>
                  <div className="font-medium text-blue-500 dark:text-cyan">🔜 به‌زودی</div>
                  {/* قیمت برای محصولات «به‌زودی» هم نمایش داده می‌شود — فقط افزودن به سبد غیرفعال است */}
                  {displayPrice != null && (
                    <div className="mt-2">
                      <div className="text-xs text-gray-steel mb-1">{priceLabel}</div>
                      <div className="text-2xl font-bold text-brand dark:text-cyan">
                        {Number(displayPrice).toLocaleString('fa-IR')}
                        <span className="text-sm font-normal text-gray-steel mr-1">ریال</span>
                      </div>
                      {pricing?.original_price && !isPlatinum && (
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="text-xs text-gray-steel line-through">
                            {Number(pricing.original_price).toLocaleString('fa-IR')} ریال
                          </span>
                          <span className="text-xs bg-alert-red/10 text-alert-red px-2 py-0.5 rounded-full">
                            ٪{Number(pricing.discount_percent).toLocaleString('fa-IR')} تخفیف
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="text-xs text-gray-steel mt-1">این محصول در راه است — برای اطلاع از موجود شدن با ما در تماس باشید.</div>
                </div>
              ) : availability === 'discontinued' ? (
                <div>
                  <div className="text-alert-red font-medium">توقف تولید</div>
                  <div className="text-xs text-gray-steel mt-1">این محصول دیگر تولید و موجود نمی‌شود.</div>
                </div>
              ) : (
                <div className="text-alert-red font-medium">ناموجود</div>
              )}
            </div>
          )}

          <VariantSelector variants={product.variants} selected={selectedVariant} onSelect={setSelectedVariant} />

          {/* گزینه‌های پرداخت همکار پلاتینیوم */}
          {isPlatinum && inStock && (
            <div className="mb-4">
              <div className="text-xs text-gray-steel mb-2">روش پرداخت:</div>
              <div className="flex gap-2 flex-wrap">
                {/* گزینه‌ها از کلیدهای pricing.options رندر می‌شوند — month2 خودکار ظاهر می‌شود */}
                {Object.keys(pricing.options).map(k => (
                  <button key={k} onClick={() => setPayOption(k)}
                    className={`text-xs px-4 py-2 rounded-xl border transition-all text-center
                      ${payOption === k
                        ? 'border-brand bg-brand/10 text-brand dark:text-cyan'
                        : 'border-gray-200 dark:border-white/10 text-gray-steel hover:border-brand/50'}`}>
                    <div>{PAY_OPTION_LABELS[k] || PRICE_LABELS[k] || k}</div>
                    {/* قیمت نقدی فقط بعد از انتخاب تیک نمایش داده می‌شود (تخفیف ویژه نقدی) */}
                    {k !== 'cash' && (
                      <div className="mt-0.5 font-bold">{Number(pricing.options[k]).toLocaleString('fa-IR')} ریال</div>
                    )}
                    {k === 'cash' && payOption !== 'cash' && (
                      <div className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">با تخفیف ویژه</div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* تعداد + افزودن */}
          {isAuthenticated() && (
            <div>
              <div className="flex items-center gap-3">
                <div className="flex items-center border border-gray-200 dark:border-white/10 rounded-xl overflow-hidden">
                  <button onClick={() => setQty(q => Math.max(1, q - 1))}
                    className="px-3 py-2 hover:bg-brand/10 transition-colors text-lg leading-none">−</button>
                  <span className="text-[10px] text-[var(--color-text-muted)] select-none pr-1">✏️</span>
                  <input
                    type="text" inputMode="numeric"
                    // تایپ آزاد عدد دلخواه — با کلیک کل متن انتخاب می‌شود تا جایگزین شود
                    value={qtyText ?? qty.toLocaleString('en')}
                    onFocus={e => { setQtyText(String(qty)); setTimeout(() => e.target.select(), 0) }}
                    onChange={e => {
                      // ارقام فارسی/عربی هم پذیرفته می‌شود
                      const raw = e.target.value
                        .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
                        .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
                        .replace(/[^\d]/g, '').slice(0, 5)
                      setQtyText(raw)
                      const v = parseInt(raw)
                      if (v >= 1) setQty(Math.min(v, 99999))
                    }}
                    onBlur={() => setQtyText(null)}
                    className="w-28 py-2 text-base font-mono font-bold text-center bg-transparent border-x border-gray-200 dark:border-white/10 focus:outline-none"
                    dir="ltr"
                    placeholder="تایپ کنید"
                  />
                  <button onClick={() => setQty(q => Math.min(99999, q + 1))}
                    className="px-3 py-2 hover:bg-brand/10 transition-colors text-lg leading-none">+</button>
                </div>

                <button onClick={handleAdd} disabled={adding || !inStock}
                  className={`flex-1 py-3 rounded-xl font-medium text-sm transition-all
                    ${added ? 'bg-alert-green text-white'
                      : inStock ? 'bg-brand text-white hover:bg-brand-light shadow-sm'
                      : 'bg-gray-200 dark:bg-white/5 text-gray-400 cursor-not-allowed'}`}>
                  {adding ? '...' : added ? '✓ اضافه شد!'
                    : !inStock ? (availability === 'coming_soon' ? '🔜 به‌زودی' : availability === 'discontinued' ? 'توقف تولید' : 'ناموجود')
                    : isPartner() ? '+ افزودن به سبد استعلام'
                    : '+ افزودن به سبد خرید'}
                </button>

                <button onClick={handleCompare}
                  title={compared ? 'حذف از مقایسه' : 'افزودن به مقایسه'}
                  className={`px-4 py-3 rounded-xl text-sm font-medium border transition-all
                    ${compared
                      ? 'border-brand text-brand bg-brand/10'
                      : 'border-gray-200 dark:border-white/10 text-gray-500 dark:text-gray-steel hover:border-brand hover:text-brand'}`}>
                  ⚖ {compared ? 'در مقایسه' : 'مقایسه'}
                </button>
              </div>

              {/* جمع مبلغ زنده — برای خرید عمده */}
              {inStock && qty > 1 && displayPrice != null && (
                <div className="text-xs text-gray-steel mt-2">
                  جمع {qty.toLocaleString('fa-IR')} عدد:
                  <span className="font-bold text-brand dark:text-cyan mr-1">
                    {(qty * displayPrice).toLocaleString('fa-IR')} ریال
                  </span>
                </div>
              )}

              {/* هشدار موجودی — تعداد بیشتر از موجودی قابل فروش پذیرفته نمی‌شود */}
              {variant && qty > (variant.available_stock || 0) && (
                <div className="text-[11px] text-alert-red bg-alert-red/10 rounded-lg px-3 py-2 mt-2">
                  ⚠️ درخواست شما بیشتر از موجودی است — حداکثر {(variant.available_stock || 0).toLocaleString('fa-IR')} عدد قابل سفارش است.
                </div>
              )}

              {/* انتخاب سریع تعدادهای زیاد */}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <span className="text-[10px] text-gray-steel">💡 روی عدد بالا کلیک کنید و تعداد دلخواه را تایپ کنید، یا:</span>
                {[10, 50, 100, 500, 1000, 2000].map(n => (
                  <button key={n}
                    onClick={() => setQty(Math.min(n, 99999))}
                    className={`text-[11px] px-3 py-1 rounded-full border transition-all
                      ${qty === n ? 'border-brand bg-brand/10 text-brand dark:text-cyan'
                        : 'border-gray-200 dark:border-white/10 text-gray-steel hover:border-brand/50'}`}>
                    {n.toLocaleString('fa-IR')} عدد
                  </button>
                ))}
              </div>
            </div>
          )}

          {!isAuthenticated() && (
            <div className="flex items-center gap-3">
              <Link to="/auth/login"
                className="flex-1 flex items-center justify-center py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-light transition-colors">
                برای خرید وارد شوید
              </Link>
              <button onClick={handleCompare}
                title={compared ? 'حذف از مقایسه' : 'افزودن به مقایسه'}
                className={`px-4 py-3 rounded-xl text-sm font-medium border transition-all
                  ${compared
                    ? 'border-brand text-brand bg-brand/10'
                    : 'border-gray-200 dark:border-white/10 text-gray-500 dark:text-gray-steel hover:border-brand hover:text-brand'}`}>
                ⚖ {compared ? 'در مقایسه' : 'مقایسه'}
              </button>
            </div>
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


      {/* پکیج‌های مرتبط */}
      <ProductPackages productId={product.id} />

      {/* نمودار قیمت */}
      <PriceChart slug={product.slug} variantId={variant?.id} />

      {/* جایگزین‌های پیشنهادی */}
      <SimilarProducts slug={product.slug} />

      {product.compatible_with?.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display font-bold text-xl text-white mb-4">🔗 قطعات سازگار</h2>
          <div className="grid grid-cols-2 gap-3">
            {product.compatible_with.map(p => (
              <Link key={p.id} to={`/products/${p.slug}`}
                className="card p-4 flex items-center gap-3 hover:border-brand/30 transition-all group">
                {p.image && (
                  <img src={p.image} alt={p.name}
                    className="w-14 h-14 object-contain rounded-lg bg-white/5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-white group-hover:text-brand transition-colors truncate">
                    {p.name}
                  </div>
                  {p.category_name && (
                    <div className="text-xs text-gray-steel mt-0.5">{p.category_name}</div>
                  )}
                  <div className="text-xs text-cyan mt-1">مشاهده محصول ←</div>
                </div>
              </Link>
            ))}
          </div>
          <p className="text-xs text-gray-steel mt-3">
            این قطعات با یکدیگر سازگار هستند و می‌توانند در کنار هم استفاده شوند.
          </p>
        </section>
      )}

      {/* دیتاشیت فنی — انتهای صفحه: گالری تصاویر PDF برای مطالعه عمیق، بدون دفن کردن محصولات مشابه */}
      {product.has_datasheet && product.datasheet_pdf && (
        <section className="mt-8">
          <h2 className="font-display font-bold text-xl text-white mb-4">📄 دیتاشیت فنی</h2>
          <a href={mediaUrl(product.datasheet_pdf)} target="_blank" rel="noreferrer" download
            className="inline-flex items-center justify-center gap-2 mb-4 px-5 py-2.5 rounded-xl
              bg-brand/10 text-brand dark:text-cyan border border-brand/20
              hover:bg-brand/20 transition-colors text-sm font-medium">
            ⬇ دانلود PDF دیتاشیت
          </a>
          {product.datasheet_pages?.length > 0 && (
            <div className="space-y-4">
              {product.datasheet_pages.map(p => (
                <div key={p.id} className="card p-2 sm:p-3">
                  <img src={mediaUrl(p.image)} loading="lazy"
                    alt={`دیتاشیت ${product.name} — صفحه ${p.page}`}
                    className="w-full rounded-lg bg-white" />
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}