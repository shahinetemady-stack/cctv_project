import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence, useScroll, useMotionValueEvent } from 'framer-motion'
import useAuthStore from '../../store/useAuthStore'
import useCartStore from '../../store/useCartStore'
import useCompareStore from '../../store/useCompareStore'
import api from '../../services/api'
import { filterAdminMenu } from '../../config/adminMenu'
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
} from './header/icons'

const SPRING_SNAPPY = { type: 'spring', stiffness: 500, damping: 35 }
const SPRING_GENTLE = { type: 'spring', stiffness: 200, damping: 25 }
const SPRING_BOUNCE = { type: 'spring', stiffness: 400, damping: 17 }

// دکمه آیکونی مشترک هدر
const iconBtn =
  'w-10 h-10 rounded-xl flex items-center justify-center text-[var(--color-text-secondary)] hover:text-gold hover:bg-white/5 transition-colors'

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

  const { scrollY } = useScroll()
  useMotionValueEvent(scrollY, 'change', (v) => setScrolled(v > 8))

  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then((r) => r.data),
    staleTime: 0,
  })

  // ─── دسترسی‌ها برای منوی ادمین (موبایل) ───
  const { data: permsData } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/accounting/my-permissions/').then((r) => r.data),
    staleTime: 60000,
    enabled: !!user?.is_staff,
    retry: 1,
  })
  const isSuperuser = permsData?.is_superuser || user?.is_superuser || false
  const perms = permsData?.permissions || []
  // منوی کاشی‌ای موبایل لینک‌های flat می‌خواهد — گروه‌های تاشو باز می‌شوند
  const visibleAdminMenu = filterAdminMenu(perms, isSuperuser)
    .flatMap((item) => (item.children ? item.children : [item]))

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
      <AnimatePresence>
        {showLogoUpload && (
          <LogoUploadModal
            onClose={() => setShowLogoUpload(false)}
            onUploaded={(url) => console.log('Logo uploaded:', url)}
          />
        )}
      </AnimatePresence>

      {/* نوار اطلاع‌رسانی */}
      <TopBar settings={settings} />

      {/* دراور موبایل */}
      <MobileMenu
        menuOpen={mobileMenuOpen}
        onCloseMenu={() => setMobileMenuOpen(false)}
        user={user}
        isStaff={isStaff}
        adminMenu={visibleAdminMenu}
        onLogout={handleLogout}
      />

      {/* ─── نوار هدر ─────────────────────────────────────────── */}
      <motion.header
        className={`sticky top-0 z-50 glass pt-safe transition-shadow ${
          scrolled ? 'shadow-[var(--shadow-header)]' : ''
        }`}
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={SPRING_GENTLE}
      >
        <div className="container-site flex items-center gap-2 h-16 relative">
          {/* منوی همبرگری (موبایل) */}
          <motion.button
            onClick={() => setMobileMenuOpen(true)}
            className={`${iconBtn} md:hidden`}
            aria-label="منو"
            whileTap={{ scale: 0.92 }}
            transition={SPRING_SNAPPY}
          >
            <MenuIcon />
          </motion.button>

          {/* لوگو */}
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} transition={SPRING_SNAPPY}>
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
                  <motion.div
                    whileHover={{ rotate: -8, scale: 1.05 }}
                    transition={SPRING_SNAPPY}
                    className="w-9 h-9 rounded-xl flex items-center justify-center"
                    style={{ background: 'var(--gradient-gold)', boxShadow: 'var(--shadow-gold)' }}
                  >
                    <CameraIcon style={{ color: 'var(--color-brand-contrast)' }} />
                  </motion.div>
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
          </motion.div>

          {/* دکمه‌های سمت چپ */}
          <div className="flex items-center gap-1 md:gap-1.5 flex-shrink-0 mr-auto">
            {/* سوشیال مدیا (دسکتاپ) — با رنگ رسمی هر برند، هم‌سبک فوتر */}
            <div className="hidden lg:flex items-center gap-1.5">
              {settings?.whatsapp_number && (
                <motion.a
                  href={`https://wa.me/${settings.whatsapp_number.replace(/[^0-9]/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="واتساپ"
                  className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:scale-110"
                  style={{ background: '#25D36620', color: '#25D366', border: '1px solid #25D36640' }}
                  whileTap={{ scale: 0.92 }}
                >
                  <WhatsAppIcon />
                </motion.a>
              )}
              {settings?.instagram_username && (
                <motion.a
                  href={`https://instagram.com/${settings.instagram_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="اینستاگرام"
                  className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:scale-110"
                  style={{ background: '#E1306C20', color: '#E1306C', border: '1px solid #E1306C40' }}
                  whileTap={{ scale: 0.92 }}
                >
                  <InstagramIcon />
                </motion.a>
              )}
              {settings?.bale_username && (
                <motion.a
                  href={`https://ble.ir/${settings.bale_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="بله"
                  className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:scale-110 text-[10px] font-bold"
                  style={{ background: '#0088cc20', color: '#0088cc', border: '1px solid #0088cc40' }}
                  whileTap={{ scale: 0.92 }}
                >
                  بله
                </motion.a>
              )}
            </div>

            {/* دکمه پنل مدیریت (موبایل) */}
            {isStaff && (
              <motion.div whileTap={{ scale: 0.92 }} transition={SPRING_SNAPPY}>
                <Link to="/admin/dashboard" className={`${iconBtn} md:hidden`} title="پنل مدیریت">
                  <GridIcon />
                </Link>
              </motion.div>
            )}

            {/* تعویض تم دارک/لایت */}
            <ThemeToggle className={iconBtn} />

            {/* مقایسه محصولات */}
            <motion.div whileTap={{ scale: 0.92 }} transition={SPRING_SNAPPY} className="relative">
              <Link to="/compare" className={`${iconBtn} relative`} aria-label="مقایسه محصولات" title="مقایسه محصولات">
                <span className="text-lg leading-none">⚖</span>
                <AnimatePresence>
                  {compareCount > 0 && (
                    <motion.span
                      key={compareCount}
                      initial={{ scale: 0, rotate: -45 }}
                      animate={{ scale: 1, rotate: 0 }}
                      exit={{ scale: 0, rotate: 45 }}
                      transition={SPRING_BOUNCE}
                      className="absolute -top-0.5 -left-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center"
                      style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
                    >
                      {compareCount}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            </motion.div>

            {/* سبد خرید */}
            <motion.div whileTap={{ scale: 0.92 }} transition={SPRING_SNAPPY} className="relative">
              <Link to={isPartnerUser ? '/inquiry-cart' : '/cart'} className={`${iconBtn} relative`} aria-label="سبد خرید">
                <CartIcon />
                <AnimatePresence>
                  {itemCount > 0 && (
                    <motion.span
                      key={itemCount}
                      initial={{ scale: 0, rotate: -45 }}
                      animate={{ scale: 1, rotate: 0 }}
                      exit={{ scale: 0, rotate: 45 }}
                      transition={SPRING_BOUNCE}
                      className="absolute -top-0.5 -left-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center"
                      style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
                    >
                      {itemCount}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            </motion.div>

            {/* کاربر (دسکتاپ) */}
            <div className="hidden md:flex items-center gap-2">
              <UserMenu user={user} isStaff={isStaff} onLogout={handleLogout} />
            </div>

            {/* ورود (موبایل، حالت مهمان) */}
            {!user && (
              <motion.div whileTap={{ scale: 0.92 }} transition={SPRING_SNAPPY}>
                <Link to="/auth/login" className={`${iconBtn} md:hidden`} aria-label="ورود">
                  <UserIcon />
                </Link>
              </motion.div>
            )}
          </div>
        </div>

        {/* ناوبری دسکتاپ + مگامنو */}
        <MainNav />
      </motion.header>
    </>
  )
}
