"""
python write_files.py
مستقیم فایل‌ها را روی دیسک می‌نویسد
"""
import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── Header.jsx ──────────────────────────────────────────────
header_path = os.path.join(FRONTEND, 'components', 'layout', 'Header.jsx')
with open(header_path, 'w', encoding='utf-8') as f:
    f.write("""import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import useAuthStore from '../../store/useAuthStore'
import useThemeStore from '../../store/useThemeStore'
import useCartStore from '../../store/useCartStore'
import { catalogService } from '../../services/catalog'
import { Spinner } from '../ui'

const SearchIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
  </svg>
)
const MoonIcon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
)
const SunIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="5" strokeWidth="2"/>
    <path strokeWidth="2" strokeLinecap="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
  </svg>
)

function NavCategories() {
  const { data } = useQuery({
    queryKey: ['categories'],
    queryFn: catalogService.getCategories,
  })
  const cats = Array.isArray(data) ? data : (data?.results || [])
  return (
    <nav className="flex items-center gap-1 pb-2 overflow-x-auto scrollbar-thin">
      <Link to="/products" className="flex-shrink-0 text-xs px-3 py-1.5 rounded-lg text-gray-steel hover:text-white hover:bg-white/5 transition-colors">
        همه محصولات
      </Link>
      {cats.map(cat => (
        <Link key={cat.id} to={'/products?category=' + cat.id}
          className="flex-shrink-0 text-xs px-3 py-1.5 rounded-lg text-gray-steel hover:text-white hover:bg-white/5 transition-colors">
          {cat.name}
        </Link>
      ))}
    </nav>
  )
}

export default function Header() {
  const navigate = useNavigate()
  const { user, logout, isAuthenticated, isPartner } = useAuthStore()
  const { dark, toggle } = useThemeStore()
  const { count, inquiryCount } = useCartStore()

  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showSearch, setShowSearch] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const searchRef = useRef(null)
  const menuRef = useRef(null)
  const timerRef = useRef(null)

  const isStaff = user?.is_staff || false

  useEffect(() => {
    clearTimeout(timerRef.current)
    if (search.length < 2) { setSearchResults([]); return }
    setSearching(true)
    timerRef.current = setTimeout(async () => {
      try {
        const data = await catalogService.searchProducts(search)
        setSearchResults(data.results || [])
      } catch {}
      setSearching(false)
    }, 400)
  }, [search])

  useEffect(() => {
    const handler = (e) => {
      if (!searchRef.current?.contains(e.target)) setShowSearch(false)
      if (!menuRef.current?.contains(e.target)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = async () => {
    const refresh = localStorage.getItem('refresh_token')
    try { await import('../../services/auth').then(m => m.authService.logout(refresh)) } catch {}
    logout()
    navigate('/')
    setMenuOpen(false)
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (search.trim()) {
      navigate(`/products?search=${encodeURIComponent(search)}`)
      setShowSearch(false)
      setSearch('')
    }
  }

  return (
    <header className="sticky top-0 z-40 glass-dark border-b border-white/5">
      <div className="container-main">
        <div className="flex items-center gap-4 h-16">
          <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center shadow-brand">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M15 10l4.553-2.069A1 1 0 0 1 21 8.82v6.36a1 1 0 0 1-1.447.889L15 14v-4zM3 8a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8z"/>
              </svg>
            </div>
            <div className="hidden sm:block">
              <div className="font-display font-bold text-white text-sm leading-tight">قطعات دوربین</div>
              <div className="text-cyan text-[10px] font-mono leading-tight">CCTV PARTS</div>
            </div>
          </Link>

          <div ref={searchRef} className="flex-1 max-w-xl relative">
            <form onSubmit={handleSearch}>
              <div className="relative">
                <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-steel hover:text-brand transition-colors">
                  {searching ? <Spinner size="sm" /> : <SearchIcon />}
                </button>
                <input
                  value={search}
                  onChange={e => { setSearch(e.target.value); setShowSearch(true) }}
                  onFocus={() => setShowSearch(true)}
                  placeholder="جستجو در قطعات... (سنسور، چیپست، مدل)"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pr-10 pl-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:border-brand/50 transition-all duration-200"
                />
              </div>
            </form>
            {showSearch && searchResults.length > 0 && (
              <div className="absolute top-full mt-2 w-full glass-dark rounded-xl border border-white/10 shadow-2xl overflow-hidden z-50">
                {searchResults.slice(0, 6).map(p => (
                  <Link key={p.id} to={`/products/${p.slug}`}
                    onClick={() => { setShowSearch(false); setSearch('') }}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors group">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white group-hover:text-cyan truncate">{p.name}</div>
                      <div className="text-xs text-gray-steel">{p.category_name}</div>
                    </div>
                  </Link>
                ))}
                <Link to={`/products?search=${encodeURIComponent(search)}`}
                  onClick={() => { setShowSearch(false); setSearch('') }}
                  className="block text-center py-3 text-xs text-brand hover:text-cyan border-t border-white/5 transition-colors">
                  مشاهده همه نتایج ←
                </Link>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            <button onClick={toggle} className="btn-ghost p-2 rounded-xl text-gray-steel hover:text-white">
              {dark ? <SunIcon /> : <MoonIcon />}
            </button>

            {isAuthenticated() && isPartner() && (
              <Link to="/inquiry-cart" className="btn-ghost p-2 rounded-xl relative">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                {inquiryCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-cyan text-navy text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">{inquiryCount}</span>
                )}
              </Link>
            )}

            {isAuthenticated() && !isPartner() && (
              <Link to="/cart" className="btn-ghost p-2 rounded-xl text-gray-steel hover:text-white relative">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2 9m12-9l2 9M9 21a1 1 0 1 0 2 0 1 1 0 0 0-2 0zm8 0a1 1 0 1 0 2 0 1 1 0 0 0-2 0z" />
                </svg>
                {count > 0 && (
                  <span className="absolute -top-1 -right-1 bg-brand text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">{count}</span>
                )}
              </Link>
            )}

            {isAuthenticated() ? (
              <div className="relative" ref={menuRef}>
                <button onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-white/5 transition-colors">
                  <div className="w-8 h-8 bg-brand rounded-full flex items-center justify-center text-white text-sm font-bold">
                    {user?.first_name?.[0] || user?.phone?.[0] || 'U'}
                  </div>
                  {isStaff && (
                    <svg className="w-4 h-4 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  )}
                </button>

                {menuOpen && (
                  <div className="absolute left-0 top-full mt-2 w-52 glass-dark rounded-xl border border-white/10 shadow-2xl overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-white/5">
                      <div className="text-sm font-medium text-white truncate">
                        {user?.first_name ? `${user.first_name} ${user.last_name}`.trim() : user?.phone}
                      </div>
                      <div className="text-xs text-gray-steel mt-0.5">
                        {isStaff ? '⚙️ پرسنل' : isPartner() ? '🤝 همکار' : '👤 عمومی'}
                      </div>
                    </div>

                    {isStaff && (
                      <Link to="/admin/dashboard" onClick={() => setMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-3 text-sm bg-brand/10 hover:bg-brand/20 transition-colors text-brand font-medium border-b border-white/5">
                        <span>⚙️</span> پنل مدیریت
                      </Link>
                    )}

                    <Link to="/account" onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-white/5 transition-colors text-gray-300">
                      <span>👤</span> پروفایل من
                    </Link>
                    <Link to="/account/orders" onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-white/5 transition-colors text-gray-300">
                      <span>📋</span> سفارش‌های من
                    </Link>
                    <button onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-red-500/10 text-red-400 transition-colors border-t border-white/5">
                      <span>🚪</span> خروج
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/auth/login" className="btn-ghost text-sm px-3 py-2">ورود</Link>
                <Link to="/auth/register" className="btn-primary text-sm px-3 py-2">ثبت‌نام</Link>
              </div>
            )}
          </div>
        </div>
        <NavCategories />
      </div>
    </header>
  )
}
""")
print("✓ Header.jsx نوشته شد")

# ─── DashboardPage.jsx ───────────────────────────────────────
dash_path = os.path.join(FRONTEND, 'pages', 'admin', 'DashboardPage.jsx')
with open(dash_path, 'w', encoding='utf-8') as f:
    f.write("""import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'

const STATUS_FA = {
  pending: 'در انتظار', confirmed: 'تأیید شده',
  awaiting_payment: 'در انتظار پرداخت', paid: 'پرداخت شده',
  ready_to_ship: 'آماده ارسال', shipped: 'ارسال شده', cancelled: 'لغو شده',
}
const STATUS_COLOR = {
  pending: '#FF9500', confirmed: '#0066FF', awaiting_payment: '#8B5CF6',
  paid: '#00C896', ready_to_ship: '#00C896', shipped: '#0066FF', cancelled: '#FF3B3B',
}

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/stats/').then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: bs } = useQuery({
    queryKey: ['balance-sheet-dash'],
    queryFn: () => api.get('/accounting/reports/balance-sheet/').then(r => r.data),
    staleTime: 300000,
  })

  if (isLoading) return <PageLoader />
  if (isError) return (
    <div className="container-main py-20 text-center text-gray-steel">
      خطا در بارگذاری — با حساب ادمین وارد شوید
    </div>
  )

  const { sales, orders, users, inventory, monthly_sales, last_orders } = data
  const maxSale = Math.max(...monthly_sales.map(d => d.total), 1)

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-display font-bold text-2xl text-white">داشبورد مدیریت</h1>
        <span className="text-xs text-gray-steel">بروزرسانی خودکار هر دقیقه</span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block"></span>آمار فروش
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">امروز</div><div className="text-lg font-bold text-green-400">{fmt(sales.today)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">این هفته</div><div className="text-lg font-bold text-white">{fmt(sales.week)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">این ماه</div><div className="text-lg font-bold text-brand">{fmt(sales.month)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400 inline-block"></span>وضعیت سفارشات
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">امروز</div><div className="text-lg font-bold text-white">{fmt(orders.today)}</div><div className="text-[10px] text-gray-steel">سفارش</div></div>
            <div><div className="text-xs text-gray-steel mb-1">در انتظار</div><div className="text-lg font-bold text-orange-400">{fmt(orders.pending)}</div><div className="text-[10px] text-gray-steel">سفارش</div></div>
            <div><div className="text-xs text-gray-steel mb-1">پرداخت</div><div className="text-lg font-bold text-purple-400">{fmt(orders.awaiting_payment)}</div><div className="text-[10px] text-gray-steel">در انتظار</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-purple-400 inline-block"></span>کاربران
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">جدید امروز</div><div className="text-lg font-bold text-white">{fmt(users.new_today)}</div><div className="text-[10px] text-gray-steel">کاربر</div></div>
            <div><div className="text-xs text-gray-steel mb-1">درخواست همکار</div><div className="text-lg font-bold text-purple-400">{fmt(users.partner_requests)}</div><div className="text-[10px] text-gray-steel">در انتظار تأیید</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-orange-400 inline-block"></span>انبار
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">موجودی کم</div><div className="text-lg font-bold text-orange-400">{fmt(inventory.low_stock)}</div><div className="text-[10px] text-gray-steel">محصول</div></div>
            <div><div className="text-xs text-gray-steel mb-1">ناموجود</div><div className="text-lg font-bold text-red-400">{fmt(inventory.out_of_stock)}</div><div className="text-[10px] text-gray-steel">محصول</div></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block"></span>دریافت و پرداخت
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">طلب از مشتریان</div><div className="text-lg font-bold text-blue-400">{fmt(bs?.assets?.receivable)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">بدهی به تامین‌کنندگان</div><div className="text-lg font-bold text-red-400">{fmt(bs?.liabilities?.payable_irr)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">موجودی بانک</div><div className="text-lg font-bold text-green-400">{fmt(bs?.assets?.cash_irr)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand inline-block"></span>تراز کلی
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">سود ناخالص</div><div className={`text-lg font-bold ${(bs?.profit?.gross_profit||0)>=0?'text-green-400':'text-red-400'}`}>{fmt(bs?.profit?.gross_profit)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">ارزش موجودی کالا</div><div className="text-lg font-bold text-white">{fmt(bs?.assets?.stock_value)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">خالص دارایی</div><div className={`text-lg font-bold ${(bs?.equity||0)>=0?'text-green-400':'text-red-400'}`}>{fmt(bs?.equity)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
          </div>
        </div>
      </div>

      <div className="card p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-sm text-white">فروش ۶ ماه اخیر</h2>
          <span className="text-xs text-gray-steel">تومان</span>
        </div>
        <div className="flex items-end gap-3 h-32">
          {monthly_sales.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className="text-[10px] text-gray-steel">{d.count > 0 ? d.count : ''}</div>
              <div className="w-full rounded-t-lg transition-all duration-500"
                style={{ height: Math.max((d.total/maxSale)*90, d.total>0?4:0), background: i===monthly_sales.length-1?'#0066FF':'#0066FF33', minHeight: d.total>0?4:0 }} />
              <div className="text-[10px] text-gray-steel">{d.month}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <h2 className="font-semibold text-sm text-white mb-4">آخرین سفارشات</h2>
        <div className="space-y-0">
          {last_orders.map((o, i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-brand">{o.order_number}</span>
                <span className="text-xs text-gray-steel">{o.user}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ color: STATUS_COLOR[o.status], background: STATUS_COLOR[o.status]+'20' }}>
                  {STATUS_FA[o.status] || o.status}
                </span>
                <span className="text-xs font-bold text-white">{fmt(o.amount)} ت</span>
                <span className="text-[10px] text-gray-steel" dir="ltr">{o.created_at}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
""")
print("✓ DashboardPage.jsx نوشته شد")
print("\nفرانت‌اند را restart کنید (Ctrl+C و npm run dev)")
