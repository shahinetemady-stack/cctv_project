import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import useAuthStore from '../../store/useAuthStore'
import useThemeStore from '../../store/useThemeStore'
import useCartStore from '../../store/useCartStore'
import { catalogService } from '../../services/catalog'
import api from '../../services/api'

// ─── Logo Upload Modal (فقط برای ادمین) ─────────────────────
function LogoUploadModal({ onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const qc = useQueryClient()
  const fileRef = useRef()

  function handleFile(e) {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  async function upload() {
    if (!file) return
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('logo', file)
      const res = await api.post('/core/settings/logo/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      qc.invalidateQueries(['site-settings'])
      onUploaded(res.data.logo_url)
      onClose()
    } catch (e) {
      setErr(e.response?.data?.error || 'خطا در آپلود')
    }
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 z-[500] flex items-center justify-center bg-black/80 p-4">
      <div className="card p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-sm">آپلود لوگو</h3>
          <button onClick={onClose} className="text-gray-steel text-xl">×</button>
        </div>
        <div onClick={() => fileRef.current.click()}
          className="border-2 border-dashed border-white/20 rounded-xl p-8 text-center cursor-pointer hover:border-brand/50 transition-all mb-4">
          {preview ? (
            <img src={preview} alt="preview" className="max-h-24 mx-auto object-contain" />
          ) : (
            <>
              <div className="text-3xl mb-2">🖼️</div>
              <div className="text-sm text-gray-steel">کلیک کنید یا فایل را اینجا بکشید</div>
              <div className="text-xs text-gray-steel mt-1">PNG, JPG, SVG</div>
            </>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
        {err && <div className="text-red-400 text-xs mb-3">{err}</div>}
        <div className="flex gap-2">
          <button onClick={upload} disabled={!file || loading}
            className="btn-primary flex-1 py-2 text-sm disabled:opacity-50">
            {loading ? 'در حال آپلود...' : '⬆️ آپلود'}
          </button>
          <button onClick={onClose} className="btn-secondary px-4 py-2 text-sm">انصراف</button>
        </div>
      </div>
    </div>
  )
}

const SunIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
    <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
)
const MoonIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
)
const CartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
)

export default function Header() {
  const { user, logout } = useAuthStore()
  const { dark, toggle } = useThemeStore()
  const { itemCount } = useCartStore()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [showLogoUpload, setShowLogoUpload] = useState(false)
  const isStaff = user?.is_staff || false

  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 0,
  })

  async function handleSearch(e) {
    e.preventDefault()
    if (search.trim()) navigate(`/products?search=${encodeURIComponent(search)}`)
  }

  async function handleLogout() {
    try { await api.post('/users/auth/logout/') } catch {}
    logout()
    navigate('/auth/login')
  }

  return (
    <>
      {showLogoUpload && (
        <LogoUploadModal
          onClose={() => setShowLogoUpload(false)}
          onUploaded={(url) => console.log('Logo uploaded:', url)}
        />
      )}
      <header className="sticky top-0 z-40 glass border-b border-white/5">
        <div className="container-main flex items-center gap-4 h-16">
          {/* لوگو */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0 group">
            {settings?.site_logo ? (
              <div className="relative">
                <img
                  src={settings.site_logo}
                  alt={settings?.site_name || 'logo'}
                  className="h-9 w-auto object-contain"
                  onError={e => e.target.style.display = 'none'}
                />
                {isStaff && (
                  <button
                    onClick={e => { e.preventDefault(); setShowLogoUpload(true) }}
                    className="absolute -top-1 -right-1 w-4 h-4 bg-brand rounded-full text-[8px] text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    title="تغییر لوگو">
                    ✏️
                  </button>
                )}
              </div>
            ) : (
              <div className="relative">
                <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.889L15 14v-4zM3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/>
                  </svg>
                </div>
                {isStaff && (
                  <button
                    onClick={e => { e.preventDefault(); setShowLogoUpload(true) }}
                    className="absolute -top-1 -right-1 w-4 h-4 bg-brand/80 rounded-full text-[8px] text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    title="آپلود لوگو">
                    +
                  </button>
                )}
              </div>
            )}
            <span className="font-display font-bold text-white text-sm hidden sm:block">
              {settings?.site_name || 'قطعات دوربین'}
            </span>
            <span className="text-[10px] text-brand font-mono hidden md:block">CCTV PARTS</span>
          </Link>

          {/* جستجو */}
          <form onSubmit={handleSearch} className="flex-1 max-w-xl">
            <div className="relative">
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="جستجو در قطعات... (سنسور، چیپست، مدل)"
                className="input w-full pl-10 pr-4 text-sm"
              />
              <button type="submit" className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-steel hover:text-white">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </button>
            </div>
          </form>

          {/* دکمه‌های راست */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* دارک مود */}
            <button onClick={toggle} className="btn-ghost p-2 rounded-xl text-gray-steel hover:text-white">
              {dark ? <SunIcon /> : <MoonIcon />}
            </button>

            {/* سوشیال مدیا */}
            {settings?.whatsapp_number && (
              <a href={`https://wa.me/${settings.whatsapp_number.replace(/[^0-9]/g, '')}`}
                target="_blank" rel="noopener noreferrer"
                className="btn-ghost p-2 rounded-xl text-gray-steel hover:text-green-400 transition-colors" title="واتساپ">
                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                </svg>
              </a>
            )}
            {settings?.telegram_username && (
              <a href={`https://t.me/${settings.telegram_username}`}
                target="_blank" rel="noopener noreferrer"
                className="btn-ghost p-2 rounded-xl text-gray-steel hover:text-blue-400 transition-colors" title="تلگرام">
                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
              </a>
            )}
            {settings?.eitaa_username && (
              <a href={`https://eitaa.com/${settings.eitaa_username}`}
                target="_blank" rel="noopener noreferrer"
                className="btn-ghost p-1.5 rounded-xl text-gray-steel hover:text-purple-400 transition-colors text-[10px] font-bold" title="ایتا">
                ایتا
              </a>
            )}

            {/* سبد خرید */}
            <Link to="/cart" className="btn-ghost p-2 rounded-xl text-gray-steel hover:text-white relative">
              <CartIcon />
              {itemCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-brand text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center font-bold">
                  {itemCount}
                </span>
              )}
            </Link>

            {/* کاربر */}
            {user ? (
              <div className="flex items-center gap-2">
                {isStaff && (
                  <Link to="/admin/dashboard" className="btn-ghost text-xs px-3 py-1.5 rounded-xl text-brand hover:bg-brand/10">
                    پنل مدیریت
                  </Link>
                )}
                <button onClick={handleLogout} className="btn-ghost text-xs px-3 py-1.5 rounded-xl text-gray-steel hover:text-white">
                  خروج
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/auth/login" className="btn-ghost text-xs px-3 py-1.5 rounded-xl text-gray-steel hover:text-white">
                  ورود
                </Link>
                <Link to="/auth/register" className="btn-primary text-xs px-3 py-1.5 rounded-xl">
                  ثبت‌نام
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* منو */}
        <nav className="border-t border-white/5">
          <div className="container-main flex items-center gap-1 h-10 overflow-x-auto">
            {[
              ['همه محصولات', '/products'],
              ['🎁 پکیج‌ها', '/packages'],
              ['📚 مقالات', '/blog'],
              ['🎬 ویدیوها', '/videos'],
              ['🎯 راهنمای انتخاب', '/guides/part-selection'],
              ['🇨🇳 سفارش از چین', '/china-order'],
              ['🔍 رهگیری', '/track'],
            ].map(([label, href]) => (
              <Link key={href} to={href}
                className="text-xs px-3 py-1.5 rounded-lg text-gray-steel hover:text-white hover:bg-white/5 transition-all whitespace-nowrap">
                {label}
              </Link>
            ))}
          </div>
        </nav>
      </header>
    </>
  )
}
