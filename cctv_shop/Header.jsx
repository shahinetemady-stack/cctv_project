import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import useAuthStore from '../../store/useAuthStore'
import useThemeStore from '../../store/useThemeStore'
import useCartStore from '../../store/useCartStore'
import { catalogService } from '../../services/catalog'
import { Spinner } from '../ui'
import api from '../../services/api'

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

// منوی ادمین بر اساس دسترسی‌ها
const ADMIN_MENU = [
  { label: 'داشبورد', path: '/admin/dashboard', perm: 'dashboard_view', icon: '📊' },
  { label: 'فاکتور فروش', path: '/admin/sales', perm: 'sale_view', icon: '🧾' },
  { label: 'کاردکس موجودی', path: '/admin/kardex', perm: 'kardex_view', icon: '📦' },
  { label: 'فاکتور خرید', path: '/admin/purchases', perm: 'purchase_view', icon: '🛒' },
  { label: 'طرف حساب‌ها', path: '/admin/contacts', perm: 'contacts_view', icon: '👥' },
  { label: 'گزارشات مالی', path: '/admin/financial', perm: 'reports_view', icon: '💰' },
  { label: 'تراز حساب‌ها', path: '/admin/reports', perm: 'balance_view', icon: '⚖️' },
  { label: 'مدیریت نقش‌ها', path: '/admin/roles', perm: 'users_edit', icon: '🎭' },
  { label: 'محصولات', path: '/products', perm: 'products_view', icon: '📷' },
]

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
  const timerRef = useRef(null)
  const menuRef = useRef(null)

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
      if (!menuRef.current?.contains(e.target)) { setMenuOpen(false) }
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

  const isStaff = user?.is_staff || false

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
                    <div className="w-10 h-10 rounded-lg bg-navy flex-shrink-0 flex items-center justify-center text-brand">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.889L15 14v-4z"/>
                      </svg>
                    </div>
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
                {/* دکمه پروفایل */}
                <button onClick={() => { setMenuOpen(!menuOpen) }}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/5 transition-colors text-sm">
                  <div className="w-7 h-7 bg-brand rounded-full flex items-center justify-center text-white text-xs font-bold">
                    {user?.first_name?.[0] || user?.phone?.[0] || 'U'}
                  </div>
                </button>

                {/* دراپ‌داون پروفایل */}
                {menuOpen && (
                  <div className="absolute left-0 top-full mt-2 w-48 glass-dark rounded-xl border border-white/10 shadow-2xl overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-white/5">
                      <div className="text-sm font-medium text-white truncate">
                        {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.phone}
                      </div>
                      <div className="text-xs text-gray-steel">
                        {isPartner() ? '🤝 همکار' : isStaff ? '⚙️ پرسنل' : '👤 عمومی'}
                      </div>
                    </div>
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
