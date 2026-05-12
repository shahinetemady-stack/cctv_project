import { Link } from 'react-router-dom'
import useAuthStore from '../../store/useAuthStore'
import useCartStore from '../../store/useCartStore'
import { orderService } from '../../services/orders'
import { useState } from 'react'

const CATEGORY_TYPE_ICON = {
  board: '📟', lens: '🔭', modem: '📡', housing: '📦', other: '🔧',
}

function StockBadge({ available_stock }) {
  if (available_stock === 0)
    return <span className="badge-red text-[10px]">ناموجود</span>
  if (available_stock <= 5)
    return <span className="badge-orange text-[10px]">⚠ کم</span>
  return <span className="badge-green text-[10px]">موجود</span>
}

export default function ProductCard({ product }) {
  const { isAuthenticated, isPartner } = useAuthStore()
  const { increment } = useCartStore()
  const [adding, setAdding] = useState(false)

  const variant = product.variants?.[0]
  const isUserPartner = isAuthenticated() && isPartner()
  const originalPrice = product.min_price || variant?.final_price
  const partnerPrice = product.partner_min_price
  const price = isUserPartner && partnerPrice ? partnerPrice : originalPrice
  const hasDiscount = isUserPartner && partnerPrice && product.partner_discount_percent > 0
  const inStock = product.available_stock > 0
  const catType = product.category_type || 'other'

  const handleAddToCart = async (e) => {
    e.preventDefault()
    if (!variant || !inStock) return
    setAdding(true)
    try {
      if (isPartner()) {
        await orderService.addToInquiryCart(variant.id)
      } else {
        await orderService.addToCart(variant.id)
      }
      increment()
    } catch (err) {
      console.error(err)
    } finally {
      setAdding(false)
    }
  }

  return (
    <Link to={`/products/${product.slug}`}
      className="card card-hover flex flex-col group overflow-hidden cursor-pointer">

      {/* تصویر */}
      <div className="relative aspect-square bg-gradient-to-br from-navy to-steel overflow-hidden">
        {product.main_image ? (
          <img
            src={product.main_image.image}
            alt={product.name}
            className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <span className="text-4xl">{CATEGORY_TYPE_ICON[catType]}</span>
          </div>
        )}
        {product.is_featured && (
          <div className="absolute top-2 right-2 badge bg-brand text-white text-[10px]">
            ⭐ ویژه
          </div>
        )}
      </div>

      {/* اطلاعات */}
      <div className="flex-1 p-4 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-gray-steel uppercase tracking-wider">
            {product.category_name || ''}
          </span>
          <StockBadge available_stock={product.available_stock} />
        </div>

        <h3 className="font-semibold text-sm leading-snug line-clamp-2
          text-gray-900 dark:text-white group-hover:text-brand dark:group-hover:text-cyan transition-colors">
          {product.name}
        </h3>

        <div className="flex flex-wrap gap-1 mt-auto">
          {product.brand && (
            <span className="text-[10px] bg-brand/10 text-brand dark:text-cyan px-2 py-0.5 rounded-full">
              {product.brand}
            </span>
          )}
          {product.sensor_name && (
            <span className="text-[10px] bg-white/5 text-gray-steel px-2 py-0.5 rounded-full">
              {product.sensor_name}
            </span>
          )}
          {product.lens_name && (
            <span className="text-[10px] bg-white/5 text-gray-steel px-2 py-0.5 rounded-full">
              {product.lens_name}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-white/5 mt-1">
          <div>
            {price ? (
              <div>
                <div className="text-xs text-gray-steel">
                  {isUserPartner ? 'قیمت همکار' : 'قیمت'}
                </div>
                <div className="text-sm font-bold text-brand dark:text-cyan font-mono">
                  {Number(price).toLocaleString('fa-IR')}
                  <span className="text-[10px] font-normal text-gray-steel mr-1">تومان</span>
                </div>
                {hasDiscount && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="text-[10px] text-gray-steel line-through">
                      {Number(originalPrice).toLocaleString('fa-IR')}
                    </span>
                    <span className="text-[10px] text-alert-green">
                      {product.partner_discount_percent}٪ تخفیف
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <span className="text-xs text-gray-steel">—</span>
            )}
          </div>

          {isAuthenticated() && inStock && (
            <button
              onClick={handleAddToCart}
              disabled={adding}
              className="btn-secondary text-xs px-3 py-1.5"
            >
              {adding ? '...' : isPartner() ? '+ استعلام' : '+ سبد'}
            </button>
          )}
        </div>
      </div>
    </Link>
  )
}