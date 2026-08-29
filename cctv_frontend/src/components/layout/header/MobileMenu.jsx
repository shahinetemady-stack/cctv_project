import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { navGroups, isActivePath } from './navGroups'
import { catalogService } from '../../../services/catalog'
import { CloseIcon, GridIcon } from './icons'

const SPRING_SNAPPY = { type: 'spring', stiffness: 500, damping: 35 }
const SPRING_SMOOTH = { type: 'spring', stiffness: 300, damping: 30 }

// برچسب نوع عضویت کاربر — زیر شماره/نام در منو
const TIER_LABELS = { silver: 'همکار سیلور', gold: 'همکار گلد', platinum: 'همکار پلاتینیوم' }
function membershipLabel(user) {
  const p = user?.profile
  if (p?.user_type === 'partner') {
    if (!p.is_approved) return 'همکار (در انتظار تأیید)'
    return TIER_LABELS[p.partner_tier] || 'همکار'
  }
  return 'مشتری عمومی'
}

// نام نمایشی مشتری — نام و نام خانوادگی، وگرنه شماره موبایل (مثل UserMenu دسکتاپ)
function displayName(user) {
  const full = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return full || user?.username || user?.phone || ''
}

const slideRight = {
  hidden: { x: '100%' },
  visible: { x: 0, transition: SPRING_SMOOTH },
  exit: { x: '100%', transition: { duration: 0.22, ease: [0.32, 0.72, 0, 1] } },
}
const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } },
  exit: {},
}
const itemFadeUp = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: SPRING_SMOOTH },
  exit: { opacity: 0, transition: { duration: 0.15 } },
}

const CATEGORY_TYPE_ICON = {
  board: '📟',
  lens: '🔭',
  modem: '📡',
  housing: '📦',
  other: '🔧',
}

// ─── دراور موبایل ─────────────────────────────────────────────
export default function MobileMenu({
  menuOpen,
  onCloseMenu,
  user,
  isStaff,
  adminMenu,
  onLogout,
}) {
  const location = useLocation()
  const isActive = (href) => isActivePath(location.pathname, href)

  const { data: categoriesData } = useQuery({
    queryKey: ['nav-categories'],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  })

  const categories = categoriesData?.results || []

  const shopGroup = {
    id: 'shop',
    label: 'فروشگاه',
    items: [
      { label: 'همه محصولات', href: '/products', icon: '📦' },
      { label: 'پکیج‌ها', href: '/packages', icon: '🎁' },
      ...categories.map((cat) => ({
        label: cat.name,
        href: `/categories/${cat.slug}`,
        icon: CATEGORY_TYPE_ICON[cat.category_type] || CATEGORY_TYPE_ICON.other,
      })),
    ],
  }

  const groups = [shopGroup, ...navGroups.filter((g) => g.id !== 'shop')]

  return (
    <>
      {/* ─── دراور منو (اسلاید از راست) ───────────────────────── */}
      {/* key بر اساس مسیر: با ناوبری، دراور فوراً آن‌مانت می‌شود و باز نمی‌ماند */}
      <AnimatePresence key={location.pathname}>
        {menuOpen && (
          <motion.div
            className="fixed inset-0 z-[70] md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <motion.div
              className="absolute inset-0 bg-black/70 backdrop-blur-md"
              onClick={onCloseMenu}
            />
            <motion.div
              className="absolute top-0 right-0 bottom-0 w-[88%] max-w-sm overflow-y-auto pt-safe pb-24 border-l border-[var(--color-border)]"
              variants={slideRight}
              initial="hidden"
              animate="visible"
              exit="exit"
              style={{
                background: 'linear-gradient(180deg, #161618 0%, #0C0C0E 100%)',
                boxShadow: '-20px 0 60px -20px rgba(0,0,0,0.6)',
              }}
            >
              {/* کارت کاربر */}
              <motion.div
                className="relative p-4 border-b border-[var(--color-border)] overflow-hidden"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={SPRING_SMOOTH}
              >
                <div
                  aria-hidden="true"
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background:
                      'radial-gradient(300px circle at 85% 0%, rgba(251,192,45,0.12), transparent 60%)',
                  }}
                />
                <div className="relative flex items-center gap-3">
                  <motion.div
                    whileTap={{ scale: 0.94 }}
                    className="h-11 px-3 rounded-2xl flex items-center justify-center text-sm font-bold flex-shrink-0 max-w-[150px] truncate"
                    style={{
                      background: 'var(--gradient-gold)',
                      color: 'var(--color-brand-contrast)',
                      boxShadow: 'var(--shadow-gold)',
                    }}
                  >
                    {user ? displayName(user) : 'G'}
                  </motion.div>
                  <div className="flex-1 min-w-0">
                    {user ? (
                      <>
                        <div className="text-sm font-bold text-[var(--color-text-primary)] truncate font-mono" dir="ltr">
                          {user.phone || user.username}
                        </div>
                        <div className={`text-[11px] mt-0.5 ${isStaff ? 'text-gold' : 'text-[var(--color-text-muted)]'}`}>
                          {isStaff ? '✦ کاربر ارشد' : membershipLabel(user)}
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="text-sm font-bold text-[var(--color-text-primary)]">بازدیدکننده</div>
                        <div className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                          برای دسترسی کامل وارد شوید
                        </div>
                      </>
                    )}
                  </div>
                  <motion.button
                    onClick={onCloseMenu}
                    whileTap={{ scale: 0.92, rotate: 90 }}
                    transition={SPRING_SNAPPY}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-gold hover:bg-white/5 transition-colors"
                    aria-label="بستن"
                  >
                    <CloseIcon />
                  </motion.button>
                </div>
              </motion.div>

              {/* گروه‌های ناوبری */}
              <motion.div
                className="flex-1 px-3 py-3 space-y-4"
                variants={stagger}
                initial="hidden"
                animate="visible"
              >
                {groups.map((group) => (
                  <motion.div key={group.id} variants={itemFadeUp}>
                    <div className="flex items-center gap-2 px-2 mb-1.5 text-[11px] font-bold text-[var(--color-text-muted)]">
                      <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
                      {group.label}
                    </div>
                    <div className="space-y-1">
                      {group.items.map((item) => (
                        <motion.div key={item.href} whileTap={{ scale: 0.98 }} transition={SPRING_SNAPPY}>
                          <Link
                            to={item.href}
                            onClick={onCloseMenu}
                            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] transition-colors ${
                              isActive(item.href)
                                ? 'text-gold bg-[var(--color-brand-soft)]'
                                : 'text-[var(--color-text-secondary)] hover:bg-white/5 hover:text-[var(--color-text-primary)]'
                            }`}
                          >
                            <span className="text-base w-6 text-center">{item.icon}</span>
                            <span className="flex-1">{item.label}</span>
                            {item.badge && (
                              <span className="badge badge-gold !text-[10px] !py-0.5">
                                {item.badge === 'hot' ? '🔥' : item.badge}
                              </span>
                            )}
                            {isActive(item.href) && !item.badge && (
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="15 18 9 12 15 6" />
                              </svg>
                            )}
                          </Link>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                ))}

                {/* گروه: پنل مدیریت */}
                {isStaff && (
                  <motion.div variants={itemFadeUp}>
                    <div className="flex items-center gap-2 px-2 mb-1.5 text-[11px] font-bold text-gold">
                      <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
                      <GridIcon />
                      پنل مدیریت
                    </div>
                    <motion.div
                      className="grid grid-cols-3 gap-2"
                      variants={stagger}
                      initial="hidden"
                      animate="visible"
                    >
                      {adminMenu.map((item) => (
                        <motion.div key={item.path} whileTap={{ scale: 0.96 }} transition={SPRING_SNAPPY}>
                          <Link
                            to={item.path}
                            onClick={onCloseMenu}
                            className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-center transition-colors ${
                              isActive(item.path)
                                ? 'border-[rgba(251,192,45,0.4)] bg-[var(--color-brand-soft)] text-gold'
                                : 'border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]'
                            }`}
                          >
                            <span className="text-xl">{item.icon}</span>
                            <span className="text-[10px] leading-tight">{item.label}</span>
                          </Link>
                        </motion.div>
                      ))}
                    </motion.div>
                  </motion.div>
                )}

                {/* گروه: حساب کاربری */}
                <motion.div variants={itemFadeUp}>
                  <div className="flex items-center gap-2 px-2 mb-1.5 text-[11px] font-bold text-[var(--color-text-muted)]">
                    <span className="w-1 h-3 rounded-full bg-[var(--color-text-muted)]" />
                    حساب کاربری
                  </div>
                  {user ? (
                    <>
                      <motion.div whileTap={{ scale: 0.98 }} transition={SPRING_SNAPPY}>
                        <Link
                          to="/account"
                          onClick={onCloseMenu}
                          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] text-[var(--color-text-secondary)] hover:bg-white/5 hover:text-[var(--color-text-primary)] transition-colors"
                        >
                          <span className="text-base w-6 text-center">👤</span>
                          <span className="flex-1">پروفایل من</span>
                        </Link>
                      </motion.div>
                      <motion.button
                        onClick={onLogout}
                        whileTap={{ scale: 0.98 }}
                        transition={SPRING_SNAPPY}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] w-full text-right text-alert-red hover:bg-[rgba(248,113,113,0.08)] transition-colors"
                      >
                        <span className="text-base w-6 text-center">🚪</span>
                        <span className="flex-1">خروج از حساب</span>
                      </motion.button>
                    </>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <motion.div whileTap={{ scale: 0.97 }} transition={SPRING_SNAPPY}>
                        <Link
                          to="/auth/login"
                          onClick={onCloseMenu}
                          className="btn-ghost w-full text-xs"
                        >
                          ورود
                        </Link>
                      </motion.div>
                      <motion.div whileTap={{ scale: 0.97 }} transition={SPRING_SNAPPY}>
                        <Link
                          to="/auth/register"
                          onClick={onCloseMenu}
                          className="btn-gold w-full text-xs"
                        >
                          ثبت‌نام
                        </Link>
                      </motion.div>
                    </div>
                  )}
                </motion.div>

                <motion.div variants={itemFadeUp} className="pt-2">
                  <div className="text-[10px] text-[var(--color-text-muted)] text-center">
                    © {new Date().getFullYear()} — قطعات دوربین
                  </div>
                </motion.div>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
