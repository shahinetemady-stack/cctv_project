import { Link } from 'react-router-dom'
import { RotateCw, Scale } from 'lucide-react'
import useCompareStore from '../../store/useCompareStore'
import { useState } from 'react'

const CATEGORY_TYPE_ICON = {
  board: '📟', lens: '🔭', modem: '📡', housing: '📦', other: '🔧',
}

function StockBadge({ available_stock, availability }) {
  // به‌زودی/توقف تولید مستقل از عدد موجودی است — موجودی صفرِ عادی همان «ناموجود» می‌ماند
  if (availability === 'coming_soon')
    return <span className="badge-blue text-[10px]">🔜 به‌زودی</span>
  if (availability === 'discontinued')
    return <span className="badge-red text-[10px]">توقف تولید</span>
  if (available_stock === 0)
    return <span className="badge-red text-[10px]">ناموجود</span>
  if (available_stock <= 5)
    return <span className="badge-orange text-[10px]">⚠ کم</span>
  return <span className="badge-green text-[10px]">موجود</span>
}

export default function ProductCard({ product }) {
  const { add: addToCompare, remove: removeFromCompare, has: inCompare } = useCompareStore()
  const [flipped, setFlipped] = useState(false)

  const variant = product.variants?.[0]
  const price = product.min_price || variant?.final_price
  const catType = product.category_type || 'other'
  const compared = inCompare(product.slug)
  // چیپ‌های مشخصات زیر مدل — همان استایل کارت هوم‌پیج (زرد = رنگ برند)
  const specChips = catType === 'lens'
    ? [{ v: product.lens_resolution, lat: 1 }, { v: product.lens_degree, lat: 1 }, { v: product.focal_ratio }, { v: product.brand }]
    : catType === 'board'
      ? [{ v: product.board_system, lat: 1 }, { v: product.board_resolution, lat: 1 }, { v: product.brand }]
      : [{ v: product.brand }, { v: product.sensor_name, gray: 1 }, { v: product.lens_name, gray: 1 }]

  const handleCompare = (e) => {
    e.preventDefault()
    if (compared) {
      removeFromCompare(product.slug)
    } else {
      addToCompare({
        slug: product.slug,
        name: product.name,
        category_id: product.category_id,
        image: product.main_image?.image || null,
        min_price: price || null,
      })
    }
  }

  return (
    <Link to={`/products/${product.slug}`}
      className="card card-hover flex flex-col group overflow-hidden cursor-pointer">

      {/* تصویر — استیج روشن برای خوانایی محصولات مشکی؛ با تصویر دوم، هاور = چرخش به نمای پشت */}
      <div className="relative aspect-square product-media-stage overflow-hidden">
        {product.main_image ? (
          product.secondary_image ? (
            <div className="product-flip">
              <div className={`product-flip-inner${flipped ? ' flipped' : ''}`}>
                <div className="product-flip-face">
                  <img
                    src={product.main_image.image}
                    alt={product.name}
                    className="w-full h-full object-contain p-4"
                  />
                </div>
                <div className="product-flip-face product-flip-back">
                  <img
                    src={product.secondary_image.image}
                    alt={`${product.name} — نمای دیگر`}
                    loading="lazy"
                    className="w-full h-full object-contain p-4"
                  />
                </div>
              </div>
            </div>
          ) : (
            <img
              src={product.main_image.image}
              alt={product.name}
              className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-500"
            />
          )
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <span className="text-4xl">{CATEGORY_TYPE_ICON[catType]}</span>
          </div>
        )}
        {/* دکمه چرخش تصویر — فقط روی دستگاه‌های لمسی نمایش داده می‌شود (CSS: hover: none) */}
        {product.secondary_image && (
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); setFlipped(v => !v) }}
            aria-label="نمایش نمای دیگر محصول"
            className="product-flip-btn absolute bottom-2 left-2 z-10 w-11 h-11 rounded-full items-center justify-center border border-[var(--color-border-strong)] bg-[var(--color-bg-elevated)]/80 backdrop-blur text-[#FFB25C] active:scale-90 transition-transform"
          >
            <RotateCw size={17} />
          </button>
        )}
        {product.is_featured && (
          <div className="absolute top-2 right-2 badge badge-gold text-[10px]">
            ⭐ ویژه
          </div>
        )}
        {(product.discount_percent || 0) > 0 && (
          <div className="absolute top-2 left-2 badge badge-red text-[10px]">
            ٪{Number(product.discount_percent).toLocaleString('fa-IR')} تخفیف
          </div>
        )}
      </div>

      {/* اطلاعات */}
      <div className="flex-1 p-4 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-gray-steel uppercase tracking-wider">
            {product.category_name || ''}
          </span>
          <StockBadge available_stock={product.available_stock} availability={product.availability} />
        </div>

        <h3 className="font-semibold text-sm leading-snug line-clamp-2
          text-gray-900 dark:text-white group-hover:text-brand dark:group-hover:text-cyan transition-colors"
          style={{ unicodeBidi: 'plaintext' }}>
          {product.name}
        </h3>

        {/* مدل (خط مونو) + چیپ‌های مشخصات زیر آن — استایل یکسان با کارت هوم‌پیج */}
        {/* مدل فقط وقتی جدا نشان داده می‌شود که داخل نام محصول نباشد */}
        {product.model_number && (catType === 'lens' || catType === 'board' || !product.name.includes(product.model_number)) && (
          <div dir="ltr" className="text-right text-[15px] font-extrabold font-mono tracking-wide
            text-gray-700 dark:text-[var(--color-text-secondary)] -mt-0.5">
            {product.model_number}
          </div>
        )}
        {specChips.some(c => c.v) && (
          <div className="flex flex-wrap gap-1">
            {specChips.filter(c => c.v).map((c, i) => (
              <span key={i} dir={c.lat ? 'ltr' : undefined}
                className={`rounded-full whitespace-nowrap${c.lat ? ' font-mono' : ''}`}
                style={{
                  fontSize: 13, padding: '3px 10px',
                  background: c.gray ? 'var(--color-bg-tertiary)' : 'rgba(251,192,45,0.12)',
                  color: c.gray ? 'var(--color-text-muted)' : 'var(--color-brand)',
                }}>
                {c.v}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-white/5 mt-auto">
          <div>
            {price ? (
              <div>
                {product.min_price_original && (
                  <div className="text-[11px] text-gray-steel line-through">
                    {Number(product.min_price_original).toLocaleString('fa-IR')}
                  </div>
                )}
                <div className="text-sm font-bold text-brand dark:text-cyan">
                  {Number(price).toLocaleString('fa-IR')}
                  <span className="text-[10px] font-normal text-gray-steel mr-1">ریال</span>
                </div>
              </div>
            ) : (
              <span className="text-xs text-gray-steel">—</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCompare}
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-all ${
                compared
                  ? 'border-brand text-brand bg-brand/10'
                  : 'border-white/10 text-gray-steel hover:text-white hover:border-white/25'
              }`}
            >
              <Scale size={13} />
              <span>مقایسه</span>
            </button>
          </div>
        </div>
      </div>
    </Link>
  )
}