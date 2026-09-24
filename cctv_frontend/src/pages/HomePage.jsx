import { useEffect, useRef, useState, lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CircuitBoard, Focus, Radio, Box, Wrench, Factory, Zap, Microscope,
  Handshake, Gem, Globe, Camera, Play, ArrowLeft, Check,
  RotateCw, Scale,
} from 'lucide-react'
import api from '../services/api'
import { mediaUrl } from '../utils/media'
import { useAfterLoad } from '../hooks/useAfterLoad'
import useCompareStore from '../store/useCompareStore'
import BrandMarquee from '../components/home/BrandMarquee'
import Seo from '../components/Seo'

// کنواس برد و باکس هوشمند — چانک جدا تا کد/اجرا از مسیر بحرانی FCP/LCP خارج شود؛
// اسپلش استاتیک index.html معادل ظاهری آنها را تا لود چانک پوشش می‌دهد
const SmartSearch = lazy(() => import('../components/home/SmartSearch'))
const BoardCanvas = lazy(() => import('../components/home/BoardCanvas'))

const CATEGORY_ICON = {
  board: CircuitBoard,
  lens: Focus,
  modem: Radio,
  housing: Box,
  other: Wrench,
}

// ─── ثابت‌های تم — همه از توکن‌های CSS (دارک/لایت خودکار) ─────
const B   = 'var(--color-brand)'
const BS  = 'var(--color-brand-soft)'
const BST = 'var(--color-brand-softer)'
const T1  = 'var(--color-text-primary)'
const T2  = 'var(--color-text-secondary)'
const T3  = 'var(--color-text-muted)'
const MONO = "'JetBrains Mono', monospace"

// ─── Reveal wrapper ──────────────────────────────────────────────
function Section({ children, style = {}, delay = 0 }) {
  const ref = useRef(null); const [vis, setVis] = useState(false)
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVis(true); obs.disconnect() }
    }, { threshold: 0.1 })
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])
  return (
    <div ref={ref} style={{
      opacity: vis ? 1 : 0,
      transform: vis ? 'translateY(0)' : 'translateY(40px)',
      transition: `opacity 0.8s ease ${delay}ms, transform 0.8s ease ${delay}ms`,
      ...style
    }}>{children}</div>
  )
}

// ─── Glass Card ──────────────────────────────────────────────────
function GlassCard({ children, style = {}, hover = true }) {
  const [hov, setHov] = useState(false)
  return (
    <div
      onMouseEnter={() => hover && setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: `1px solid ${hov ? 'var(--color-border-strong)' : 'var(--color-border)'}`,
        borderRadius: 20,
        boxShadow: hov ? 'var(--shadow-card-hover), 0 0 40px rgba(251,192,45,0.07)' : 'var(--shadow-card)',
        transform: hov && hover ? 'translateY(-4px)' : 'none',
        transition: 'all 0.3s ease',
        ...style,
      }}
    >{children}</div>
  )
}

// ─── مشاهده‌گر ورود به ویوپورت — برای به تأخیر انداختن کوئری‌های زیر اسکرول ───
// نکته سئو: گوگل‌بات با ویوپورت خیلی بلند رندر می‌کند، پس این سکشن‌ها برای خزنده هم لود می‌شوند.
function useInViewOnce(rootMargin = '600px') {
  const ref = useRef(null); const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current; if (!el || inView) return
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setInView(true); obs.disconnect() }
    }, { rootMargin })
    obs.observe(el)
    return () => obs.disconnect()
  }, [inView, rootMargin])
  return [ref, inView]
}

// سکشن‌های زیر اسکرول — mount فرزندان فقط وقتی نزدیک ویوپورت شوند تا DOM اولیه کوچک
// بماند و restyle سراسری stylesheet اصلی (async) روی DOM کوچک اعمال شود (CLS کمتر)
function Deferred({ children, rootMargin = '350px' }) {
  const [ref, inView] = useInViewOnce(rootMargin)
  return <div ref={ref}>{inView ? children : null}</div>
}

// ─── Product Card ────────────────────────────────────────────────
function ProductCard({ product }) {
  const [hov, setHov] = useState(false)
  const [flipped, setFlipped] = useState(false)
  const { add: addToCompare, remove: removeFromCompare, has: inCompare } = useCompareStore()
  const compared = inCompare(product.slug)
  const price = product.variants?.[0]?.final_price || product.min_price
  const rawImg = product.main_image?.image || product.images?.[0]?.image || product.image
  const img = mediaUrl(rawImg)
  const rawBack = product.secondary_image?.image || product.images?.[1]?.image
  const backImg = rawBack && rawBack !== rawImg ? mediaUrl(rawBack) : null
  const handleCompare = (e) => {
    e.preventDefault()
    if (compared) {
      removeFromCompare(product.slug)
    } else {
      addToCompare({
        slug: product.slug,
        name: product.name,
        category_id: product.category_id,
        image: rawImg || null,
        min_price: price || null,
      })
    }
  }
  // چیپ‌های مشخصات زیر مدل — همان الگوی کارت صفحه محصولات (زرد = رنگ برند)
  const catType = product.category_type || 'other'
  const specChips = catType === 'lens'
    ? [{ v: product.lens_resolution, lat: 1 }, { v: product.lens_degree, lat: 1 }, { v: product.focal_ratio }, { v: product.brand }]
    : catType === 'board'
      ? [{ v: product.board_system, lat: 1 }, { v: product.board_resolution, lat: 1 }, { v: product.brand }]
      : [{ v: product.brand }, { v: product.sensor_name, gray: 1 }, { v: product.lens_name, gray: 1 }]
  return (
    <Link to={`/products/${product.slug || product.id}`} style={{ textDecoration: 'none', display: 'block', height: '100%' }}>
      <div
        className="group"
        onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
        style={{
          background: 'var(--glass-bg)',
          backdropFilter: 'blur(20px)',
          border: `1px solid ${hov ? 'var(--color-brand)' : 'var(--color-border)'}`,
          borderRadius: 16,
          overflow: 'hidden',
          transform: hov ? 'translateY(-6px) scale(1.01)' : 'none',
          transition: 'all 0.3s ease',
          boxShadow: hov ? 'var(--shadow-card-hover), 0 0 30px rgba(251,192,45,0.08)' : 'var(--shadow-card)',
          display: 'flex', flexDirection: 'column', height: '100%',
        }}
      >
        <div className="product-media-stage" style={{ aspectRatio: '1/1', overflow: 'hidden', position: 'relative' }}>
          {img ? (
            backImg ? (
              <div className="product-flip">
                <div className={`product-flip-inner${flipped ? ' flipped' : ''}`}>
                  <div className="product-flip-face">
                    <img src={img} alt={product.name} loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 12 }}/>
                  </div>
                  <div className="product-flip-face product-flip-back">
                    <img src={backImg} alt={`${product.name} — نمای دیگر`} loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 12 }}/>
                  </div>
                </div>
              </div>
            ) : (
              <img src={img} alt={product.name} loading="lazy" style={{
                width: '100%', height: '100%', objectFit: 'contain', padding: 12,
                transition: 'transform 0.4s', ...(hov ? { transform: 'scale(1.06)' } : {})
              }}/>
            )
          ) : (
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: T3, opacity: 0.4 }}>
              <Camera size={44} strokeWidth={1.2} />
            </div>
          )}
          {/* دکمه چرخش تصویر — فقط روی دستگاه‌های لمسی نمایش داده می‌شود (CSS: hover: none) */}
          {backImg && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setFlipped(v => !v) }}
              aria-label="نمایش نمای دیگر محصول"
              className="product-flip-btn"
              style={{
                position: 'absolute', bottom: 8, left: 8, zIndex: 10,
                width: 44, height: 44, borderRadius: '50%',
                alignItems: 'center', justifyContent: 'center',
                background: 'var(--color-bg-elevated)', opacity: 0.9,
                border: '1px solid var(--color-border)',
                color: '#FFB25C', cursor: 'pointer',
              }}
            >
              <RotateCw size={17} />
            </button>
          )}
          {product.is_featured && (
            <div style={{
              position: 'absolute', top: 8, right: 8,
              background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)',
              fontSize: 9, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
            }}>پرفروش</div>
          )}
          {(product.discount_percent || 0) > 0 && (
            <div style={{
              position: 'absolute', top: 8, left: 8,
              background: 'rgba(248,113,113,0.15)', color: 'var(--color-danger)',
              border: '1px solid rgba(248,113,113,0.4)',
              fontSize: 9, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
            }}>٪{Number(product.discount_percent).toLocaleString('fa-IR')} تخفیف</div>
          )}
        </div>
        <div style={{ padding: '10px 12px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 10, color: T3, marginBottom: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {product.category_name || product.category?.name || 'قطعات دوربین'}
          </div>
          <div style={{
            fontSize: 'clamp(12px, 2vw, 13px)', color: T1,
            fontWeight: 600, marginBottom: 4, lineHeight: 1.4, direction: 'rtl',
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>{product.name}</div>
          {product.model_number && (
            <div dir="ltr" style={{
              direction: 'ltr', textAlign: 'right',
              fontSize: 'clamp(13px, 2vw, 15px)', fontWeight: 800, color: T2,
              fontFamily: MONO, letterSpacing: 0.5, marginBottom: 8,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>{product.model_number}</div>
          )}
          {/* چیپ‌های مشخصات — زیر مدل محصول؛ جا نشد می‌رود خط بعد */}
          {specChips.some(c => c.v) && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 'auto', marginBottom: 8, direction: 'rtl' }}>
              {specChips.filter(c => c.v).map((c, i) => (
                <span key={i} dir={c.lat ? 'ltr' : undefined} style={{
                  fontSize: 13, padding: '3px 10px', borderRadius: 999,
                  fontFamily: c.lat ? MONO : undefined,
                  whiteSpace: 'nowrap',
                  background: c.gray ? 'var(--color-bg-tertiary)' : 'rgba(251,192,45,0.12)',
                  color: c.gray ? T3 : 'var(--color-brand)',
                }}>{c.v}</span>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', direction: 'rtl' }}>
            {price ? (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {product.min_price_original && (
                  <span style={{ fontSize: 10, color: T3, textDecoration: "line-through" }}>
                    {Number(product.min_price_original).toLocaleString('fa-IR')}
                  </span>
                )}
                <span style={{ fontSize: 'clamp(12px, 2vw, 14px)', fontWeight: 700, color: B }}>
                  {Number(price).toLocaleString('fa-IR')} ریال
                </span>
              </div>
            ) : (
              <span style={{ fontSize: 11, color: B }}>استعلام قیمت</span>
            )}
            {/* دکمه مقایسه — مشابه کارت صفحه محصولات */}
            <button
              onClick={handleCompare}
              aria-label={compared ? 'حذف از مقایسه' : 'افزودن به مقایسه'}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 11, padding: '6px 10px', borderRadius: 10,
                border: `1px solid ${compared ? 'var(--color-brand)' : 'var(--color-border-strong)'}`,
                background: compared ? 'var(--color-brand-soft)' : 'transparent',
                color: compared ? 'var(--color-brand)' : 'var(--color-text-secondary)',
                cursor: 'pointer', transition: 'all 0.2s', flexShrink: 0,
              }}
            >
              <Scale size={13} />
              <span>مقایسه</span>
            </button>
          </div>
        </div>
      </div>
    </Link>
  )
}

// ─── تیتر انگلیسی کوچک سکشن ─────────────────────────────────────
function SectionTag({ children }) {
  return (
    <div style={{ fontSize: 11, color: B, letterSpacing: '3px', marginBottom: 12, fontFamily: MONO, opacity: 0.85 }}>
      {children}
    </div>
  )
}

// روی دستگاه‌های کم‌توان کنواس فقط یک فریم ثابت می‌کشد — چانک کوچک آن بلافاصله
// لود می‌شود تا فریم ثابت هیرو زود نقش ببندد و فیلم‌استریپ زودتر settle شود
// (به‌تاخیر انداختن آن تا idle، تغییر پیکسلی دیررس و SI بالا می‌ساخت)
function LazyBoardCanvas() {
  return <Suspense fallback={null}><BoardCanvas /></Suspense>
}

// ─── ردیف دسته‌بندی‌ها — کوئری و رندر هر دو با نزدیک‌شدن به ویوپورت ───
function CategoriesRow() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: categoriesData } = useQuery({
    queryKey: ['home-categories'],
    queryFn: () => api.get('/catalog/categories/').then(r => r.data).catch(() => null),
    enabled: inView && afterLoad,
  })
  const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData?.results || [])
  return (
    <div ref={ref}>
      {inView && categories.length > 0 && (
        <Section>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px) clamp(40px, 8vw, 60px)' }}>
            <div className="no-scrollbar" style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 8, direction: 'rtl' }}>
              {categories.map((c, i) => {
                const CatIcon = CATEGORY_ICON[c.category_type] || CATEGORY_ICON.other
                return (
                <Link key={c.id || i} to={`/categories/${c.slug || c.id}`} style={{ textDecoration: 'none', flexShrink: 0 }}>
                  <div className="glass" style={{ display: 'flex', alignItems: 'center', gap: 10, borderRadius: 14, padding: '12px 20px', transition: 'all 0.25s ease' }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-brand)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.transform = '' }}
                  >
                    <CatIcon size={18} color={B} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: T1, whiteSpace: 'nowrap' }}>{c.name}</span>
                    {c.product_count != null && (
                      <span style={{ fontSize: 10, color: B }}>({Number(c.product_count).toLocaleString('fa-IR')})</span>
                    )}
                  </div>
                </Link>
                )
              })}
            </div>
          </div>
        </Section>
      )}
    </div>
  )
}

// ─── SPECIAL OFFERS — محصولات تخفیف‌دار ───
// محصولات تخفیف‌دار جدا از صفحه اول محصولات گرفته می‌شود تا هر ۶ تای اول مستقل از ترتیب کلی بیایند
function DiscountedSection() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: discountedData } = useQuery({
    queryKey: ['home-discounted'],
    queryFn: () => api.get('/catalog/products/?is_active=true&discounted=true').then(r => r.data).catch(() => null),
    enabled: inView && afterLoad,
  })
  const discountedProducts = (discountedData?.results || []).slice(0, 6)
  return (
    <div ref={ref}>
      {inView && discountedProducts.length > 0 && (
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px) clamp(60px, 12vw, 100px)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 'clamp(28px, 5vw, 48px)', direction: 'rtl', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <SectionTag>SPECIAL OFFERS</SectionTag>
              <h2 style={{ fontSize: 'clamp(20px, 4vw, 40px)', fontWeight: 800, color: T1 }}>تخفیفات ویژه</h2>
            </div>
            <Link to="/products?discounted=true" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              color: B, textDecoration: 'none', fontSize: 13,
              border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '8px 20px',
            }}>
              مشاهده همه
              <ArrowLeft size={13} />
            </Link>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(160px, 100%), 1fr))', gap: 'clamp(12px, 2vw, 20px)' }}>
            {discountedProducts.map((p, i) => (
              <Section key={p.id} delay={i * 60} style={{ height: '100%' }}><ProductCard product={p}/></Section>
            ))}
          </div>
        </div>
      </Section>
      )}
    </div>
  )
}

// ─── FEATURED PRODUCTS — پرفروش‌ترین قطعات ───
function FeaturedSection() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: productsData } = useQuery({
    queryKey: ['home-products'],
    queryFn: () => api.get('/catalog/products/?is_active=true').then(r => r.data),
    enabled: inView && afterLoad,
  })
  const products = productsData?.results || []
  return (
    <div ref={ref}>
      {inView && (
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px) clamp(60px, 12vw, 100px)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 'clamp(28px, 5vw, 48px)', direction: 'rtl', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <SectionTag>FEATURED PRODUCTS</SectionTag>
              <h2 style={{ fontSize: 'clamp(20px, 4vw, 40px)', fontWeight: 800, color: T1 }}>پرفروش‌ترین قطعات</h2>
            </div>
            <Link to="/products" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              color: B, textDecoration: 'none', fontSize: 13,
              border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '8px 20px',
            }}>
              مشاهده همه
              <ArrowLeft size={13} />
            </Link>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(160px, 100%), 1fr))', gap: 'clamp(12px, 2vw, 20px)' }}>
            {(() => {
              const featured = products.filter(p => p.is_featured)
              const list = (featured.length > 0 ? featured : products.filter(p => !(p.discount_percent > 0))).slice(0, 18)
              return list.length > 0 ? list.map((p, i) => (
                <Section key={p.id} delay={i * 60} style={{ height: '100%' }}><ProductCard product={p}/></Section>
              )) : (
                [...Array(8)].map((_, i) => (
                  <GlassCard key={i} hover={false} style={{ overflow: 'hidden' }}>
                    <div className="skeleton" style={{ aspectRatio: '1/1', borderRadius: 0 }}/>
                    <div style={{ padding: '14px 16px' }}>
                      <div className="skeleton" style={{ height: 10, marginBottom: 8, width: '60%' }}/>
                      <div className="skeleton" style={{ height: 14 }}/>
                    </div>
                  </GlassCard>
                ))
              )
            })()}
          </div>
        </div>
      </Section>
      )}
    </div>
  )
}

// ─── پکیج‌ها — فقط با داده واقعی (بدون محتوای جعلی برای خزنده‌ها) ───
function PackagesSection() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: packagesData } = useQuery({
    queryKey: ['home-packages'],
    queryFn: () => api.get('/catalog/packages/').then(r => r.data).catch(() => null),
    enabled: inView && afterLoad,
  })
  const packages = Array.isArray(packagesData) ? packagesData : (packagesData?.results || [])
  return (
    <div ref={ref}>
      {inView && packages.length > 0 && (
      <Section>
        <div style={{
          background: 'linear-gradient(180deg,transparent,var(--color-brand-softer) 50%,transparent)',
          padding: 'clamp(60px, 12vw, 100px) 0',
        }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px)' }}>
            <div style={{ textAlign: 'center', marginBottom: 'clamp(32px, 6vw, 56px)' }}>
              <SectionTag>PACKAGES</SectionTag>
              <h2 style={{ fontSize: 'clamp(20px, 4vw, 40px)', fontWeight: 800, color: T1, marginBottom: 12 }}>پکیج‌های آماده</h2>
              <p style={{ fontSize: 'clamp(13px, 2vw, 14px)', color: T2, maxWidth: 480, margin: '0 auto', lineHeight: 1.8, padding: '0 8px' }}>
                ست‌های کامل قطعات برای راه‌اندازی سیستم دوربین مداربسته
              </p>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(320px, 100%), 1fr))',
              gap: 'clamp(16px, 3vw, 24px)', maxWidth: 1100, margin: '0 auto',
            }}>
              {(() => {
                return packages.slice(0, 3).map((pkg, i) => {
                  const pkgImg = mediaUrl(pkg.image)
                  const pkgPrice = pkg.final_price || pkg.total_price
                  return (
                <Section key={pkg.id || i} delay={i * 100}>
                  <GlassCard style={{ padding: 0, position: 'relative', overflow: 'hidden', height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <div style={{
                      aspectRatio: '16/10', background: 'linear-gradient(135deg,var(--color-brand-soft),var(--color-bg-tertiary))',
                      position: 'relative', overflow: 'hidden',
                    }}>
                      {pkgImg ? (
                        <img src={pkgImg} alt={pkg.name} loading="lazy" decoding="async" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                      ) : (
                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: T3, opacity: 0.4 }}>
                          <Box size={44} strokeWidth={1.2} />
                        </div>
                      )}
                      {(pkg._tag || i === 1) && (
                        <div style={{
                          position: 'absolute', top: 10, left: 10,
                          background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)',
                          fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 100,
                        }}>{pkg._tag || 'پیشنهاد ویژه'}</div>
                      )}
                    </div>
                    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', flex: 1 }}>
                      <h3 style={{ fontSize: 16, fontWeight: 700, color: T1, marginBottom: 8, lineHeight: 1.4 }}>{pkg.name}</h3>
                      <p style={{ fontSize: 12, color: T2, lineHeight: 1.6, marginBottom: 16, flex: 1,
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                      }}>{pkg.description}</p>
                      {pkgPrice && (
                        <div style={{ fontSize: 18, fontWeight: 700, color: B, marginBottom: 16 }}>
                          {Number(pkgPrice).toLocaleString('fa-IR')} ریال
                        </div>
                      )}
                      <Link to={`/packages/${pkg.slug || pkg.id}`} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 8,
                        alignSelf: 'flex-start',
                        background: i === 1 ? 'var(--gradient-gold)' : BS,
                        color: i === 1 ? 'var(--color-brand-contrast)' : B, textDecoration: 'none',
                        border: i === 1 ? 'none' : '1px solid var(--color-border-strong)',
                        borderRadius: 10, padding: '10px 20px', fontSize: 12, fontWeight: 600,
                      }}>مشاهده پکیج <ArrowLeft size={13} /></Link>
                    </div>
                  </GlassCard>
                </Section>
                  )
                })
              })()}
            </div>
          </div>
        </div>
      </Section>
      )}
    </div>
  )
}

// ─── مقالات — فقط با داده واقعی ───
// سکشن پین‌شده‌ی مقالات — تا رسیدن به آن، اسکرول عمودی به ورق زدن افقی تبدیل می‌شود
function ArticlesSection() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: articlesData } = useQuery({
    queryKey: ['home-articles'],
    queryFn: () => api.get('/education/articles/').then(r => r.data).catch(() => null),
    enabled: inView && afterLoad,
  })
  const articles = Array.isArray(articlesData) ? articlesData : (articlesData?.results || [])

  const artPinRef = useRef(null)
  const artTrackRef = useRef(null)
  useEffect(() => {
    const wrap = artPinRef.current
    const track = artTrackRef.current
    if (!wrap || !track) return
    let raf = null
    const clamp01 = (v) => Math.min(1, Math.max(0, v))
    const update = () => {
      raf = null
      const total = wrap.offsetHeight - window.innerHeight
      const p = total > 0 ? clamp01(-wrap.getBoundingClientRect().top / total) : 0
      const viewport = track.parentElement
      const maxShift = Math.max(0, track.scrollWidth - viewport.clientWidth)
      track.style.transform = `translate3d(${-p * maxShift}px, 0, 0)`
      // کارت نزدیک مرکز بزرگ‌تر و واضح‌تر — کارت‌های کنار کوچک‌تر و کم‌رنگ‌تر
      const cx = window.innerWidth / 2
      track.querySelectorAll('.art-float-card').forEach((c) => {
        const r = c.getBoundingClientRect()
        const t = Math.min(Math.abs(r.left + r.width / 2 - cx) / (window.innerWidth * 0.55), 1)
        c.style.transform = `translateY(${Math.round(t * 22)}px) scale(${(1 - 0.22 * t).toFixed(3)})`
        c.style.opacity = (1 - 0.35 * t).toFixed(3)
      })
    }
    const onScroll = () => { if (raf == null) raf = requestAnimationFrame(update) }
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    update()
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [articles.length])

  return (
    <div ref={ref}>
      {inView && articles.length > 0 && (
      <div className="art-pin-wrap" ref={artPinRef}>
        <div className="art-pin-sticky">
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 'clamp(28px, 5vw, 48px)', direction: 'rtl', flexWrap: 'wrap', gap: 12, padding: '0 clamp(16px, 4vw, 40px)' }}>
            <div>
              <SectionTag>ARTICLES</SectionTag>
              <h2 style={{ fontSize: 'clamp(20px, 4vw, 40px)', fontWeight: 800, color: T1 }}>مقالات آموزشی</h2>
            </div>
            <Link to="/blog" style={{ color: B, textDecoration: 'none', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '8px 20px', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              همه مقالات <ArrowLeft size={13} />
            </Link>
          </div>

          <div className="art-row-viewport" dir="ltr">
            <div className="art-row-track" ref={artTrackRef}>
            {articles.slice(0, 6).map((a, i) => {
              const thumb = mediaUrl(a.thumbnail)
              const catName = typeof a.category === 'string' ? a.category : (a.category?.name || 'مقاله')
              return (
              <div className="art-float-card" key={`${a.id || i}-${i}`} dir="rtl">
              <Section delay={(i % 6) * 80}>
                <Link to={`/blog/${a.slug || a.id}`} style={{ textDecoration: 'none' }}>
                  <GlassCard style={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <div style={{
                      aspectRatio: '16/9', background: 'linear-gradient(135deg,var(--color-brand-soft),var(--color-bg-tertiary))',
                      position: 'relative', overflow: 'hidden',
                    }}>
                      {thumb ? (
                        <img src={thumb} alt={a.title} loading="lazy" decoding="async" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                      ) : (
                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: T3, opacity: 0.4 }}>
                          <CircuitBoard size={44} strokeWidth={1.2} />
                        </div>
                      )}
                    </div>
                    <div style={{ padding: 22, display: 'flex', flexDirection: 'column', flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 12, direction: 'rtl' }}>
                        <span style={{ fontSize: 10, color: B, background: BST, border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '3px 10px' }}>
                          {catName}
                        </span>
                        {a.read_time && (
                          <span style={{ fontSize: 10, color: T3, padding: '3px 10px' }}>
                            {a.read_time} دقیقه مطالعه
                          </span>
                        )}
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, color: T1, marginBottom: 10, lineHeight: 1.5, direction: 'rtl', flex: 1 }}>{a.title}</h3>
                      <p style={{
                        fontSize: 13, color: T2, lineHeight: 1.7,
                        direction: 'rtl', marginBottom: 16,
                        display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                      }}>{a.description || a.summary}</p>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', color: B, fontSize: 12, gap: 6 }}>
                        ادامه مطلب <ArrowLeft size={13} />
                      </div>
                    </div>
                  </GlassCard>
                </Link>
              </Section>
              </div>
              )
            })}
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
  )
}

// ─── ویدیوها — فقط با داده واقعی ───
function VideosSection() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: videosData } = useQuery({
    queryKey: ['home-videos'],
    queryFn: () => api.get('/education/videos/').then(r => r.data).catch(() => null),
    enabled: inView && afterLoad,
  })
  const videos = Array.isArray(videosData) ? videosData : (videosData?.results || [])
  return (
    <div ref={ref}>
      {inView && videos.length > 0 && (
      <Section>
        <div style={{
          background: 'linear-gradient(180deg,transparent,var(--color-brand-softer) 50%,transparent)',
          padding: 'clamp(60px, 12vw, 100px) 0',
        }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 'clamp(28px, 5vw, 48px)', direction: 'rtl', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <SectionTag>VIDEO TUTORIALS</SectionTag>
                <h2 style={{ fontSize: 'clamp(20px, 4vw, 40px)', fontWeight: 800, color: T1 }}>ویدیوهای آموزشی</h2>
              </div>
              <Link to="/videos" style={{ color: B, textDecoration: 'none', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '8px 20px', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                همه ویدیوها <ArrowLeft size={13} />
              </Link>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(280px, 100%), 1fr))', gap: 'clamp(16px, 3vw, 24px)' }}>
              {(videos.slice(0, 3)).map((v, i) => {
                const vThumb = mediaUrl(v.thumbnail)
                return (
                <Section key={v.id || i} delay={i * 100}>
                  <Link to={`/videos/${v.slug || v.id}`} style={{ textDecoration: 'none' }}>
                    <GlassCard style={{ overflow: 'hidden' }}>
                      <div style={{
                        aspectRatio: '16/9',
                        background: 'linear-gradient(135deg,var(--color-brand-soft),var(--color-bg-tertiary))',
                        position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {vThumb ? (
                          <img src={vThumb} alt={v.title} loading="lazy" decoding="async" style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                        ) : (
                          <Play size={40} color={T3} style={{ opacity: 0.4 }} />
                        )}
                        <div style={{
                          position: 'absolute', width: 52, height: 52,
                          borderRadius: '50%', background: 'var(--gradient-gold)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          boxShadow: '0 0 25px rgba(251,192,45,0.45)',
                        }}>
                          <Play size={20} color="var(--color-brand-contrast)" fill="var(--color-brand-contrast)" />
                        </div>
                        {v.duration && (
                          <div style={{
                            position: 'absolute', bottom: 10, left: 10,
                            background: 'rgba(0,0,0,0.75)', color: '#fff', fontSize: 11,
                            padding: '2px 8px', borderRadius: 4, fontFamily: MONO,
                          }}>{v.duration}</div>
                        )}
                      </div>
                      <div style={{ padding: '16px 18px', direction: 'rtl' }}>
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: T1, lineHeight: 1.5 }}>{v.title}</h3>
                      </div>
                    </GlassCard>
                  </Link>
                </Section>
                )
              })}
            </div>
          </div>
        </div>
      </Section>
      )}
    </div>
  )
}

// ─── سوالات متداول — متن قابل‌خزش + FAQPage schema ───
function FaqSection() {
  const [ref, inView] = useInViewOnce()
  const afterLoad = useAfterLoad()
  const { data: faqsData } = useQuery({
    queryKey: ['home-faqs'],
    queryFn: () => api.get('/assistant/faqs/').then(r => r.data).catch(() => null),
    enabled: inView && afterLoad,
  })
  const faqs = Array.isArray(faqsData) ? faqsData : (faqsData?.results || [])
  // اسکیمای Organization/WebSite/Store به‌صورت استاتیک در index.html است
  // (تا خزنده‌های بدون JS هم ببینند) — اینجا فقط FAQPage پویا اضافه می‌شود.
  const faqLd = faqs.length > 0 ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(f => ({
      '@type': 'Question',
      name: f.question,
      acceptedAnswer: { '@type': 'Answer', text: f.answer },
    })),
  } : null
  return (
    <div ref={ref}>
      {faqLd && <Seo jsonLd={faqLd} />}
      {inView && faqs.length > 0 && (
      <Section>
        <div style={{ maxWidth: 820, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px) clamp(48px, 10vw, 80px)' }}>
          <div style={{ textAlign: 'center', marginBottom: 'clamp(28px, 5vw, 40px)' }}>
            <SectionTag>FAQ</SectionTag>
            <h2 style={{ fontSize: 'clamp(20px, 4vw, 40px)', fontWeight: 800, color: T1 }}>سوالات متداول</h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {faqs.slice(0, 5).map(f => (
              <details key={f.id} style={{
                background: 'var(--glass-bg)', backdropFilter: 'blur(16px)',
                border: '1px solid var(--color-border)', borderRadius: 14,
                padding: '16px 20px',
              }}>
                <summary style={{ cursor: 'pointer', fontSize: 'clamp(13px, 2vw, 14px)', fontWeight: 700, color: T1, lineHeight: 1.7 }}>
                  {f.question}
                </summary>
                <p style={{ fontSize: 'clamp(12px, 1.8vw, 13px)', color: T2, lineHeight: 1.9, marginTop: 12, whiteSpace: 'pre-line' }}>
                  {f.answer}
                </p>
              </details>
            ))}
          </div>
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Link to="/china-order/faq" style={{ color: B, textDecoration: 'none', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 100, padding: '8px 20px', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              همه سوالات متداول <ArrowLeft size={13} />
            </Link>
          </div>
        </div>
      </Section>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
// HOMEPAGE — SENTINEL
// بدنه بدون state/کوئری — هر سکشن داده‌دار کامپوننت مستقل خودش است تا
// رندرهای مجدد (لود داده/ورود به ویوپورت) به همان سکشن محدود بماند و
// کل صفحه دوباره reconcile نشود
// ═══════════════════════════════════════════════════════════════════
export default function HomePage() {
  return (
    <div style={{ direction: 'rtl', color: T1 }}>
      <Seo
        title="دوربینکار | فروشگاه آنلاین قطعات دوربین مداربسته"
        description="فروشگاه تخصصی قطعات دوربین مداربسته — برد، لنز، سنسور، مودم و بدنه با قیمت همکار؛ جستجوی هوشمند و ربات مشاور برای انتخاب قطعه سازگار، ارسال به سراسر ایران."
        canonical="/"
        image="/icons/icon-512.png"
        geoTags={['تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج']}
      />

      {/* ══════════════════════════════════════════════
          HERO — افکت برد بازگشتی (چپ) + متن و باکس هوشمند (راست)
      ══════════════════════════════════════════════ */}
      <section className="hero-board" style={{ position: 'relative', overflow: 'hidden', minHeight: '92vh', display: 'flex', alignItems: 'center' }}>
        {/* بک‌گراند متحرک — دای سیلیکون که سلول‌به‌سلول از بردهای واقعی ساخته می‌شود */}
        <LazyBoardCanvas />

        <div style={{
          position: 'relative', zIndex: 2, width: '100%',
          maxWidth: 1280, margin: '0 auto',
          padding: 'clamp(48px, 10vh, 96px) clamp(16px, 4vw, 40px) clamp(64px, 12vh, 110px)',
          display: 'flex', justifyContent: 'flex-start',
        }}>
          {/* ستون متن — در جریان RTL سمت راست صفحه می‌نشیند */}
          <div style={{ maxWidth: 700, width: '100%' }}>

            {/* تیتر — بدون انیمیشن ورود: تاخیر انیمیشن، LCP را به تاخیر می‌انداخت و
                با اسپلش استاتیک (که متن ثابت دارد) ناهماهنگی فلش ایجاد می‌کرد */}
            <h1 className="hero-text" style={{ fontWeight: 900, lineHeight: 1.35, margin: 0 }}>
              <span style={{ display: 'block', fontSize: 'clamp(34px, 5.2vw, 62px)', color: T1 }}>
                قطعات دوربین مداربسته‌ات رو راحت پیدا کن
              </span>
              <span className="gold-text" style={{ display: 'block', fontSize: 'clamp(29px, 4.3vw, 52px)' }}>
                بسپارش به ربات هوشمند دوربینکار
              </span>
            </h1>

            {/* زیرتیتر — معرفی دو ویژگی کلیدی */}
            <p className="hero-text" style={{ fontSize: 'clamp(15px, 1.8vw, 18px)', color: T2, lineHeight: 2, maxWidth: 640, margin: '24px 0 0' }}>
              بین هزاران قطعه با <b style={{ color: T1 }}>جستجوی پیشرفته</b> دقیقاً همان چیزی را که می‌خواهی پیدا کن — مدل، چیپست، برند.
              اگر مطمئن نیستی، <b style={{ color: T1 }}>ربات مشاور</b> در انتخاب قطعه مناسب، مچ کردن لنز و برد و پاسخ به سوالات فنی کمکت می‌کند.
              فقط کافیه توی کادر زیر هر سوالی داری ازش بپرسی.
            </p>

            {/* باکس جستجو و مشاوره هوشمند — بلافاصله زیر متن، در مسیر نگاه کاربر */}
            <div className="animate-slide-up" style={{ animationDelay: '220ms', marginTop: 30 }}>
              <Suspense fallback={
                <div className="liquid-metal-frame" style={{ boxShadow: 'var(--shadow-card-hover), 0 0 60px rgba(251,192,45,0.10)' }}>
                  <div className="liquid-metal-inner">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', minHeight: 56 }}>
                      <span style={{ flex: 1, color: 'var(--color-text-muted)', fontSize: 14, lineHeight: 1.9 }}>مثلاً بپرس: لنز دارک لایت چی داری؟</span>
                    </div>
                  </div>
                </div>
              }>
                <SmartSearch />
              </Suspense>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════
          نوار برندها — مارکی لوگوها
      ══════════════════════════════════════════════ */}
      <Deferred>
        <Section>
          <BrandMarquee />
        </Section>
      </Deferred>

      {/* ══════════════════════════════════════════════
          دسته‌بندی‌ها
      ══════════════════════════════════════════════ */}
      <CategoriesRow />

      {/* ══════════════════════════════════════════════
          معرفی دوربینکار — متن قابل‌خزش برای موتورهای جستجو و AI
      ══════════════════════════════════════════════ */}
      <Deferred>
      <Section>
        <div className="about-hero">
          {/* دو بک‌گراند ترکیبی: دفتر چین + کانتینر — تصاویر در public/images */}
          <div className="about-hero-bg" aria-hidden="true">
            <img className="about-hero-img" src="/images/about-container-mobile.webp" alt="" fetchPriority="high" decoding="async" />
            <div className="about-hero-layer about-hero-office" />
            <div className="about-hero-layer about-hero-container" />
            <div className="about-hero-scrim" />
          </div>
          <div style={{ position: 'relative', maxWidth: 820, margin: '0 auto', padding: 'clamp(64px, 12vw, 120px) clamp(16px, 4vw, 40px)' }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <SectionTag>ABOUT DOORBINKAR</SectionTag>
            <h2 style={{ fontSize: 'clamp(20px, 4vw, 36px)', fontWeight: 800, color: T1 }}>
              دوربینکار؛ مرجع تخصصی قطعات دوربین مداربسته در ایران
            </h2>
          </div>
          <div style={{ fontSize: 'clamp(13px, 2vw, 15px)', color: T2, lineHeight: 1.9 }}>
            <p style={{ marginBottom: 16 }}>
              دوربینکار فروشگاه تخصصی <b style={{ color: T1 }}>قطعات دوربین مداربسته</b> است — مرجع مونتاژکاران، تعمیرکاران و نصاب‌های حرفه‌ای در سراسر ایران. ما برد دوربین، لنز، سنسور تصویر، مودم، بدنه و متعلقات را مستقیم و بدون واسطه از کارخانه‌های چین و تایوان تأمین می‌کنیم تا قطعه اصل با قیمت واقعی کارخانه به دست شما برسد.
            </p>
            <p style={{ marginBottom: 16 }}>
              چیزی که دوربینکار را از بقیه جدا می‌کند، <b style={{ color: T1 }}>جستجوی هوشمند و ربات مشاور</b> است: به‌جای ساعت‌ها گشتن بین کاتالوگ‌ها، مدل برد یا سنسورتان را بنویسید تا قطعه سازگار دقیقاً پیدا شود — یا سوال فنی‌تان را از ربات مشاور بپرسید تا در انتخاب برد، مچ کردن لنز و سنسور و حتی عیب‌یابی راهنمایی‌تان کند. این دستیار تخصصی همان چیزی است که انتخاب قطعه را برای همکاران ما سریع و مطمئن کرده است.
            </p>
            <p style={{ marginBottom: 16 }}>
              بیش از ۳۰ سال تجربه در بازار دوربین مداربسته پشت این مجموعه است؛ همه قطعات قبل از ارسال کنترل فنی می‌شوند، همکاران (مونتاژکاران و فروشندگان) از قیمت ویژه و اعتبار خرید بهره‌مند می‌شوند و اگر قطعه‌ای در انبار نبود، مستقیم از کارخانه چین برایتان سفارش می‌دهیم.
            </p>
            <p style={{ fontSize: 'clamp(12px, 1.8vw, 13px)' }}>
              <Link to="/products" style={{ color: B, textDecoration: 'none' }}>مشاهده همه قطعات</Link>
              {' · '}
              <Link to="/packages" style={{ color: B, textDecoration: 'none' }}>پکیج‌های آماده</Link>
              {' · '}
              <Link to="/blog" style={{ color: B, textDecoration: 'none' }}>مقالات آموزشی</Link>
              {' · '}
              <Link to="/china-order" style={{ color: B, textDecoration: 'none' }}>سفارش از چین</Link>
            </p>
          </div>
          </div>
        </div>
      </Section>
      </Deferred>

      {/* ══════════════════════════════════════════════
          چرا ما؟
      ══════════════════════════════════════════════ */}
      <Deferred>
      <Section>
        <div id="why-us" style={{ maxWidth: 1280, margin: '0 auto', padding: 'clamp(40px, 8vw, 60px) clamp(16px, 4vw, 40px) clamp(60px, 12vw, 100px)' }}>
          <div style={{ textAlign: 'center', marginBottom: 'clamp(32px, 6vw, 64px)' }}>
            <SectionTag>WHY CHOOSE US</SectionTag>
            <h2 style={{ fontSize: 'clamp(22px, 4vw, 44px)', fontWeight: 800, color: T1, marginBottom: 14 }}>
              چرا باید با ما کار کنید؟
            </h2>
            <p style={{ fontSize: 'clamp(13px, 2vw, 15px)', color: T2, maxWidth: 560, margin: '0 auto', lineHeight: 1.8, padding: '0 8px' }}>
              ۳۰ سال تجربه در تأمین قطعات اصل — مستقیم از کارخانه‌های چین و تایوان
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(180px, 100%), 1fr))', gap: 'clamp(14px, 2vw, 20px)' }}>
            {[
              { icon: Factory, title: 'مستقیم از کارخانه', desc: 'بدون واسطه — قیمت واقعی کارخانه با ضمانت اصالت کالا' },
              { icon: Zap, title: 'تحویل سریع', desc: 'تحویل اکسپرس ۴۸ ساعته از انبار تهران برای سفارش‌های آماده' },
              { icon: Microscope, title: 'کنترل کیفیت', desc: 'تمام محصولات قبل از ارسال کنترل فنی و تست می‌شوند' },
              { icon: Handshake, title: 'پشتیبانی تخصصی', desc: 'تیم فنی متخصص برای راهنمایی انتخاب و نصب قطعات' },
              { icon: Gem, title: 'قیمت رقابتی', desc: 'بهترین قیمت بازار با تضمین برگشت وجه در صورت عدم رضایت' },
              { icon: Globe, title: 'سفارش از چین', desc: 'خرید سفارشی مستقیم از کارخانه‌های چین با تحویل ۲–۳ هفته' },
            ].map((f, i) => (
              <Section key={i} delay={i * 80}>
                <GlassCard style={{ padding: 'clamp(20px, 3vw, 28px)', height: '100%' }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: 14, marginBottom: 16,
                    background: BS, border: '1px solid var(--color-border-strong)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <f.icon size={22} color={B} />
                  </div>
                  <div style={{ fontSize: 'clamp(14px, 2vw, 15px)', fontWeight: 700, color: T1, marginBottom: 10 }}>{f.title}</div>
                  <div style={{ fontSize: 'clamp(12px, 1.8vw, 13px)', color: T2, lineHeight: 1.7 }}>{f.desc}</div>
                </GlassCard>
              </Section>
            ))}
          </div>
        </div>
      </Section>
      </Deferred>

      {/* ══════════════════════════════════════════════
          محصولات — تخفیف‌دار و پرفروش‌ترین
      ══════════════════════════════════════════════ */}
      <DiscountedSection />
      <FeaturedSection />

      {/* ══════════════════════════════════════════════
          پکیج‌ها
      ══════════════════════════════════════════════ */}
      <PackagesSection />

      {/* ══════════════════════════════════════════════
          عضویت همکار CTA
      ══════════════════════════════════════════════ */}
      <Deferred>
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px) clamp(60px, 12vw, 100px)' }}>
          <div style={{
            position: 'relative', borderRadius: 'clamp(20px, 4vw, 28px)', overflow: 'hidden',
            background: 'linear-gradient(135deg, var(--color-brand-soft) 0%, var(--color-bg-card) 60%)',
            border: '1px solid var(--color-border-strong)',
            padding: 'clamp(32px, 6vw, 64px) clamp(20px, 4vw, 56px)',
          }}>
            <div style={{ position: 'absolute', top: -60, right: -60, width: 300, height: 300, borderRadius: '50%', background: 'rgba(251,192,45,0.12)', filter: 'blur(70px)', pointerEvents: 'none' }}/>
            <div style={{ position: 'absolute', bottom: -60, left: -60, width: 250, height: 250, borderRadius: '50%', background: 'rgba(251,192,45,0.07)', filter: 'blur(60px)', pointerEvents: 'none' }}/>

            <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: '1fr auto', gap: 'clamp(20px, 4vw, 40px)', alignItems: 'center', direction: 'rtl' }}>
              <div>
                <SectionTag>PARTNER PROGRAM</SectionTag>
                <h2 style={{ fontSize: 'clamp(20px, 4vw, 42px)', fontWeight: 800, color: T1, marginBottom: 14, lineHeight: 1.2 }}>
                  همکار ما شوید<br/>
                  <span className="gold-text">قیمت ویژه همکاری</span> دریافت کنید
                </h2>
                <p style={{ fontSize: 'clamp(13px, 2vw, 14px)', color: T2, lineHeight: 1.8, maxWidth: 500, marginBottom: 28 }}>
                  با ثبت‌نام به عنوان همکار از قیمت‌های ویژه، اعتبار خرید، پشتیبانی اختصاصی و
                  دسترسی به کاتالوگ کامل محصولات بهره‌مند شوید.
                </p>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {['قیمت ویژه همکاری', 'پشتیبانی اختصاصی', 'اعتبار خرید', 'کاتالوگ کامل'].map(b => (
                    <span key={b} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      background: BST, border: '1px solid var(--color-border-strong)',
                      borderRadius: 100, padding: '5px 14px', fontSize: 'clamp(11px, 1.8vw, 12px)', color: B,
                    }}>
                      <Check size={12} /> {b}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 'min(180px, 100%)' }}>
                <Link to="/partner" className="btn-gold" style={{
                  textDecoration: 'none', borderRadius: 14,
                  padding: '14px 24px', fontSize: 'clamp(13px, 2vw, 15px)', whiteSpace: 'nowrap',
                  boxShadow: '0 8px 32px rgba(251,192,45,0.3)',
                }}>ثبت‌نام همکار</Link>
                <Link to="/partner" style={{
                  display: 'block', textAlign: 'center',
                  background: 'var(--color-bg-elevated)', color: T2,
                  textDecoration: 'none', border: '1px solid var(--color-border)',
                  borderRadius: 14, padding: '12px 24px', fontSize: 13, whiteSpace: 'nowrap',
                }}>اطلاعات بیشتر درباره همکاری</Link>
              </div>
            </div>
          </div>
        </div>
      </Section>
      </Deferred>

      {/* ══════════════════════════════════════════════
          مقالات و ویدیوها
      ══════════════════════════════════════════════ */}
      <ArticlesSection />
      <VideosSection />

      {/* ══════════════════════════════════════════════
          سوالات متداول
      ══════════════════════════════════════════════ */}
      <FaqSection />

      {/* ══════════════════════════════════════════════
          سفارش از چین — مراحل
      ══════════════════════════════════════════════ */}
      <Deferred>
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 clamp(16px, 4vw, 40px) clamp(60px, 12vw, 100px)' }}>
          <GlassCard style={{
            padding: 'clamp(28px, 5vw, 64px) clamp(20px, 4vw, 56px)',
            background: 'linear-gradient(135deg, var(--color-brand-soft), var(--color-bg-card))',
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(280px, 100%), 1fr))',
            gap: 'clamp(24px, 5vw, 60px)', alignItems: 'center',
          }}>
            <div style={{ direction: 'rtl' }}>
              <SectionTag>CHINA ORDER</SectionTag>
              <h2 style={{ fontSize: 'clamp(20px, 4vw, 38px)', fontWeight: 800, color: T1, marginBottom: 14, lineHeight: 1.2 }}>
                قطعه‌ای که نمی‌یابید؟<br/>
                <span className="gold-text">از چین سفارش دهید</span>
              </h2>
              <p style={{ fontSize: 'clamp(13px, 2vw, 14px)', color: T2, lineHeight: 1.8, marginBottom: 28 }}>
                سفارش مستقیم از کارخانه‌های چین — تحویل ۲ تا ۳ هفته.
                ما واردات، گمرک و حمل‌ونقل را مدیریت می‌کنیم.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
                {['سفارش از هر کارخانه چینی', 'مدیریت کامل واردات و گمرک', 'ضمانت تحویل و کیفیت', 'قیمت رقابتی تضمینی'].map(f => (
                  <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 'clamp(12px, 1.8vw, 13px)', color: T1 }}>
                    <div style={{ width: 18, height: 18, borderRadius: '50%', background: BS, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <Check size={10} color={B} />
                    </div>
                    {f}
                  </div>
                ))}
              </div>
              <Link to="/china-order" className="btn-gold" style={{
                textDecoration: 'none', borderRadius: 14,
                padding: '14px 28px', fontSize: 'clamp(13px, 2vw, 15px)',
                boxShadow: '0 8px 32px rgba(251,192,45,0.3)', display: 'inline-flex', gap: 10,
              }}>ثبت سفارش از چین <ArrowLeft size={15} /></Link>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {[
                { step: '۱', title: 'درخواست خود را ثبت کنید', desc: 'مشخصات دقیق قطعه مورد نیاز را وارد کنید' },
                { step: '۲', title: 'دریافت استعلام قیمت', desc: 'ظرف ۲۴ ساعت قیمت و زمان تحویل اعلام می‌شود' },
                { step: '۳', title: 'پرداخت و ثبت سفارش', desc: 'پس از تأیید قیمت، سفارش را نهایی کنید' },
                { step: '۴', title: 'تحویل درب منزل', desc: '۲ تا ۳ هفته — تحویل با ضمانت' },
              ].map((s, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 16, direction: 'rtl' }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                    background: BS,
                    border: '1px solid var(--color-border-strong)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13, fontWeight: 700, color: B, fontFamily: MONO,
                  }}>{s.step}</div>
                  <div>
                    <div style={{ fontSize: 'clamp(13px, 2vw, 14px)', fontWeight: 600, color: T1, marginBottom: 4 }}>{s.title}</div>
                    <div style={{ fontSize: 'clamp(11px, 1.8vw, 12px)', color: T3 }}>{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          CTA نهایی
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{ textAlign: 'center', padding: 'clamp(40px, 8vw, 60px) clamp(16px, 4vw, 40px) clamp(80px, 16vw, 120px)' }}>
          <h2 style={{ fontSize: 'clamp(22px, 5vw, 48px)', fontWeight: 900, color: T1, marginBottom: 14 }}>
            آماده شروع هستید؟
          </h2>
          <p style={{ fontSize: 'clamp(13px, 2vw, 15px)', color: T2, marginBottom: 36, padding: '0 8px' }}>
            همین حالا محصولات را مشاهده کنید یا با ما تماس بگیرید
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/products" className="btn-gold" style={{
              textDecoration: 'none', borderRadius: 14,
              padding: '14px 28px', fontSize: 'clamp(14px, 2vw, 16px)',
              boxShadow: '0 8px 40px rgba(251,192,45,0.35)', display: 'inline-flex', gap: 10,
            }}>مشاهده محصولات</Link>
            <Link to="/contact" className="btn-ghost" style={{
              textDecoration: 'none', borderRadius: 14,
              padding: '14px 28px', fontSize: 'clamp(13px, 2vw, 15px)',
            }}>تماس با ما</Link>
          </div>
        </div>
      </Section>
      </Deferred>
    </div>
  )
}
