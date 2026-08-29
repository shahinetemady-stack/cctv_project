// بررسی دسترسی‌های کاربر جاری بر اساس کدهای permission بک‌اند
// can(code) → برای سوپریوزر همیشه true — کوئری ['my-permissions'] کش می‌شود
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

export default function usePermissions() {
  const { data } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/accounting/my-permissions/').then(r => r.data),
    staleTime: 60000,
    retry: 1,
  })
  const can = (code) => !!data?.is_superuser || !!data?.permissions?.includes(code)
  return {
    can,
    isSuperuser: !!data?.is_superuser,
    permissions: data?.permissions || [],
    // نوع‌های مجاز طرف حساب — [] یعنی بدون محدودیت (همه نوع‌ها)
    allowedContactTypes: data?.allowed_contact_types || [],
    // نوع‌های قابل ساخت — null = بدون محدودیت (سوپریوزر) | [] = ساخت هیچ نوعی مجاز نیست
    creatableContactTypes: data?.is_superuser ? null : (data?.creatable_contact_types || []),
  }
}
