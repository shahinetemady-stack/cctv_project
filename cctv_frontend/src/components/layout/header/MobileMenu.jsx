import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { navGroups, isActivePath } from './navGroups'
import { catalogService } from '../../../services/catalog'
import { CloseIcon } from './icons'

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
      {/* رندر شرطی + انیمیشن ورود CSS — بدون انیمیشن خروج تا با ناوبری گیر نکند */}
      {menuOpen && (
        <div className="fixed inset-0 z-[70] md:hidden animate-fade-in-fast">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-md"
            onClick={onCloseMenu}
          />
          <div
            className="absolute top-0 right-0 bottom-0 w-[88%] max-w-sm overflow-y-auto pt-safe pb-24 border-l border-[var(--color-border)] animate-drawer-in"
            style={{
              background: 'linear-gradient(180deg, #161618 0%, #0C0C0E 100%)',
              boxShadow: '-20px 0 60px -20px rgba(0,0,0,0.6)',
            }}
          >
            {/* کارت کاربر */}
            <div className="relative p-4 border-b border-[var(--color-border)] overflow-hidden animate-slide-down-sm">
                <div
                  aria-hidden="true"
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    background:
                      'radial-gradient(300px circle at 85% 0%, rgba(251,192,45,0.12), transparent 60%)',
                  }}
                />
                <div className="relative flex items-center gap-3">
                  <div
                    className="h-11 px-3 rounded-2xl flex items-center justify-center text-sm font-bold flex-shrink-0 max-w-[150px] truncate transition-transform active:scale-[0.94]"
                    style={{
                      background: 'var(--gradient-gold)',
                      color: 'var(--color-brand-contrast)',
                      boxShadow: 'var(--shadow-gold)',
                    }}
                  >
                    {user ? displayName(user) : 'G'}
                  </div>
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
                  <button
                    onClick={onCloseMenu}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--color-text-muted)] hover:text-gold hover:bg-white/5 transition-all active:scale-[0.92] active:rotate-90"
                    aria-label="بستن"
                  >
                    <CloseIcon />
                  </button>
                </div>
            </div>

            {/* گروه‌های ناوبری */}
            <div className="flex-1 px-3 py-3 space-y-4">
              {groups.map((group, groupIdx) => (
                <div key={group.id} className="animate-fade-up-sm" style={{ animationDelay: `${0.04 + groupIdx * 0.05}s` }}>
                    <div className="flex items-center gap-2 px-2 mb-1.5 text-[11px] font-bold text-[var(--color-text-muted)]">
                      <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
                      {group.label}
                    </div>
                    <div className="space-y-1">
                      {group.items.map((item) => (
                        <div key={item.href} className="transition-transform active:scale-[0.98]">
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
                        </div>
                      ))}
                    </div>
                </div>
              ))}

              {/* گروه: حساب کاربری */}
              <div className="animate-fade-up-sm" style={{ animationDelay: `${0.04 + (groups.length + 1) * 0.05}s` }}>
                  <div className="flex items-center gap-2 px-2 mb-1.5 text-[11px] font-bold text-[var(--color-text-muted)]">
                    <span className="w-1 h-3 rounded-full bg-[var(--color-text-muted)]" />
                    حساب کاربری
                  </div>
                  {user ? (
                    <>
                      <div className="transition-transform active:scale-[0.98]">
                        <Link
                          to="/account"
                          onClick={onCloseMenu}
                          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] text-[var(--color-text-secondary)] hover:bg-white/5 hover:text-[var(--color-text-primary)] transition-colors"
                        >
                          <span className="text-base w-6 text-center">👤</span>
                          <span className="flex-1">پروفایل من</span>
                        </Link>
                      </div>
                      <button
                        onClick={onLogout}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] w-full text-right text-alert-red hover:bg-[rgba(248,113,113,0.08)] transition-all active:scale-[0.98]"
                      >
                        <span className="text-base w-6 text-center">🚪</span>
                        <span className="flex-1">خروج از حساب</span>
                      </button>
                    </>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div className="transition-transform active:scale-[0.97]">
                        <Link
                          to="/auth/login"
                          onClick={onCloseMenu}
                          className="btn-ghost w-full text-xs"
                        >
                          ورود
                        </Link>
                      </div>
                      <div className="transition-transform active:scale-[0.97]">
                        <Link
                          to="/auth/register"
                          onClick={onCloseMenu}
                          className="btn-gold w-full text-xs"
                        >
                          ثبت‌نام
                        </Link>
                      </div>
                    </div>
                  )}
              </div>

              <div className="pt-2 animate-fade-up-sm" style={{ animationDelay: `${0.04 + (groups.length + 2) * 0.05}s` }}>
                <div className="text-[10px] text-[var(--color-text-muted)] text-center">
                  © {new Date().getFullYear()} — قطعات دوربین
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
