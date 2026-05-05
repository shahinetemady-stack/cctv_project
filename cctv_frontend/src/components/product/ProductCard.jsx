import { Link } from 'react-router-dom'
import { formatPrice, partTypeLabel } from '../../utils/format'
import useAuthStore from '../../store/useAuthStore'
import useCartStore from '../../store/useCartStore'
import { orderService } from '../../services/orders'
import { useState } from 'react'

const PART_TYPE_ICON = {
  sensor: '📷', lens: '🔭', board: '🔌', isp: '💻',
  housing: '📦', ir_cut: '🔴', motor: '⚙️', fpc: '📎',
  power: '⚡', other: '🔧',
}

function StockBadge({ available_stock }) {
  if (available_stock === 0)
    return <span className="badge-red">ناموجود</span>
  if (available_stock <= 5)
    return <span className="badge-orange">⚠ کم ({available_stock})</span>
  return <span className="badge-green">موجود</span>
}

export default function ProductCard({ product }) {
  const { isAuthenticated, isPartner } = useAuthStore()
  const { increment } = useCartStore()
  const [adding, setAdding] = useState(false)

  const variant = product.variants?.[0]
  const price = product.min_price || variant?.final_price
  const inStock = product.available_stock > 0

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
            <span className="text-4xl">{PART_TYPE_ICON[product.part_type] || '🔧'}</span>
            <span className="text-xs text-gray-steel font-mono">{product.model_number || 'NO IMG'}</span>
          </div>
        )}

        {/* بج ویژه */}
        {product.is_featured && (
          <div className="absolute top-2 right-2 badge bg-brand text-white text-[10px]">
            ⭐ ویژه
          </div>
        )}

        {/* اسکن‌لاین دوربین */}
        <div className="absolute inset-0 scan-line opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
      </div>

      {/* اطلاعات */}
      <div className="flex-1 p-4 flex flex-col gap-2">
        {/* نوع قطعه */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-gray-steel uppercase tracking-wider">
            {partTypeLabel[product.part_type] || product.part_type}
          </span>
          <StockBadge available_stock={product.available_stock} />
        </div>

        {/* نام */}
        <h3 className="font-semibold text-sm leading-snug line-clamp-2
          text-gray-900 dark:text-white group-hover:text-brand dark:group-hover:text-cyan transition-colors">
          {product.name}
        </h3>

        {/* مشخصات کلیدی */}
        <div className="flex flex-wrap gap-1 mt-auto">
          {product.chipset && (
            <span className="text-[10px] bg-brand/10 text-brand dark:text-cyan px-2 py-0.5 rounded-full">
              {product.chipset}
            </span>
          )}
          {product.voltage && (
            <span className="text-[10px] bg-white/5 text-gray-steel px-2 py-0.5 rounded-full">
              {product.voltage}
            </span>
          )}
        </div>

        {/* قیمت و دکمه */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-white/5 mt-1">
          <div>
            {isAuthenticated() && isPartner() ? (
              <span className="text-xs text-gray-steel">قیمت استعلامی</span>
            ) : price ? (
              <div>
                <div className="text-xs text-gray-steel">قیمت</div>
                <div className="text-sm font-bold text-brand dark:text-cyan font-mono">
                  {Number(price).toLocaleString('fa-IR')}
                  <span className="text-[10px] font-normal text-gray-steel mr-1">تومان</span>
                </div>
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
