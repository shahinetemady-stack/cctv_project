import SiteBackground from './SiteBackground'
import ExchangeRateWidget from './ExchangeRateWidget'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useEffect as useEffectReact, useState, useRef, lazy, Suspense, startTransition } from 'react'
import { useQuery } from '@tanstack/react-query'
import Header from './Header'
import Footer from './Footer'
import useAuthStore from '../../store/useAuthStore'
import useCartStore from '../../store/useCartStore'
import api from '../../services/api'
import { filterAdminMenu } from '../../config/adminMenu'
import MenuBadge from './MenuBadge'
import OrderNotifier from './OrderNotifier'
import BackToTop from './BackToTop'
import AppBadge from '../AppBadge'
import InstallPrompt from './InstallPrompt'
// چت‌بات با تأخیر و به‌صورت چانک جدا لود می‌شود تا لود اولیه سبک بماند
const ChatWidget = lazy(() => import('../ChatWidget'))

// فوتر سنگین و همیشه زیر اسکرول است — فقط وقتی نزدیک ویوپورت شود mount می‌شود تا
// رندر/استایل آن وارد پنجره بوت اولیه نشود
function LazyFooter() {
  const ref = useRef(null)
  const [near, setNear] = useState(false)
  useEffectReact(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { startTransition(() => setNear(true)); obs.disconnect() }
    }, { rootMargin: '500px' })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return <div ref={ref}>{near ? <Footer /> : null}</div>
}

// چت‌بات بعد از لود کامل صفحه و idle مرورگر mount می‌شود — چانک سنگین آن نباید
// پنجره تعامل‌پذیری اولیه (TTI) را طولانی کند
function LazyChat() {
  const [ready, setReady] = useState(false)
  useEffectReact(() => {
    let idleId, cancelled = false
    const cb = () => { if (!cancelled) setReady(true) }
    const schedule = () => {
      idleId = window.requestIdleCallback
        ? window.requestIdleCallback(cb, { timeout: 8000 })
        : setTimeout(cb, 5000)
    }
    if (document.readyState === 'complete') schedule()
    else window.addEventListener('load', schedule, { once: true })
    return () => {
      cancelled = true
      window.removeEventListener('load', schedule)
      if (window.cancelIdleCallback) cancelIdleCallback(idleId)
    }
  }, [])
  if (!ready) return null
  return <Suspense fallback={null}><ChatWidget /></Suspense>
}

// ─── آیتم تکی منوی ادمین (مشترک سایدبار و کشوی موبایل) ───────
function AdminMenuLink({ item, location, onClick, indent }) {
  const isActive = location.pathname === item.path ||
    (item.path !== '/' && location.pathname.startsWith(item.path))
  return (
    <Link to={item.path} onClick={onClick}
      style={{
        color: isActive ? 'var(--color-brand)' : 'var(--color-text-secondary)',
        background: isActive ? 'rgba(251,192,45,0.1)' : 'transparent',
        borderRight: isActive ? '2px solid var(--color-brand)' : '2px solid transparent',
        paddingRight: indent ? '2rem' : undefined,
      }}
      className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-all hover:text-current">
      <span className="text-base">{item.icon}</span>
      <span className="text-xs">{item.label}</span>
      {item.badgeKey && <MenuBadge badgeKey={item.badgeKey} />}
    </Link>
  )
}

// ─── گروه تاشو (مثل «پنل ادمین») ─────────────────────────────
function AdminMenuGroup({ item, location, onChildClick, linkClassName }) {
  const hasActiveChild = item.children.some(c => location.pathname.startsWith(c.path))
  const [open, setOpen] = useState(hasActiveChild)
  return (
    <div>
      <button onClick={() => setOpen(o => !o)}
        style={{ color: hasActiveChild ? 'var(--color-brand)' : 'var(--color-text-secondary)' }}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-all hover:text-current">
        <span className="text-base">{item.icon}</span>
        <span className="text-xs flex-1 text-right">{item.label}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>
      {open && item.children.map(child => (
        <AdminMenuLink key={child.path} item={child} location={location}
          onClick={onChildClick} indent />
      ))}
    </div>
  )
}

function AdminSidebar() {
  const location = useLocation()
  const { user } = useAuthStore()

  // ارتفاع واقعی هدر چسبان (ردیف اصلی h-16 + ناوبری دسکتاپ h-11 + بوردر) را می‌سنجیم.
  // سایدبار ارتفاع ثابت و اسکرول داخلی ندارد؛ به‌جایش sticky دوحالته است:
  //  - محتوای کوتاه → زیر هدر می‌چسبد
  //  - محتوای بلند (باز شدن منوهای کشویی) → لبه پایینی‌اش به پایین ویوپورت می‌چسبد
  //    و با اسکرول صفحه حرکت می‌کند؛ یعنی باز شدن منو هیچ چیزی را به بالا نمی‌برد.
  const [stickTop, setStickTop] = useState(109)
  const asideRef = useRef(null)
  useEffectReact(() => {
    const el = asideRef.current
    if (!el) return
    const update = () => {
      const headerH = document.querySelector('header')?.offsetHeight || 109
      const S = el.scrollHeight
      const vh = window.innerHeight
      const wrapper = el.parentElement
      if (headerH + S <= vh) {
        // محتوای کوتاه — سایدبار زیر هدر می‌چسبد
        setStickTop(headerH)
        if (wrapper) wrapper.style.minHeight = ''
      } else {
        // محتوای بلند — لبه پایین سایدبار به پایین ویوپورت می‌چسبد و با اسکرول
        // صفحه بالا/پایین می‌آید؛ برای چسبیدن، کانتینر باید حداقل به بلندی سایدبار باشد
        setStickTop(vh - S)
        if (wrapper) wrapper.style.minHeight = `${S + 8}px`
      }
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    window.addEventListener('resize', update)
    return () => { ro.disconnect(); window.removeEventListener('resize', update) }
  }, [])

  const { data: permsData } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/accounting/my-permissions/').then(r => r.data),
    staleTime: 60000,
    enabled: !!user?.is_staff,
  })

  const perms = permsData?.permissions || []
  const isSuperuser = permsData?.is_superuser || user?.is_superuser || false
  const roleName = permsData?.role || 'ادمین'

  const visibleMenu = filterAdminMenu(perms, isSuperuser)

  return (
    <aside
      ref={asideRef}
      className="w-48 flex-shrink-0 sticky self-start hidden md:block"
      style={{
        top: stickTop,
        background: 'var(--color-bg-secondary)',
        borderLeft: '1px solid var(--color-border)',
      }}>
      <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>پنل مدیریت</div>
        <div className="text-xs font-semibold mt-0.5" style={{ color: 'var(--color-brand)' }}>{roleName}</div>
        <ExchangeRateWidget />
      </div>
      <nav className="py-2">
        {visibleMenu.map(item => (
          item.children ? (
            <AdminMenuGroup key={item.label} item={item} location={location} />
          ) : (
            <AdminMenuLink key={item.path} item={item} location={location} />
          )
        ))}
      </nav>
      <div className="mt-2 py-2" style={{ borderTop: '1px solid var(--color-border)' }}>
        <Link to="/" className="flex items-center gap-2.5 px-4 py-2.5 text-xs transition-all"
          style={{ color: 'var(--color-text-secondary)' }}>
          <span>🏠</span><span>بازگشت به سایت</span>
        </Link>
      </div>
    </aside>
  )
}

// ─── Admin Mobile Drawer (موبایل) ────────────────────────────
function AdminMobileDrawer({ open, onClose, menu, roleName }) {
  const location = useLocation()
  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 99998,
          background: open ? 'rgba(0,0,0,0.6)' : 'transparent',
          pointerEvents: open ? 'auto' : 'none',
          transition: 'all 0.3s ease',
          opacity: open ? 1 : 0,
        }}
      />
      {/* Drawer Panel */}
      <div
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 99999,
          width: '280px', maxWidth: '80vw',
          paddingTop: 'env(safe-area-inset-top, 0px)',
          background: 'var(--color-bg-elevated)',
          borderRight: '1px solid var(--color-border)',
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s ease',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <div>
            <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>پنل مدیریت</div>
            <div className="text-xs font-semibold mt-0.5" style={{ color: 'var(--color-brand)' }}>{roleName}</div>
            <ExchangeRateWidget />
          </div>
          <button onClick={onClose} className="p-1" style={{ color: 'var(--color-text-muted)' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        {/* Menu Items */}
        <nav className="flex-1 overflow-y-auto py-2">
          {menu.map(item => (
            item.children ? (
              <AdminMenuGroup key={item.label} item={item} location={location}
                onChildClick={onClose} />
            ) : (
              <AdminMenuLink key={item.path} item={item} location={location}
                onClick={onClose} />
            )
          ))}
        </nav>
        {/* Footer */}
        <div className="py-2" style={{ borderTop: '1px solid var(--color-border)' }}>
          <Link to="/" onClick={onClose}
            className="flex items-center gap-2.5 px-4 py-2.5 text-xs transition-all"
            style={{ color: 'var(--color-text-secondary)' }}>
            <span>🏠</span><span>بازگشت به سایت</span>
          </Link>
        </div>
      </div>
    </>
  )
}

// ─── Bottom Navigation (Mobile only) ─────────────────────────
function BottomNav({ onOpenAdminMenu }) {
  const location = useLocation()
  const { user } = useAuthStore()
  const { count: itemCount } = useCartStore()
  const isStaff = user?.is_staff || user?.profile?.user_type === 'staff' || user?.is_superuser || false

  // ─── افکت Limelight (اقتباس از 21st.dev): نوار نور متحرک بالای آیتم فعال ───
  const itemRefs = useRef([])
  const [lightX, setLightX] = useState(null)
  const items = [
    {
      to: '/',
      label: 'خانه',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      ),
      match: (p) => p === '/',
    },
    {
      to: '/products',
      label: 'محصولات',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" rx="1"/>
          <rect x="14" y="3" width="7" height="7" rx="1"/>
          <rect x="3" y="14" width="7" height="7" rx="1"/>
          <rect x="14" y="14" width="7" height="7" rx="1"/>
        </svg>
      ),
      match: (p) => p.startsWith('/products') || p.startsWith('/packages'),
    },
    {
      to: '/blog',
      label: 'بلاگ',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
      ),
      match: (p) => p.startsWith('/blog') || p.startsWith('/videos'),
    },
    {
      to: user?.is_partner ? '/inquiry-cart' : '/cart',
      label: 'سبد',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="9" cy="21" r="1"/>
          <circle cx="20" cy="21" r="1"/>
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
        </svg>
      ),
      match: (p) => p.startsWith('/cart') || p.startsWith('/inquiry-cart'),
      badge: itemCount > 0 ? itemCount : null,
    },
    {
      to: user ? (isStaff ? '/admin/dashboard' : '/account') : '/auth/login',
      label: user ? (isStaff ? 'منو' : 'حساب') : 'ورود',
      icon: user ? (
        isStaff ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12h18M3 6h18M3 18h18"/>
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        )
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
          <polyline points="10 17 15 12 10 7"/>
          <line x1="15" y1="12" x2="3" y2="12"/>
        </svg>
      ),
      match: (p) => p.startsWith('/account') || p.startsWith('/admin') || p.startsWith('/auth'),
      onClick: isStaff ? onOpenAdminMenu : undefined,
    },
  ]

  const activeIndex = items.findIndex(it => it.match(location.pathname))

  // موقعیت نوار نور زیر آیتم فعال — با transform (بدون layout thrash)
  useEffectReact(() => {
    const update = () => {
      const el = itemRefs.current[activeIndex]
      setLightX(el ? el.offsetLeft + el.offsetWidth / 2 : null)
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [activeIndex, itemCount])

  return (
    <nav className="bottom-nav pb-safe" aria-label="ناوبری موبایل" style={{ position: 'sticky', bottom: 0, zIndex: 60 }}>
      <div className="bottom-nav-inner">
        {/* نوار نور Limelight — به آیتم فعال حرکت می‌کند */}
        <div
          aria-hidden="true"
          className={`bottom-nav-limelight${lightX != null ? ' ready' : ''}`}
          style={{ transform: lightX != null ? `translateX(calc(${lightX}px - 50%))` : 'translateX(-999px)' }}
        >
          <div className="bottom-nav-limelight-cone" />
        </div>
        {items.map((item, i) => {
          const isActive = item.match(location.pathname)
          return (
            <Link
              key={item.label}
              to={item.to}
              ref={(el) => { itemRefs.current[i] = el }}
              className={`bottom-nav-item ${isActive ? 'active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              onClick={(e) => {
                if (item.onClick) {
                  e.preventDefault()
                  item.onClick()
                }
              }}
            >
              <span style={{ position: 'relative' }}>
                {item.icon}
                {item.badge != null && (
                  <span className="bottom-nav-badge">{item.badge}</span>
                )}
              </span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export default function Layout() {
  const { user } = useAuthStore()
  const location = useLocation()
  const [adminDrawerOpen, setAdminDrawerOpen] = useState(false)

  useEffectReact(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [location.pathname])

  // بازدارنده دانلود تصاویر برای بازدیدکننده — راست‌کلیک روی عکس‌ها منو نمی‌دهد
  // (حفاظت کامل ممکن نیست؛ این فقط جلوی ذخیره ساده را می‌گیرد)
  useEffectReact(() => {
    const block = (e) => { if (e.target?.tagName === 'IMG') e.preventDefault() }
    document.addEventListener('contextmenu', block)
    return () => document.removeEventListener('contextmenu', block)
  }, [])

  const isAdminPage = location.pathname.startsWith('/admin')
  const isStaff = user?.is_staff || user?.profile?.user_type === 'staff' || user?.is_superuser || false
  const showSidebar = isStaff && isAdminPage
  // BottomNav shows on ALL pages (both customer and admin)
  const showBottomNav = true

  // Get permissions for mobile drawer — enabled for ANY staff-like user
  const { data: permsData } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/accounting/my-permissions/').then(r => r.data),
    staleTime: 60000,
    enabled: isStaff,
    retry: 1,
  })
  const perms = permsData?.permissions || user?.staff_role?.permissions || []
  const isSuperuser = permsData?.is_superuser || user?.is_superuser || false
  const roleName = permsData?.role || user?.staff_role?.role_name || 'ادمین'
  // فیلتر منوها بر اساس superuserOnly و کد دسترسی (perm) — شامل گروه‌های تاشو
  const visibleMenu = filterAdminMenu(perms, isSuperuser)

  return (
    <>
      <SiteBackground />
      <div className="min-h-screen flex flex-col">
        <Header />
        <div className="flex flex-1">
          {showSidebar && <AdminSidebar />}
          <main className="flex-1 min-w-0">
            <Outlet />
          </main>
        </div>
        <LazyFooter />
        <BottomNav onOpenAdminMenu={() => setAdminDrawerOpen(true)} />
      </div>
      {/* اعلان لحظه‌ای سفارش/فیش جدید برای پرسنل */}
      {isStaff && <OrderNotifier />}
      {/* چت‌بات دستیار هوشمند + گفتگو با پرسنل — همه صفحات؛ بعد از idle لود می‌شود */}
      <LazyChat />
      {/* نشان تعداد پیام خوانده‌نشده روی آیکون وب‌اپ نصب‌شده (PWA) */}
      <AppBadge />
      {/* دکمه شناور بازگشت به بالای صفحه — همه صفحات */}
      <BackToTop />
      {/* بنر پیشنهاد نصب وب‌اپ — فقط صفحات عمومی سایت */}
      {!isAdminPage && <InstallPrompt />}
      {/* Mobile Admin Drawer — از طریق دکمه «منو» در ناوبری پایین باز می‌شود */}
      {isStaff && (
        <AdminMobileDrawer
          open={adminDrawerOpen}
          onClose={() => setAdminDrawerOpen(false)}
          menu={visibleMenu}
          roleName={roleName}
        />
      )}
    </>
  )
}
