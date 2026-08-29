// بج قرمز شمارنده روی آیتم‌های منوی ادمین (سفارشات / طرف حساب‌ها)
// داده از /api/users/admin-badges/ — با react-query کش و رفرش دوره‌ای
// کلیک روی بج سفارشات → مستقیم به فیلتر «در انتظار بررسی»
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'

export default function MenuBadge({ badgeKey }) {
  const navigate = useNavigate()
  const { data } = useQuery({
    queryKey: ['admin-badges'],
    queryFn: () => api.get('/users/admin-badges/').then(r => r.data),
    refetchInterval: 15000,
    staleTime: 10000,
  })
  const n = badgeKey === 'orders' ? data?.orders_pending
    : badgeKey === 'partners' ? data?.partners_pending
    : badgeKey === 'salesDue' ? data?.sales_due
    : badgeKey === 'receipts' ? data?.receipts_pending
    : null
  if (!n) return null
  const links = {
    orders: '/admin/orders-management?status=pending',
    salesDue: '/admin/sales?due=1',
    partners: null,
    receipts: '/admin/receipts',
  }
  const link = links[badgeKey]
  return (
    <span
      onClick={link
        ? (e) => { e.preventDefault(); e.stopPropagation(); navigate(link) }
        : undefined}
      title="نیاز به رسیدگی"
      className="mr-auto min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold inline-flex items-center justify-center">
      {n > 99 ? '۹۹+' : Number(n).toLocaleString('fa-IR')}
    </span>
  )
}
