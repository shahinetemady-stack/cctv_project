import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { orderService } from '../services/orders'
import useAuthStore from '../store/useAuthStore'
import { formatPrice } from '../utils/format'

// بنر هشدار تسویه معوقه — در صفحات سبد خرید/استعلام نمایش داده می‌شود
// ثبت سفارش جدید را مسدود نمی‌کند؛ فقط اطلاع‌رسانی + قابل بستن است
export default function OverdueBanner() {
  const { isAuthenticated } = useAuthStore()
  const [dismissed, setDismissed] = useState(false)

  const { data } = useQuery({
    queryKey: ['my-overdue'],
    queryFn: orderService.getMyOverdue,
    enabled: isAuthenticated(),
    staleTime: 60000,
  })

  if (dismissed || !data?.count) return null

  return (
    <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 flex items-start gap-3">
      <span className="text-amber-400 text-lg leading-none mt-0.5">⚠️</span>
      <p className="flex-1 text-sm text-amber-200 leading-relaxed">
        شما {Number(data.count).toLocaleString('fa-IR')} قلم تسویه معوقه به مبلغ {formatPrice(data.total)} دارید.
        ثبت سفارش جدید ممنوع نیست اما در اولویت بررسی قرار می‌گیرد.
      </p>
      <button onClick={() => setDismissed(true)} aria-label="بستن"
        className="text-amber-400/60 hover:text-amber-300 transition-colors text-lg leading-none px-1">
        ×
      </button>
    </div>
  )
}
