// ─── گروه‌های ناوبری سایت (مگامنوی دسکتاپ + دراور موبایل) ────
export const navGroups = [
  {
    id: 'shop',
    label: 'فروشگاه',
    icon: '🛍️',
    items: [
      { label: 'همه محصولات', href: '/products', icon: '📦', desc: 'کاتالوگ کامل قطعات دوربین مداربسته' },
      { label: 'پکیج‌ها', href: '/packages', icon: '🎁', desc: 'بسته‌های آماده و اقتصادی با تخفیف ویژه' },
    ],
  },
  {
    id: 'content',
    label: 'محتوا',
    icon: '📖',
    items: [
      { label: 'مقالات', href: '/blog', icon: '📚', desc: 'مقالات آموزشی، راهنماها و نقد و بررسی' },
      { label: 'ویدیوها', href: '/videos', icon: '🎬', desc: 'ویدیوهای آموزشی و نقد محصولات' },
    ],
  },
  {
    id: 'services',
    label: 'خدمات',
    icon: '⚡',
    items: [
      { label: 'سفارش از چین', href: '/china-order', icon: '🇨🇳', desc: 'تهیه و واردات قطعات از بازار چین' },
      { label: 'پیگیری سفارش', href: '/china-order/track', icon: '📦', desc: 'پیگیری وضعیت سفارش‌های ثبت شده' },
      { label: 'سوالات متداول', href: '/china-order/faq', icon: '❓', desc: 'پاسخ به سوالات پرتکرار کاربران' },
    ],
  },
]

// ─── تشخیص فعال‌بودن مسیر ─────────────────────────────────────
export const isActivePath = (pathname, href) =>
  pathname === href || (href !== '/' && pathname.startsWith(href))
