import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'

// ─── لود lazy قالب‌ها ────────────────────────────────────────
import HeroExplode from '../components/home/HeroSection'
import GalaxyBackground from '../components/layout/GalaxyBackground'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// ─── Hero ویدیو (inline) ─────────────────────────────────────
function HeroVideo() {
  return (
    <section style={{ position: 'relative', height: '100vh', overflow: 'hidden', background: '#000' }}>
      <video autoPlay muted loop playsInline
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}>
        <source src="/videos/hero_camera.mp4" type="video/mp4" />
      </video>
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0.4) 100%)' }}/>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '0 80px', direction: 'rtl' }}>
        <div style={{ maxWidth: 480 }}>
          <h1 style={{ fontSize: 52, fontWeight: 800, color: '#fff', lineHeight: 1.15, marginBottom: 16, fontFamily: 'Tahoma' }}>
            قطعات <span style={{ color: '#ffa500' }}>دوربین</span><br/>مداربسته
          </h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.5)', marginBottom: 32, fontFamily: 'Tahoma', lineHeight: 1.8 }}>
            تامین مستقیم از کارخانه — بهترین قیمت بازار
          </p>
          <div style={{ display: 'flex', gap: 14 }}>
            <Link to="/products" style={{ background: '#ffa500', color: '#000', textDecoration: 'none', borderRadius: 10, padding: '14px 28px', fontSize: 14, fontWeight: 700, fontFamily: 'Tahoma' }}>
              مشاهده محصولات
            </Link>
            <Link to="/china-order" style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.8)', textDecoration: 'none', border: '0.5px solid rgba(255,255,255,0.2)', borderRadius: 10, padding: '14px 22px', fontSize: 14, fontFamily: 'Tahoma' }}>
              سفارش از چین
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Hero مینیمال ─────────────────────────────────────────────
function HeroMinimal() {
  return (
    <section className="relative overflow-hidden py-24 md:py-32">
      <div className="absolute inset-0 bg-hero-glow" />
      <div className="absolute inset-0 bg-grid-pattern bg-grid opacity-40" />
      <div className="container-main relative text-center">
        <h1 className="font-display font-extrabold text-4xl md:text-6xl text-white leading-tight mb-6">
          قطعات دوربین
          <span className="block text-transparent bg-clip-text bg-gradient-to-l from-cyan to-brand">
            با کیفیت اصل
          </span>
        </h1>
        <p className="text-gray-steel text-lg max-w-xl mx-auto mb-10">
          سنسور، لنز، برد ISP و تمام قطعات موردنیاز دوربین مداربسته
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link to="/products" className="btn-primary px-8 py-3 text-base">مشاهده محصولات</Link>
          <Link to="/auth/register" className="btn-secondary px-8 py-3 text-base">عضویت همکار</Link>
        </div>
      </div>
    </section>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
export default function HomePage() {
  const [theme, setTheme] = useState('explode')

  // لود قالب از localStorage
  useEffect(() => {
    const saved = localStorage.getItem('site_theme')
    if (saved) setTheme(saved)

    // گوش دادن به تغییرات (وقتی ادمین قالب را عوض می‌کند)
    const onStorage = (e) => {
      if (e.key === 'site_theme' && e.newValue) setTheme(e.newValue)
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const { data: featured = [] } = useQuery({
    queryKey: ['featured-products'],
    queryFn: () => api.get('/catalog/products/?limit=6').then(r => r.data.results || r.data),
    staleTime: 60000,
  })

  // انتخاب Hero بر اساس قالب
  const HeroComponent = theme === 'video' ? HeroVideo : theme === 'minimal' ? HeroMinimal : HeroExplode

  return (
    <div style={{ background: 'transparent', minHeight: '100vh', position: 'relative' }}>
      {theme !== 'explode' && <GalaxyBackground />}

      {/* ── Hero ── */}
      <HeroComponent />

      {/* ── محصولات ── */}
      {featured.length > 0 && (
        <section style={{ padding: '80px 80px', maxWidth: 1400, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 40, direction: 'rtl' }}>
            <div>
              <p style={{ fontSize: 11, color: '#ffa500', letterSpacing: '2px', marginBottom: 6, fontFamily: 'monospace' }}>FEATURED PRODUCTS</p>
              <h2 style={{ fontSize: 28, fontWeight: 700, color: '#fff', fontFamily: 'Tahoma' }}>پرفروش‌ترین قطعات</h2>
            </div>
            <div style={{ flex: 1, height: '0.5px', background: 'rgba(255,255,255,0.06)' }}/>
            <Link to="/products" style={{ color: '#ffa500', textDecoration: 'none', fontSize: 13, fontFamily: 'Tahoma' }}>مشاهده همه ←</Link>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
            {featured.map(product => (
              <Link key={product.id} to={`/products/${product.slug}`} style={{ textDecoration: 'none' }}>
                <div className="card" style={{ borderRadius: 12, overflow: 'hidden', transition: 'border-color 0.2s, transform 0.2s' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,165,0,0.25)'; e.currentTarget.style.transform = 'translateY(-3px)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.transform = 'translateY(0)' }}>
                  <div style={{ height: 140, background: '#111', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {product.image
                      ? <img src={product.image} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 16 }}/>
                      : <div style={{ width: 60, height: 40, background: '#1a1a1a', borderRadius: 6, border: '0.5px solid rgba(255,255,255,0.08)' }}/>
                    }
                  </div>
                  <div style={{ padding: 14, direction: 'rtl' }}>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)', fontFamily: 'Tahoma', marginBottom: 6, lineHeight: 1.4 }}>{product.name}</div>
                    <div style={{ fontSize: 13, color: '#ffa500', fontFamily: 'Tahoma', fontWeight: 600, direction: 'ltr', textAlign: 'right' }}>
                      {product.min_price ? fmt(product.min_price) + ' ت' : 'استعلام'}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ── CTA ── */}
      <section style={{ padding: '60px 80px', borderTop: '0.5px solid rgba(255,255,255,0.04)', position: 'relative', zIndex: 1 }}>
        <div style={{ maxWidth: 1240, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', direction: 'rtl' }}>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: '#fff', fontFamily: 'Tahoma', marginBottom: 8 }}>قطعه‌ای که نمی‌یابید؟</h2>
            <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.35)', fontFamily: 'Tahoma' }}>سفارش مستقیم از چین — تحویل ۲ تا ۳ هفته</p>
          </div>
          <Link to="/china-order" style={{ background: '#ffa500', color: '#000', textDecoration: 'none', borderRadius: 10, padding: '14px 32px', fontSize: 14, fontWeight: 700, fontFamily: 'Tahoma', flexShrink: 0 }}>
            سفارش از چین ←
          </Link>
        </div>
      </section>
    </div>
  )
}
