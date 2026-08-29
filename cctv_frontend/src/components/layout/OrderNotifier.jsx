// اعلان لحظه‌ای رویدادهای پنل ادمین — سفارش جدید / فیش جدید
// هر ۱۵ ثانیه admin-badges را چک می‌کند؛ اگر شمارنده زیاد شد توست نشان می‌دهد
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import api from '../../services/api'
import useAuthStore from '../../store/useAuthStore'

export default function OrderNotifier() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const prev = useRef(null)

  const { data } = useQuery({
    queryKey: ['admin-badges'],
    queryFn: () => api.get('/users/admin-badges/').then(r => r.data),
    refetchInterval: 15000,
    refetchOnWindowFocus: 'always',
    enabled: !!user?.is_staff,
  })

  useEffect(() => {
    if (!data) return
    const cur = { orders: data.orders_pending || 0, receipts: data.receipts_pending || 0 }
    if (prev.current) {
      if (cur.orders > prev.current.orders) {
        const diff = cur.orders - prev.current.orders
        toast.info(`🛒 ${diff > 1 ? `${diff.toLocaleString('fa-IR')} سفارش جدید` : 'سفارش جدید'} ثبت شد`, {
          duration: 8000,
          action: { label: 'مشاهده', onClick: () => navigate('/admin/orders-management?status=pending') },
        })
      }
      if (cur.receipts > prev.current.receipts) {
        const diff = cur.receipts - prev.current.receipts
        toast.info(`🧾 ${diff > 1 ? `${diff.toLocaleString('fa-IR')} فیش واریزی جدید` : 'فیش واریزی جدید'} ثبت شد`, {
          duration: 8000,
          action: { label: 'بررسی', onClick: () => navigate('/admin/receipts') },
        })
      }
    }
    prev.current = cur
  }, [data, navigate])

  return null
}
