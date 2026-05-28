import GalaxyBackground from './GalaxyBackground'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useEffect as useEffectReact } from 'react'
import { useQuery } from '@tanstack/react-query'
import Header from './Header'
import Footer from './Footer'
import useThemeStore from '../../store/useThemeStore'
import useAuthStore from '../../store/useAuthStore'
import api from '../../services/api'

const ADMIN_MENU = [
  { label: 'داشبورد',        path: '/admin/dashboard', perm: 'dashboard_view', icon: '📊' },
  { label: 'سفارشات',          path: '/admin/orders-management', perm: 'sale_view',      icon: '🛍️' },
  { label: 'فاکتور فروش',    path: '/admin/sales',     perm: 'sale_view',      icon: '🧾' },
  { label: 'کاردکس موجودی', path: '/admin/kardex',    perm: 'kardex_view',    icon: '📦' },
  { label: 'فاکتور خرید',    path: '/admin/purchases', perm: 'purchase_view',  icon: '🛒' },
  { label: 'طرف حساب‌ها',    path: '/admin/contacts',  perm: 'contacts_view',  icon: '👥' },
  { label: 'دریافت و پرداخت', path: '/admin/payments', perm: 'reports_view',  icon: '💰' },
  { label: 'گزارش مالی پیشرفته', path: '/admin/financial', perm: 'reports_view', icon: '📈' },
  { label: 'تراز حساب‌ها',   path: '/admin/reports',   perm: 'balance_view',   icon: '⚖️' },
  { label: 'آپلود Excel',        path: '/admin/bulk-upload', perm: 'products_edit', icon: '📊' },
  { label: 'نقش‌ها و پرسنل', path: '/admin/roles',     perm: 'users_edit',     icon: '🎭' },
  { label: 'محصولات',        path: '/products',        perm: 'products_view',  icon: '📷' },
]

function AdminSidebar() {
  const location = useLocation()
  const { user } = useAuthStore()

  const { data: permsData } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/accounting/my-permissions/').then(r => r.data),
    staleTime: 60000,
    enabled: !!user?.is_staff,
  })

  const perms = permsData?.permissions || []
  const isSuperuser = permsData?.is_superuser || user?.is_superuser || false
  const roleName = permsData?.role || 'ادمین'

  const visibleMenu = ADMIN_MENU.filter(item =>
    isSuperuser || perms.includes(item.perm)
  )

  return (
    <>
    <GalaxyBackground />
    <div className="w-48 flex-shrink-0 sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto"
      style={{ background: 'rgba(10,14,26,0.8)', borderLeft: '1px solid rgba(255,255,255,0.06)' }}>
      <div className="px-4 py-3 border-b border-white/5">
        <div className="text-xs text-gray-steel">پنل مدیریت</div>
        <div className="text-xs font-semibold text-brand mt-0.5">{roleName}</div>
      </div>
      <nav className="py-2">
        {visibleMenu.map(item => {
          const isActive = location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path))
          return (
            <Link key={item.path} to={item.path}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-sm transition-all ${
                isActive
                  ? 'bg-brand/15 text-brand border-l-2 border-brand'
                  : 'text-gray-steel hover:text-white hover:bg-white/5'
              }`}>
              <span className="text-base">{item.icon}</span>
              <span className="text-xs">{item.label}</span>
            </Link>
          )
        })}
      </nav>
      <div className="border-t border-white/5 mt-2 py-2">
        <Link to="/" className="flex items-center gap-2.5 px-4 py-2.5 text-xs text-gray-steel hover:text-white hover:bg-white/5 transition-all">
          <span>🏠</span><span>بازگشت به سایت</span>
        </Link>
      </div>
    </div>
    </>
  )
}

export default function Layout() {
  const { init } = useThemeStore()
  const { user } = useAuthStore()
  const location = useLocation()

  useEffectReact(() => init(), [])

  // scroll to top on route change
  useEffectReact(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [location.pathname])

  const isAdminPage = location.pathname.startsWith('/admin')
  const isStaff = user?.is_staff || false
  const showSidebar = isStaff && isAdminPage

  return (
    <>
    <GalaxyBackground />
    <div className="min-h-screen flex flex-col">
      <Header />
      <div className="flex flex-1">
        {showSidebar && <AdminSidebar />}
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
      {!showSidebar && <Footer />}
    </div>
    </>
  )
}
