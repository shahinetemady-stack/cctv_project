import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../services/catalog'
import { orderService } from '../services/orders'
import useAuthStore from '../store/useAuthStore'
import useCartStore from '../store/useCartStore'
import { PageLoader, ErrorMessage } from '../components/ui'
import { formatPrice, partTypeLabel, lensMountLabel } from '../utils/format'

function SpecRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-100 dark:border-white/5 last:border-0">
      <span className="text-sm text-gray-steel">{label}</span>
      <span className="text-sm font-medium text-gray-900 dark:text-white">{value}</span>
    </div>
  )
}

function VariantCard({ variant, selected, onSelect }) {
  return (
    <button
      onClick={() => onSelect(variant)}
      className={`p-3 rounded-xl border text-sm transition-all
        ${selected?.id === variant.id
          ? 'border-brand bg-brand/10 text-brand dark:text-cyan'
          : 'border-gray-200 dark:border-white/10 hover:border-brand/50'}`}
    >
      <div className="font-mono text-xs text-gray-steel">{variant.sku}</div>
      {variant.name_suffix && <div className="mt-1">{variant.name_suffix}</div>}
      <div className={`mt-2 font-bold font-mono
        ${variant.is_in_stock ? 'text-brand dark:text-cyan' : 'text-gray-400 line-through'}`}>
        {formatPrice(variant.final_price)}
      </div>
      <div className={`text-[10px] mt-1 ${variant.is_in_stock ? 'text-alert-green' : 'text-alert-red'}`}>
        {variant.is_in_stock
          ? variant.is_low_stock ? `⚠ کم (${variant.available_stock})` : `موجود (${variant.available_stock})`
          : 'ناموجود'}
      </div>
    </button>
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

  return (
    <div className="container-main py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-gray-steel mb-8">
        <Link to="/" className="hover:text-brand transition-colors">خانه</Link>
        <span>/</span>
        <Link to="/products" className="hover:text-brand transition-colors">محصولات</Link>
        <span>/</span>
        <span className="text-gray-900 dark:text-white truncate">{product.name}</span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* ─── تصاویر ───────────────────────────────────────────── */}
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

        {/* ─── اطلاعات محصول ────────────────────────────────────── */}
        <div className="space-y-6">
          {/* سربرگ */}
          <div>
            {product.brand && (
              <div className="text-xs font-mono text-brand dark:text-cyan mb-1 uppercase">
                {product.brand}
              </div>
            )}
            <h1 className="font-display font-bold text-2xl text-gray-900 dark:text-white leading-snug">
              {product.name}
            </h1>
            {product.model_number && (
              <div className="font-mono text-sm text-gray-steel mt-1">#{product.model_number}</div>
            )}
          </div>

          {/* قیمت */}
          {variant && (
            <div className="card p-4">
              {isPartner() ? (
                <div className="text-center py-2">
                  <div className="text-sm text-gray-steel mb-1">قیمت همکار</div>
                  <div className="text-lg font-bold text-cyan">استعلامی</div>
                </div>
              ) : (
                <div>
                  <div className="text-xs text-gray-steel mb-1">قیمت فروش</div>
                  <div className="text-2xl font-display font-bold text-brand dark:text-cyan">
                    {formatPrice(variant.final_price)}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* variant‌ها */}
          {product.variants?.length > 1 && (
            <div>
              <div className="label">انتخاب نوع / رنگ</div>
              <div className="grid grid-cols-2 gap-2">
                {product.variants.map(v => (
                  <VariantCard key={v.id} variant={v}
                    selected={selectedVariant} onSelect={setSelectedVariant} />
                ))}
              </div>
            </div>
          )}

          {/* تعداد + دکمه افزودن */}
          {isAuthenticated() && (
            <div className="flex items-center gap-3">
              <div className="flex items-center border border-gray-200 dark:border-white/10 rounded-xl overflow-hidden">
                <button onClick={() => setQty(q => Math.max(1, q - 1))}
                  className="px-3 py-2 hover:bg-brand/10 transition-colors text-lg">−</button>
                <span className="px-4 py-2 text-sm font-mono min-w-[3rem] text-center">{qty}</span>
                <button onClick={() => setQty(q => Math.min(variant?.available_stock || 99, q + 1))}
                  className="px-3 py-2 hover:bg-brand/10 transition-colors text-lg">+</button>
              </div>

              <button
                onClick={handleAdd}
                disabled={adding || !inStock}
                className={`flex-1 btn text-sm py-3 transition-all
                  ${added ? 'bg-alert-green text-white'
                    : inStock ? 'btn-primary' : 'bg-gray-200 dark:bg-white/5 text-gray-400 cursor-not-allowed'}`}
              >
                {adding ? '...' : added ? '✓ اضافه شد!'
                  : !inStock ? 'ناموجود'
                  : isPartner() ? '+ افزودن به سبد استعلام' : '+ افزودن به سبد خرید'}
              </button>
            </div>
          )}

          {!isAuthenticated() && (
            <Link to="/auth/login" className="btn-primary w-full text-center py-3">
              برای خرید وارد شوید
            </Link>
          )}

          {/* تماس سریع */}
          <div className="flex gap-2">
            {product.whatsapp_link && (
              <a href={product.whatsapp_link} target="_blank" rel="noreferrer"
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl
                  bg-green-500/10 text-green-500 border border-green-500/20
                  hover:bg-green-500/20 transition-colors text-sm font-medium">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                  <path d="M12 0C5.373 0 0 5.373 0 12c0 2.127.563 4.122 1.538 5.848L0 24l6.335-1.617A11.945 11.945 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.943 0-3.77-.524-5.345-1.437l-.384-.228-3.981 1.016.908-3.888-.25-.395A9.951 9.951 0 012 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/>
                </svg>
                واتساپ
              </a>
            )}
            {product.bale_link && (
              <a href={product.bale_link} target="_blank" rel="noreferrer"
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl
                  bg-blue-500/10 text-blue-400 border border-blue-500/20
                  hover:bg-blue-500/20 transition-colors text-sm font-medium">
                💬 بله
              </a>
            )}
            {product.has_datasheet && (
              <a href={product.datasheet_pdf} target="_blank" rel="noreferrer"
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl
                  bg-brand/10 text-brand dark:text-cyan border border-brand/20
                  hover:bg-brand/20 transition-colors text-sm font-medium">
                📄 دیتاشیت
              </a>
            )}
          </div>

          {/* مشخصات فنی */}
          <div className="card p-4">
            <h3 className="font-semibold text-sm mb-3">مشخصات فنی</h3>
            <SpecRow label="نوع قطعه" value={partTypeLabel[product.part_type]} />
            <SpecRow label="چیپست" value={product.chipset} />
            <SpecRow label="ولتاژ" value={product.voltage} />
            <SpecRow label="مانت لنز" value={lensMountLabel[product.lens_mount]} />
            <SpecRow label="رزولوشن" value={product.resolution} />
            <SpecRow label="برند" value={product.brand} />
            <SpecRow label="شماره مدل" value={product.model_number} />
            {product.extra_specs && Object.entries(product.extra_specs).map(([k, v]) => (
              <SpecRow key={k} label={k} value={String(v)} />
            ))}
          </div>
        </div>
      </div>

      {/* توضیحات */}
      {product.description && (
        <section className="mt-12">
          <h2 className="font-display font-bold text-xl text-white mb-4">توضیحات</h2>
          <div className="card p-6 text-sm text-gray-700 dark:text-gray-300 leading-loose whitespace-pre-line">
            {product.description}
          </div>
        </section>
      )}

      {/* محصولات سازگار */}
      {product.compatible_with?.length > 0 && (
        <section className="mt-12">
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
