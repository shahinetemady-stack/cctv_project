import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { navGroups, isActivePath } from './navGroups'
import { catalogService } from '../../../services/catalog'
import { ChevronDownIcon } from './icons'

// زیرعنوان هر گروه در ستون برند مگامنو
const GROUP_SUBTITLES = {
  shop: 'کاتالوگ کامل قطعات و پکیج‌های آماده',
  content: 'آموزش، تحلیل و راهنمای تخصصی',
  services: 'خدمات ویژه و پشتیبانی مشتریان',
}

const CATEGORY_TYPE_ICON = {
  board: '📟',
  lens: '🔭',
  modem: '📡',
  housing: '📦',
  other: '🔧',
}

// ─── ناوبری دسکتاپ + مگامنو ───────────────────────────────────
export default function MainNav() {
  const location = useLocation()
  const [hoveredNav, setHoveredNav] = useState(null)
  const megaTimeoutRef = useRef(null)
  const openTimeoutRef = useRef(null)
  // بعد از ناوبری، کروم رویداد mouseover را دوباره برای المان زیر موس ساکن فایر می‌کند
  // و منو بی‌خود باز می‌شد — برای مدت کوتاهی بازشدن هاوری سرکوب می‌شود
  const suppressHoverRef = useRef(false)

  const { data: categoriesData } = useQuery({
    queryKey: ['nav-categories'],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  })

  const categories = categoriesData?.results || []

  // ساخت آیتم‌های گروه فروشگاه از درخت دسته‌بندی
  const shopGroup = {
    id: 'shop',
    label: 'فروشگاه',
    icon: '🛍️',
    items: [
      { label: 'همه محصولات', href: '/products', icon: '📦', desc: 'کاتالوگ کامل قطعات دوربین مداربسته' },
      { label: 'پکیج‌ها', href: '/packages', icon: '🎁', desc: 'بسته‌های آماده و اقتصادی با تخفیف ویژه' },
      ...categories.map((cat) => ({
        label: cat.name,
        href: `/categories/${cat.slug}`,
        icon: CATEGORY_TYPE_ICON[cat.category_type] || CATEGORY_TYPE_ICON.other,
        desc: cat.description || `${cat.children?.length || 0} زیردسته · ${cat.product_count || 0} محصول`,
        children: cat.children || [],
      })),
    ],
  }

  const groups = [shopGroup, ...navGroups.filter((g) => g.id !== 'shop')]

  const isActive = (href) => isActivePath(location.pathname, href)


  // بستن مگامنو با تغییر مسیر
  useEffect(() => {
    setHoveredNav(null)
    suppressHoverRef.current = true
    // سرکوب فقط با حرکت فیزیکی موس برداشته می‌شود — رویدادهای جعلیِ ناشی از
    // تغییر layout (movement صفر) نادیده گرفته می‌شوند
    const onMove = (e) => {
      if (e.movementX !== 0 || e.movementY !== 0) {
        suppressHoverRef.current = false
        document.removeEventListener('mousemove', onMove)
      }
    }
    document.addEventListener('mousemove', onMove)
    return () => document.removeEventListener('mousemove', onMove)
  }, [location.pathname])

  return (
    <nav
      className="hidden md:block relative border-t border-[var(--color-border)]"
      onMouseLeave={() => {
        megaTimeoutRef.current = setTimeout(() => setHoveredNav(null), 100)
      }}
    >
      <div className="container-site flex items-center gap-1 h-11 relative">
        {groups.map((group) => {
          const isHovered = hoveredNav === group.id
          const hasActive = group.items.some((it) => isActive(it.href))
          return (
            <div
              key={group.id}
              className="relative h-full flex items-center"
              onMouseEnter={() => {
                if (suppressHoverRef.current) return
                if (megaTimeoutRef.current) clearTimeout(megaTimeoutRef.current)
                if (openTimeoutRef.current) clearTimeout(openTimeoutRef.current)
                // hover-intent: باز شدن اولیه با تاخیر ۲۲۰ms تا عبور تصادفی موس منو را نلرزاند؛
                // وقتی یک منو باز است، جابه‌جایی بین منوها فوری می‌ماند
                if (hoveredNav) {
                  setHoveredNav(group.id)
                } else {
                  openTimeoutRef.current = setTimeout(() => {
                    if (!suppressHoverRef.current) setHoveredNav(group.id)
                  }, 220)
                }
              }}
              onMouseLeave={() => {
                if (openTimeoutRef.current) clearTimeout(openTimeoutRef.current)
              }}
            >
              <button
                className={`relative flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[13px] font-medium transition-all active:scale-[0.96] ${
                  isHovered || hasActive
                    ? 'text-gold bg-[var(--color-brand-softer)]'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover-bg-soft'
                }`}
              >
                <span className="text-sm">{group.icon}</span>
                <span>{group.label}</span>
                <span className={`inline-flex transition-transform duration-300 ${isHovered ? 'rotate-180' : ''}`}>
                  <ChevronDownIcon />
                </span>
                {hasActive && (
                  <span
                    className="absolute -bottom-[9px] right-3 left-3 h-0.5 rounded-full"
                    style={{ background: 'var(--gradient-gold)' }}
                  />
                )}
              </button>

              {/* رندر شرطی + انیمیشن ورود CSS — بدون انیمیشن خروج تا پنل
                  روی هیچ مسیری گیر نکند و باز نماند (باگ قبلی انیمیشن خروج JS) */}
              {isHovered && (
                <div
                  className="absolute top-full right-0 pt-3 z-50 animate-mega-in"
                >
                    <div
                      className="rounded-2xl overflow-hidden max-h-[calc(100vh-120px)] flex flex-col"
                      style={{
                        width: group.id === 'shop' && categories.length > 0 ? 720 : 540,
                        background: 'var(--color-bg-elevated)',
                        border: '1px solid var(--color-border-strong)',
                        boxShadow: '0 24px 64px -12px rgba(0,0,0,0.75), 0 0 0 1px rgba(251,192,45,0.06)',
                      }}
                    >
                      {/* خط طلایی بالای پنل */}
                      <div className="h-[3px] w-full flex-shrink-0" style={{ background: 'var(--gradient-gold)' }} />

                      <div className="flex items-stretch flex-1 min-h-0">
                        {/* ستون برند گروه */}
                        <div
                          className="w-44 flex-shrink-0 p-5 flex flex-col justify-between relative overflow-hidden"
                          style={{ background: 'radial-gradient(130% 130% at 100% 0%, rgba(251,192,45,0.16), transparent 62%)' }}
                        >
                          <div>
                            <div className="text-3xl mb-3">{group.icon}</div>
                            <div className="font-display font-bold text-[15px] text-[var(--color-text-primary)]">
                              {group.label}
                            </div>
                            <div className="text-[11px] text-[var(--color-text-muted)] mt-1.5 leading-relaxed">
                              {GROUP_SUBTITLES[group.id]}
                            </div>
                          </div>
                          <div className="text-[9px] text-gold font-mono tracking-[0.25em] mt-6 opacity-80">
                            DOORBINKAR
                          </div>
                          {/* حلقه تزئینی */}
                          <div
                            className="absolute -bottom-10 -left-10 w-28 h-28 rounded-full pointer-events-none"
                            style={{ border: '1px solid rgba(251,192,45,0.18)' }}
                          />
                        </div>

                        {/* آیتم‌ها */}
                        <div className="flex-1 p-3 space-y-1 overflow-y-auto min-h-0">
                          {group.items.map((item, idx) => (
                            <div
                              key={item.href}
                              className="animate-mega-item"
                              style={{ animationDelay: `${0.04 + idx * 0.05}s` }}
                            >
                              <Link
                                to={item.href}
                                onClick={() => { suppressHoverRef.current = true; setHoveredNav(null) }}
                                className={`group flex items-center gap-3.5 p-3 rounded-xl border transition-all duration-200 ${
                                  isActive(item.href)
                                    ? 'border-[rgba(251,192,45,0.4)] bg-[var(--color-brand-soft)]'
                                    : 'border-transparent hover:border-[rgba(251,192,45,0.3)] hover:bg-[var(--color-brand-softer)]'
                                }`}
                              >
                                <span
                                  className="w-10 h-10 flex-shrink-0 rounded-xl flex items-center justify-center text-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] transition-all duration-200 group-hover:border-transparent group-hover:!bg-[image:var(--gradient-gold)] group-hover:text-black group-hover:shadow-[var(--shadow-gold)]"
                                >
                                  {item.icon}
                                </span>
                                <span className="min-w-0 flex-1">
                                  <span
                                    className={`block text-[13px] font-bold transition-colors ${
                                      isActive(item.href) ? 'text-gold' : 'text-[var(--color-text-primary)] group-hover:text-gold'
                                    }`}
                                  >
                                    {item.label}
                                  </span>
                                  <span className="block text-[11px] text-[var(--color-text-muted)] mt-0.5 leading-relaxed">
                                    {item.desc}
                                  </span>
                                </span>
                              </Link>

                              {/* زیردسته‌های دسته فروشگاه */}
                              {group.id === 'shop' && item.children && item.children.length > 0 && (
                                <div className="flex flex-wrap gap-2 mt-2 mr-14">
                                  {item.children.map((child) => (
                                    <Link
                                      key={child.slug}
                                      to={`/categories/${child.slug}`}
                                      onClick={() => setHoveredNav(null)}
                                      className="text-[11px] px-2.5 py-1 rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-gold hover:border-[rgba(251,192,45,0.4)] hover:bg-[var(--color-brand-softer)] transition-colors"
                                    >
                                      {child.name}
                                    </Link>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </nav>
  )
}
