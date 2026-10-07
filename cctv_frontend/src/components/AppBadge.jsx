// نشان تعداد پیام‌های خوانده‌نشده روی آیکون وب‌اپ نصب‌شده (PWA / Add to Home Screen)
// Badging API — فقط روی وب‌اپ نصب‌شده اثر دارد و در مرورگر عادی بی‌خطر no-op است.
// از همان کوئری‌های موجود (chat-unread و admin-badges) استفاده می‌کند — درخواست اضافه ندارد.
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import useAuthStore from '../store/useAuthStore'

export default function AppBadge() {
  const user = useAuthStore(s => s.user)
  const isAdmin = useAuthStore(s => s.isAdmin)
  const isStaff = !!user && isAdmin()

  // خوانده‌نشده‌های گفتگوی خود کاربر (مشتری/پرسنل به‌عنوان فرد)
  const { data: mine } = useQuery({
    queryKey: ['chat-unread'],
    queryFn: () => api.get('/chat/mine/unread/').then(r => r.data),
    refetchInterval: 60000,
    enabled: !!user,
  })
  // خوانده‌نشده‌های چت‌های در انتظار پاسخ پرسنل — همان کوئری MenuBadge (کش مشترک)
  const { data: badges } = useQuery({
    queryKey: ['admin-badges'],
    queryFn: () => api.get('/users/admin-badges/').then(r => r.data),
    refetchInterval: 15000,
    enabled: isStaff,
  })

  const total = (mine?.unread || 0) + (isStaff ? (badges?.chat_unread || 0) : 0)

  useEffect(() => {
    if (!('setAppBadge' in navigator)) return
    try {
      const p = total > 0 ? navigator.setAppBadge(total) : navigator.clearAppBadge()
      p?.catch?.(() => {})
    } catch { /* مرورگرهای قدیمی — بی‌خطر نادیده گرفته می‌شود */ }
  }, [total])

  return null
}
