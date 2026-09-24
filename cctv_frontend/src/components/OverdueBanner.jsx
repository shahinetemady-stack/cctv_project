import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { orderService } from '../services/orders'
import useAuthStore from '../store/useAuthStore'
import { formatPrice } from '../utils/format'

// بنر هشدار تسویه معوقه — در صفحات سبد خرید/استعلام نمایش داده می‌شود
// سطح محدودیت (level) از بک‌اند می‌آید: warning → فقط هشدار | cash_only → فقط نقدی | blocked → مسدود
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

  const level = data.level || 'warning'
  const styles = {
    warning:   { wrap: 'border-amber-500/30 bg-amber-500/10', icon: '⚠️', text: 'text-amber-200' },
    cash_only: { wrap: 'border-orange-500/40 bg-orange-500/10', icon: '🟠', text: 'text-orange-200' },
    blocked:   { wrap: 'border-red-500/40 bg-red-500/10', icon: '⛔', text: 'text-red-200' },
  }[level]
  const message = {
    warning: 'لطفاً هرچه زودتر تسویه کنید؛ پس از پایان مهلت، خرید اعتباری و سپس ثبت سفارش برای شما محدود می‌شود.',
    cash_only: 'مهلت هشدار تمام شده — فعلاً فقط خرید نقدی برای شما فعال است. اگر تسویه نکنید، ثبت سفارش کاملاً بسته می‌شود.',
    blocked: 'ثبت سفارش جدید برای شما موقتاً غیرفعال است. لطفاً ابتدا تسویه کنید یا با فروشگاه تماس بگیرید.',
  }[level]

  return (
    <div className={`mb-6 rounded-xl border px-4 py-3 flex items-start gap-3 ${styles.wrap}`}>
      <span className="text-lg leading-none mt-0.5">{styles.icon}</span>
      <p className={`flex-1 text-sm leading-relaxed ${styles.text}`}>
        شما {Number(data.count).toLocaleString('fa-IR')} قلم تسویه معوقه به مبلغ {formatPrice(data.total)} دارید.
        {' '}{message}
      </p>
      <button onClick={() => setDismissed(true)} aria-label="بستن"
        className="opacity-60 hover:opacity-100 transition-opacity text-lg leading-none px-1">
        ×
      </button>
    </div>
  )
}
