import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import useAuthStore from '../../store/useAuthStore'
import useCartStore from '../../store/useCartStore'
import useCompareStore from '../../store/useCompareStore'
import api from '../../services/api'
import TopBar from './header/TopBar'
import MainNav from './header/MainNav'
import UserMenu from './header/UserMenu'
import MobileMenu from './header/MobileMenu'
import LogoUploadModal from './header/LogoUploadModal'
import ThemeToggle from './header/ThemeToggle'
import {
  CartIcon,
  MenuIcon,
  UserIcon,
  GridIcon,
  CameraIcon,
  WhatsAppIcon,
  InstagramIcon,
  GaugeIcon,
} from './header/icons'

// دکمه آیکونی مشترک هدر — مدل Modern Header: قاب‌دار با glow طلایی روی هاور
const iconBtn =
  'w-10 h-10 rounded-xl flex items-center justify-center text-[var(--color-text-secondary)] border border-[var(--color-border)] bg-[var(--color-bg-elevated)]/70 hover:text-gold hover:border-[rgba(var(--color-brand-rgb),0.45)] hover:shadow-[0_0_16px_rgba(var(--color-brand-rgb),0.18)] transition-all'

// ─── هدر اصلی سایت ────────────────────────────────────────────
export default function Header() {
  const { user, logout } = useAuthStore()
  const { count: itemCount } = useCartStore()
  const compareCount = useCompareStore(s => s.items.length)
  const navigate = useNavigate()
  const location = useLocation()
  const [showLogoUpload, setShowLogoUpload] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const isStaff = user?.is_staff || user?.profile?.user_type === 'staff' || user?.is_superuser || false
  const isPartnerUser = user?.is_partner === true

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })

  // ─── بستن منو با تغییر مسیر ───
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  // ─── قفل اسکرول body هنگام بازبودن منوی موبایل ───
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [mobileMenuOpen])

  // ─── ESC برای بستن منو ───
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setMobileMenuOpen(false)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  async function handleLogout() {
    try {
      await api.post('/users/auth/logout/')
    } catch {}
    logout()
    navigate('/auth/login')
    setMobileMenuOpen(false)
  }

  return (
    <>
      {showLogoUpload && (
        <LogoUploadModal
          onClose={() => setShowLogoUpload(false)}
          onUploaded={(url) => console.log('Logo uploaded:', url)}
        />
      )}

      {/* نوار اطلاع‌رسانی */}
      <TopBar settings={settings} />

      {/* دراور موبایل */}
      <MobileMenu
        menuOpen={mobileMenuOpen}
        onCloseMenu={() => setMobileMenuOpen(false)}
        user={user}
        isStaff={isStaff}
        onLogout={handleLogout}
      />

      {/* ─── نوار هدر — پیل شناور (مدل Modern Header) ────────── */}
      <header
        className={`site-header pt-safe animate-header-in ${scrolled ? 'scrolled' : ''}`}
      >
        {/* خط اسکن متحرک روی لبه بالا */}
        <div className="hd-scan" aria-hidden="true" />
        <div className="container-site flex items-center gap-2 h-16 relative">
          {/* منوی همبرگری (موبایل) */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className={`${iconBtn} md:hidden transition-transform active:scale-[0.92]`}
            aria-label="منو"
          >
            <MenuIcon />
          </button>

          {/* لوگو */}
          <div className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
            <Link to="/" className="flex items-center gap-2.5 group flex-shrink-0">
              {settings?.site_logo ? (
                <div className="relative">
                  <img
                    src={settings.site_logo}
                    alt={settings?.site_name || 'logo'}
                    width={36}
                    height={36}
                    className="h-8 md:h-9 w-auto object-contain transition-transform group-hover:scale-105"
                    onError={(e) => (e.target.style.display = 'none')}
                  />
                  {isStaff && (
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        setShowLogoUpload(true)
                      }}
                      className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[8px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
                      title="تغییر لوگو"
                    >
                      ✏️
                    </button>
                  )}
                </div>
              ) : (
                <div className="relative">
                  <div
                    className="w-10 h-10 rounded-[13px] flex items-center justify-center transition-transform duration-500 group-hover:rotate-[-8deg] group-hover:scale-105"
                    style={{
                      background: 'var(--color-brand-soft)',
                      border: '1px solid rgba(var(--color-brand-rgb), 0.35)',
                      color: 'var(--color-brand)',
                      boxShadow: '0 0 22px rgba(var(--color-brand-rgb), 0.22)',
                    }}
                  >
                    <CameraIcon />
                  </div>
                  <span className="brand-dot" aria-hidden="true" />
                  {isStaff && (
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        setShowLogoUpload(true)
                      }}
                      className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[8px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
                      title="آپلود لوگو"
                    >
                      +
                    </button>
                  )}
                </div>
              )}
              <div className="flex flex-col leading-none">
                <span className="font-display font-bold text-sm text-[var(--color-text-primary)]">
                  {settings?.site_name || 'قطعات دوربین'}
                </span>
                <span className="text-[9px] text-gold font-mono tracking-widest mt-0.5 hidden sm:block">
                  CCTV PARTS
                </span>
              </div>
            </Link>
          </div>

          {/* دکمه‌های سمت چپ */}
          <div className="flex items-center gap-1 md:gap-1.5 flex-shrink-0 mr-auto">
            {/* سوشیال مدیا (دسکتاپ) — با رنگ رسمی هر برند، هم‌سبک فوتر */}
            <div className="hidden lg:flex items-center gap-1.5">
              {settings?.whatsapp_number && (
                <a
                  href={`https://wa.me/${settings.whatsapp_number.replace(/[^0-9]/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="واتساپ"
                  className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:scale-110 active:scale-[0.92]"
                  style={{ background: '#25D36620', color: '#25D366', border: '1px solid #25D36640' }}
                >
                  <WhatsAppIcon />
                </a>
              )}
              {settings?.instagram_username && (
                <a
                  href={`https://instagram.com/${settings.instagram_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="اینستاگرام"
                  className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:scale-110 active:scale-[0.92]"
                  style={{ background: '#E1306C20', color: '#E1306C', border: '1px solid #E1306C40' }}
                >
                  <InstagramIcon />
                </a>
              )}
              {settings?.bale_username && (
                <a
                  href={`https://ble.ir/${settings.bale_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="بله"
                  className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:scale-110 active:scale-[0.92] text-[10px] font-bold"
                  style={{ background: '#0088cc20', color: '#0088cc', border: '1px solid #0088cc40' }}
                >
                  بله
                </a>
              )}
            </div>

            {/* دکمه پنل مدیریت (موبایل) */}
            {isStaff && (
              <div className="transition-transform active:scale-[0.92]">
                <Link to="/admin/dashboard" className={`${iconBtn} md:hidden`} title="پنل مدیریت">
                  <GridIcon />
                </Link>
              </div>
            )}

            {/* تعویض تم دارک/لایت */}
            <ThemeToggle className={iconBtn} />

            {/* مقایسه محصولات */}
            <div className="relative transition-transform active:scale-[0.92]">
              <Link to="/compare" className={`${iconBtn} relative`} aria-label="مقایسه محصولات" title="مقایسه محصولات">
                <GaugeIcon />
                {compareCount > 0 && (
                  <span
                    key={compareCount}
                    className="animate-badge-pop absolute -top-0.5 -left-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center"
                    style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
                  >
                    {compareCount}
                  </span>
                )}
              </Link>
            </div>

            {/* سبد خرید */}
            <div className="relative transition-transform active:scale-[0.92]">
              <Link to={isPartnerUser ? '/inquiry-cart' : '/cart'} className={`${iconBtn} relative`} aria-label="سبد خرید">
                <CartIcon />
                {itemCount > 0 && (
                  <span
                    key={itemCount}
                    className="animate-badge-pop absolute -top-0.5 -left-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center"
                    style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
                  >
                    {itemCount}
                  </span>
                )}
              </Link>
            </div>

            {/* کاربر (دسکتاپ) */}
            <div className="hidden md:flex items-center gap-2">
              <UserMenu user={user} isStaff={isStaff} onLogout={handleLogout} />
            </div>

            {/* ورود (موبایل، حالت مهمان) */}
            {!user && (
              <div className="transition-transform active:scale-[0.92]">
                <Link to="/auth/login" className={`${iconBtn} md:hidden`} aria-label="ورود">
                  <UserIcon />
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* ناوبری دسکتاپ + مگامنو */}
        <MainNav />
      </header>
    </>
  )
}
