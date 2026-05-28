import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import HeroRobot from '../components/home/HeroRobot'

// ─── رنگ‌بندی DOORBINKAR ─────────────────────────────────────────
const Y = '#fbc02d'   // زرد لوگو
const YD = '#f9a825'  // زرد تیره
const YL = '#fdd835'  // زرد روشن

// ─── Animated counter ───────────────────────────────────────────
function Counter({ to, suffix = '', dur = 2000 }) {
  const [v, setV] = useState(0); const ref = useRef(null)
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      const start = Date.now()
      const tick = () => {
        const p = Math.min(1, (Date.now() - start) / dur)
        setV(Math.floor(p * to))
        if (p < 1) requestAnimationFrame(tick)
      }
      tick(); obs.disconnect()
    }, { threshold: 0.5 })
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [to, dur])
  return <span ref={ref}>{v.toLocaleString('fa-IR')}{suffix}</span>
}

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
        background: 'rgba(10,10,12,0.6)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: `1px solid ${hov ? 'rgba(251,192,45,0.3)' : 'rgba(255,255,255,0.07)'}`,
        borderRadius: 20,
        boxShadow: hov
          ? '0 20px 60px rgba(0,0,0,0.6), 0 0 40px rgba(251,192,45,0.08), 0 1px 0 rgba(255,255,255,0.06) inset'
          : '0 8px 32px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.04) inset',
        transform: hov && hover ? 'translateY(-4px)' : 'none',
        transition: 'all 0.3s ease',
        ...style,
      }}
    >{children}</div>
  )
}

// ─── Product Card ────────────────────────────────────────────────
function ProductCard({ product }) {
  const [hov, setHov] = useState(false)
  const price = product.variants?.[0]?.public_price
  const img = product.images?.[0]?.image || product.image
  return (
    <Link to={`/products/${product.slug || product.id}`} style={{ textDecoration: 'none' }}>
      <div
        onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
        style={{
          background: 'rgba(10,10,12,0.55)',
          backdropFilter: 'blur(20px)',
          border: `1px solid ${hov ? 'rgba(251,192,45,0.25)' : 'rgba(255,255,255,0.06)'}`,
          borderRadius: 16,
          overflow: 'hidden',
          transform: hov ? 'translateY(-6px) scale(1.01)' : 'none',
          transition: 'all 0.3s ease',
          boxShadow: hov ? '0 20px 50px rgba(0,0,0,0.6), 0 0 30px rgba(251,192,45,0.08)' : '0 4px 20px rgba(0,0,0,0.3)',
        }}
      >
        <div style={{ aspectRatio: '1/1', background: 'rgba(255,255,255,0.02)', overflow: 'hidden', position: 'relative' }}>
          {img ? (
            <img src={img} alt={product.name} style={{
              width: '100%', height: '100%', objectFit: 'contain', padding: 16,
              transition: 'transform 0.4s', ...(hov ? { transform: 'scale(1.06)' } : {})
            }}/>
          ) : (
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ fontSize: 48, opacity: 0.15 }}>📷</div>
            </div>
          )}
          {product.is_featured && (
            <div style={{
              position: 'absolute', top: 10, right: 10,
              background: Y, color: '#000',
              fontSize: 9, fontWeight: 700, padding: '3px 8px',
              borderRadius: 6, fontFamily: 'Tahoma',
            }}>پرفروش</div>
          )}
        </div>
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontFamily: 'Tahoma', marginBottom: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {product.category?.name || 'قطعات دوربین'}
          </div>
          <div style={{
            fontSize: 13, color: 'rgba(255,255,255,0.85)', fontFamily: 'Tahoma',
            fontWeight: 600, marginBottom: 10, lineHeight: 1.4, direction: 'rtl',
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>{product.name}</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', direction: 'rtl' }}>
            {price ? (
              <span style={{ fontSize: 14, fontWeight: 700, color: Y, fontFamily: 'monospace' }}>
                {Number(price).toLocaleString('fa-IR')} ت
              </span>
            ) : (
              <span style={{ fontSize: 12, color: 'rgba(251,192,45,0.7)', fontFamily: 'Tahoma' }}>استعلام قیمت</span>
            )}
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: hov ? Y : 'rgba(251,192,45,0.1)',
              border: '1px solid rgba(251,192,45,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.3s',
            }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke={hov ? '#000' : Y} strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </Link>
  )
}

// ═══════════════════════════════════════════════════════════════════
// HOMEPAGE
// ═══════════════════════════════════════════════════════════════════
export default function HomePage() {
  const { data: productsData } = useQuery({
    queryKey: ['home-products'],
    queryFn: () => api.get('/catalog/products/?is_active=true&page_size=8').then(r => r.data),
  })
  const { data: packagesData } = useQuery({
    queryKey: ['home-packages'],
    queryFn: () => api.get('/catalog/packages/?page_size=3').then(r => r.data).catch(() => null),
  })
  const { data: articlesData } = useQuery({
    queryKey: ['home-articles'],
    queryFn: () => api.get('/blog/articles/?page_size=3').then(r => r.data).catch(() => null),
  })
  const { data: videosData } = useQuery({
    queryKey: ['home-videos'],
    queryFn: () => api.get('/blog/videos/?page_size=3').then(r => r.data).catch(() => null),
  })

  const products = productsData?.results || []
  const packages = packagesData?.results || []
  const articles = articlesData?.results || []
  const videos   = videosData?.results || []

  return (
    <div style={{ direction: 'rtl', fontFamily: 'Tahoma, Arial, sans-serif', color: 'rgba(255,255,255,0.87)' }}>

      {/* ══════════════════════════════════════════════
          HERO — ربات DOORBINKAR
      ══════════════════════════════════════════════ */}
      <HeroRobot/>

      {/* ══════════════════════════════════════════════
          آمار سریع
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{
          maxWidth: 1280, margin: '0 auto', padding: '40px 40px 80px',
        }}>
          <GlassCard style={{
            padding: '32px 48px',
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: 32, direction: 'rtl',
          }}>
            {[
              { n: 1000, s: '+', l: 'نوع قطعه' },
              { n: 30, s: ' سال', l: 'سابقه فعالیت' },
              { n: 5000, s: '+', l: 'مشتری راضی' },
              { n: 48, s: 'h', l: 'تحویل اکسپرس' },
            ].map((st, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: Y, fontFamily: 'monospace', marginBottom: 4 }}>
                  <Counter to={st.n} suffix={st.s}/>
                </div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>{st.l}</div>
              </div>
            ))}
          </GlassCard>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          چرا ما؟
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '60px 40px 100px' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <div style={{ fontSize: 11, color: 'rgba(251,192,45,0.7)', letterSpacing: '3px', marginBottom: 12 }}>WHY CHOOSE US</div>
            <h2 style={{ fontSize: 'clamp(24px,3vw,44px)', fontWeight: 800, color: '#fff', marginBottom: 14 }}>
              چرا باید با ما کار کنید؟
            </h2>
            <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.4)', maxWidth: 560, margin: '0 auto', lineHeight: 1.8 }}>
              ۳۰ سال تجربه در تأمین قطعات اصل — مستقیم از کارخانه‌های چین و تایوان
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 20 }}>
            {[
              { icon: '🏭', title: 'مستقیم از کارخانه', desc: 'بدون واسطه — قیمت واقعی کارخانه با ضمانت اصالت کالا' },
              { icon: '⚡', title: 'تحویل سریع', desc: 'تحویل اکسپرس ۴۸ ساعته از انبار تهران برای سفارش‌های آماده' },
              { icon: '🔬', title: 'کنترل کیفیت', desc: 'تمام محصولات قبل از ارسال کنترل فنی و تست می‌شوند' },
              { icon: '🤝', title: 'پشتیبانی تخصصی', desc: 'تیم فنی متخصص برای راهنمایی انتخاب و نصب قطعات' },
              { icon: '💎', title: 'قیمت رقابتی', desc: 'بهترین قیمت بازار با تضمین برگشت وجه در صورت عدم رضایت' },
              { icon: '🌐', title: 'سفارش از چین', desc: 'خرید سفارشی مستقیم از کارخانه‌های چین با تحویل ۲–۳ هفته' },
            ].map((f, i) => (
              <Section key={i} delay={i * 80}>
                <GlassCard style={{ padding: 28, height: '100%' }}>
                  <div style={{ fontSize: 32, marginBottom: 16 }}>{f.icon}</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#fff', marginBottom: 10 }}>{f.title}</div>
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', lineHeight: 1.7 }}>{f.desc}</div>
                </GlassCard>
              </Section>
            ))}
          </div>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          محصولات
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px 100px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 48, direction: 'rtl', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'rgba(251,192,45,0.7)', letterSpacing: '3px', marginBottom: 10 }}>FEATURED PRODUCTS</div>
              <h2 style={{ fontSize: 'clamp(22px,2.5vw,40px)', fontWeight: 800, color: '#fff' }}>پرفروش‌ترین قطعات</h2>
            </div>
            <Link to="/products" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              color: 'rgba(251,192,45,0.85)', textDecoration: 'none',
              fontSize: 13, border: '1px solid rgba(251,192,45,0.22)',
              borderRadius: 100, padding: '8px 20px',
            }}>
              مشاهده همه
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </Link>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 20 }}>
            {products.length > 0 ? products.map((p, i) => (
              <Section key={p.id} delay={i * 60}><ProductCard product={p}/></Section>
            )) : (
              [...Array(8)].map((_, i) => (
                <GlassCard key={i} hover={false} style={{ overflow: 'hidden' }}>
                  <div style={{ aspectRatio: '1/1', background: 'linear-gradient(135deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))' }}/>
                  <div style={{ padding: '14px 16px' }}>
                    <div style={{ height: 10, background: 'rgba(255,255,255,0.05)', borderRadius: 4, marginBottom: 8, width: '60%' }}/>
                    <div style={{ height: 14, background: 'rgba(255,255,255,0.05)', borderRadius: 4 }}/>
                  </div>
                </GlassCard>
              ))
            )}
          </div>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          پکیج‌ها
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{
          background: 'linear-gradient(180deg,transparent,rgba(251,192,45,0.04) 50%,transparent)',
          padding: '100px 0',
        }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px' }}>
            <div style={{ textAlign: 'center', marginBottom: 56 }}>
              <div style={{ fontSize: 11, color: 'rgba(251,192,45,0.7)', letterSpacing: '3px', marginBottom: 12 }}>PACKAGES</div>
              <h2 style={{ fontSize: 'clamp(22px,2.5vw,40px)', fontWeight: 800, color: '#fff', marginBottom: 12 }}>پکیج‌های آماده</h2>
              <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.35)', maxWidth: 480, margin: '0 auto', lineHeight: 1.8 }}>
                ست‌های کامل قطعات برای راه‌اندازی سیستم دوربین مداربسته
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 24 }}>
              {(packages.length > 0 ? packages : [
                { id: 1, name: 'پکیج دوربین ۲ مگاپیکسل', description: 'مناسب برای منازل و دفاتر کوچک', total_price: '2800000', _tag: '' },
                { id: 2, name: 'پکیج دوربین ۵ مگاپیکسل', description: 'ایده‌آل برای فروشگاه و انبار', total_price: '5500000', _tag: 'پیشنهاد ویژه' },
                { id: 3, name: 'پکیج دوربین ۸ مگاپیکسل', description: 'سیستم حرفه‌ای با کیفیت بالا', total_price: '9800000', _tag: '' },
              ]).map((pkg, i) => (
                <Section key={pkg.id || i} delay={i * 100}>
                  <GlassCard style={{ padding: 32, position: 'relative', overflow: 'hidden', height: '100%' }}>
                    {(pkg._tag || i === 1) && (
                      <div style={{
                        position: 'absolute', top: 16, left: 16,
                        background: `linear-gradient(135deg,${Y},${YD})`,
                        color: '#000', fontSize: 10, fontWeight: 700,
                        padding: '4px 12px', borderRadius: 100,
                      }}>{pkg._tag || 'پیشنهاد ویژه'}</div>
                    )}
                    <h3 style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginBottom: 10, marginTop: pkg._tag || i === 1 ? 32 : 0 }}>{pkg.name}</h3>
                    <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', lineHeight: 1.7, marginBottom: 20 }}>{pkg.description}</p>
                    {pkg.total_price && (
                      <div style={{ fontSize: 22, fontWeight: 700, color: Y, fontFamily: 'monospace', marginBottom: 20 }}>
                        {Number(pkg.total_price).toLocaleString('fa-IR')} تومان
                      </div>
                    )}
                    <Link to={`/packages/${pkg.id}`} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 8,
                      background: i === 1 ? `linear-gradient(135deg,${Y},${YD})` : 'rgba(251,192,45,0.1)',
                      color: i === 1 ? '#000' : Y, textDecoration: 'none',
                      border: i === 1 ? 'none' : 'rgba(251,192,45,0.22) 1px solid',
                      borderRadius: 10, padding: '12px 24px', fontSize: 13, fontWeight: 600,
                    }}>مشاهده پکیج ←</Link>
                  </GlassCard>
                </Section>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          عضویت همکار CTA
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px 100px' }}>
          <div style={{
            position: 'relative', borderRadius: 28, overflow: 'hidden',
            background: 'linear-gradient(135deg,rgba(251,192,45,0.12) 0%,rgba(10,10,12,0.6) 60%,rgba(10,10,12,0.6) 100%)',
            border: '1px solid rgba(251,192,45,0.15)',
            padding: '64px 56px',
          }}>
            <div style={{ position: 'absolute', top: -60, right: -60, width: 300, height: 300, borderRadius: '50%', background: 'rgba(251,192,45,0.1)', filter: 'blur(70px)', pointerEvents: 'none' }}/>
            <div style={{ position: 'absolute', bottom: -60, left: -60, width: 250, height: 250, borderRadius: '50%', background: 'rgba(251,192,45,0.06)', filter: 'blur(60px)', pointerEvents: 'none' }}/>

            <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: '1fr auto', gap: 40, alignItems: 'center', direction: 'rtl' }}>
              <div>
                <div style={{ fontSize: 11, color: 'rgba(251,192,45,0.8)', letterSpacing: '3px', marginBottom: 14 }}>PARTNER PROGRAM</div>
                <h2 style={{ fontSize: 'clamp(22px,2.8vw,42px)', fontWeight: 800, color: '#fff', marginBottom: 14, lineHeight: 1.2 }}>
                  همکار ما شوید<br/>
                  <span style={{ color: Y }}>قیمت ویژه همکاری</span> دریافت کنید
                </h2>
                <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', lineHeight: 1.8, maxWidth: 500, marginBottom: 28 }}>
                  با ثبت‌نام به عنوان همکار از قیمت‌های ویژه، اعتبار خرید، پشتیبانی اختصاصی و
                  دسترسی به کاتالوگ کامل محصولات بهره‌مند شوید.
                </p>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {['قیمت ویژه همکاری', 'پشتیبانی اختصاصی', 'اعتبار خرید', 'کاتالوگ کامل'].map(b => (
                    <span key={b} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      background: 'rgba(251,192,45,0.08)', border: '1px solid rgba(251,192,45,0.18)',
                      borderRadius: 100, padding: '5px 14px', fontSize: 12, color: Y,
                    }}>✓ {b}</span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 180 }}>
                <Link to="/partner" style={{
                  display: 'block', textAlign: 'center',
                  background: `linear-gradient(135deg,${Y},${YD})`,
                  color: '#000', textDecoration: 'none', borderRadius: 14,
                  padding: '16px 28px', fontSize: 15, fontWeight: 700,
                  boxShadow: '0 8px 32px rgba(251,192,45,0.35)', whiteSpace: 'nowrap',
                }}>ثبت‌نام همکار</Link>
                <Link to="/partner" style={{
                  display: 'block', textAlign: 'center',
                  background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)',
                  textDecoration: 'none', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 14, padding: '14px 28px', fontSize: 13, whiteSpace: 'nowrap',
                }}>اطلاعات بیشتر</Link>
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          مقالات
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px 100px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 48, direction: 'rtl', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'rgba(251,192,45,0.7)', letterSpacing: '3px', marginBottom: 10 }}>ARTICLES</div>
              <h2 style={{ fontSize: 'clamp(22px,2.5vw,40px)', fontWeight: 800, color: '#fff' }}>مقالات آموزشی</h2>
            </div>
            <Link to="/articles" style={{ color: Y, textDecoration: 'none', fontSize: 13, border: '1px solid rgba(251,192,45,0.22)', borderRadius: 100, padding: '8px 20px' }}>
              همه مقالات ←
            </Link>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 24 }}>
            {(articles.length > 0 ? articles : [
              { id: 1, title: 'راهنمای انتخاب لنز دوربین مداربسته', summary: 'نحوه انتخاب صحیح لنز بر اساس فاصله، زاویه دید و نور محیط', category: { name: 'آموزش' }, read_time: 8 },
              { id: 2, title: 'مقایسه سنسور CMOS و CCD در دوربین‌های مداربسته', summary: 'بررسی تفاوت‌های فنی و کاربردی دو نوع سنسور تصویری', category: { name: 'فنی' }, read_time: 12 },
              { id: 3, title: 'نصب و راه‌اندازی برد DVR خانگی', summary: 'آموزش گام‌به‌گام نصب و پیکربندی برد ضبط تصویر', category: { name: 'نصب' }, read_time: 15 },
            ]).map((a, i) => (
              <Section key={a.id || i} delay={i * 100}>
                <Link to={`/articles/${a.slug || a.id}`} style={{ textDecoration: 'none' }}>
                  <GlassCard style={{ padding: 28, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 14, direction: 'rtl' }}>
                      <span style={{ fontSize: 10, color: Y, background: 'rgba(251,192,45,0.08)', border: '1px solid rgba(251,192,45,0.18)', borderRadius: 100, padding: '3px 10px' }}>
                        {a.category?.name || 'مقاله'}
                      </span>
                      {a.read_time && (
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', padding: '3px 10px' }}>
                          {a.read_time} دقیقه مطالعه
                        </span>
                      )}
                    </div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: '#fff', marginBottom: 10, lineHeight: 1.5, direction: 'rtl', flex: 1 }}>{a.title}</h3>
                    <p style={{
                      fontSize: 13, color: 'rgba(255,255,255,0.35)', lineHeight: 1.7,
                      direction: 'rtl', marginBottom: 16,
                      display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                    }}>{a.summary}</p>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', color: Y, fontSize: 12 }}>
                      ادامه مطلب ←
                    </div>
                  </GlassCard>
                </Link>
              </Section>
            ))}
          </div>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          ویدیوها
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{
          background: 'linear-gradient(180deg,transparent,rgba(251,192,45,0.03) 50%,transparent)',
          padding: '100px 0',
        }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 48, direction: 'rtl', flexWrap: 'wrap', gap: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: 'rgba(251,192,45,0.7)', letterSpacing: '3px', marginBottom: 10 }}>VIDEO TUTORIALS</div>
                <h2 style={{ fontSize: 'clamp(22px,2.5vw,40px)', fontWeight: 800, color: '#fff' }}>ویدیوهای آموزشی</h2>
              </div>
              <Link to="/videos" style={{ color: Y, textDecoration: 'none', fontSize: 13, border: '1px solid rgba(251,192,45,0.22)', borderRadius: 100, padding: '8px 20px' }}>
                همه ویدیوها ←
              </Link>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 24 }}>
              {(videos.length > 0 ? videos : [
                { id: 1, title: 'آموزش تنظیم دوربین مداربسته IP', duration: '12:30' },
                { id: 2, title: 'نحوه تعویض لنز دوربین بولت', duration: '8:45' },
                { id: 3, title: 'راه‌اندازی سیستم NVR کامل', duration: '22:10' },
              ]).map((v, i) => (
                <Section key={v.id || i} delay={i * 100}>
                  <Link to={`/videos/${v.slug || v.id}`} style={{ textDecoration: 'none' }}>
                    <GlassCard style={{ overflow: 'hidden' }}>
                      <div style={{
                        aspectRatio: '16/9',
                        background: 'linear-gradient(135deg,rgba(251,192,45,0.08),rgba(10,10,12,0.6))',
                        position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {v.thumbnail ? (
                          <img src={v.thumbnail} alt={v.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }}/>
                        ) : (
                          <div style={{ fontSize: 40, opacity: 0.3 }}>🎬</div>
                        )}
                        <div style={{
                          position: 'absolute', width: 52, height: 52,
                          borderRadius: '50%', background: `rgba(251,192,45,0.95)`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          boxShadow: '0 0 25px rgba(251,192,45,0.5)',
                        }}>
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="#000">
                            <path d="M5 3l14 9-14 9V3z"/>
                          </svg>
                        </div>
                        {v.duration && (
                          <div style={{
                            position: 'absolute', bottom: 10, left: 10,
                            background: 'rgba(0,0,0,0.75)', color: '#fff', fontSize: 11,
                            padding: '2px 8px', borderRadius: 4, fontFamily: 'monospace',
                          }}>{v.duration}</div>
                        )}
                      </div>
                      <div style={{ padding: '16px 18px', direction: 'rtl' }}>
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.85)', lineHeight: 1.5 }}>{v.title}</h3>
                      </div>
                    </GlassCard>
                  </Link>
                </Section>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* ══════════════════════════════════════════════
          سفارش از چین — مراحل
      ══════════════════════════════════════════════ */}
      <Section>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px 100px' }}>
          <GlassCard style={{
            padding: '64px 56px',
            background: 'linear-gradient(135deg,rgba(251,192,45,0.08),rgba(10,10,12,0.6))',
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))',
            gap: 60, alignItems: 'center',
          }}>
            <div style={{ direction: 'rtl' }}>
              <div style={{ fontSize: 11, color: Y, letterSpacing: '3px', marginBottom: 14 }}>CHINA ORDER</div>
              <h2 style={{ fontSize: 'clamp(22px,2.5vw,38px)', fontWeight: 800, color: '#fff', marginBottom: 14, lineHeight: 1.2 }}>
                قطعه‌ای که نمی‌یابید؟<br/>
                <span style={{ color: Y }}>از چین سفارش دهید</span>
              </h2>
              <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', lineHeight: 1.8, marginBottom: 28 }}>
                سفارش مستقیم از کارخانه‌های چین — تحویل ۲ تا ۳ هفته.
                ما واردات، گمرک و حمل‌ونقل را مدیریت می‌کنیم.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
                {['سفارش از هر کارخانه چینی', 'مدیریت کامل واردات و گمرک', 'ضمانت تحویل و کیفیت', 'قیمت رقابتی تضمینی'].map(f => (
                  <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'rgba(255,255,255,0.6)' }}>
                    <div style={{ width: 18, height: 18, borderRadius: '50%', background: 'rgba(251,192,45,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: Y, flexShrink: 0 }}>✓</div>
                    {f}
                  </div>
                ))}
              </div>
              <Link to="/china-order" style={{
                display: 'inline-flex', alignItems: 'center', gap: 10,
                background: `linear-gradient(135deg,${Y},${YD})`,
                color: '#000', textDecoration: 'none', borderRadius: 14,
                padding: '16px 32px', fontSize: 15, fontWeight: 700,
                boxShadow: '0 8px 32px rgba(251,192,45,0.35)',
              }}>ثبت سفارش از چین ←</Link>
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
                    background: 'linear-gradient(135deg,rgba(251,192,45,0.25),rgba(251,192,45,0.05))',
                    border: '1px solid rgba(251,192,45,0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13, fontWeight: 700, color: Y,
                  }}>{s.step}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.85)', marginBottom: 4 }}>{s.title}</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>{s.desc}</div>
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
        <div style={{ textAlign: 'center', padding: '60px 40px 120px' }}>
          <h2 style={{ fontSize: 'clamp(24px,3vw,48px)', fontWeight: 900, color: '#fff', marginBottom: 14 }}>
            آماده شروع هستید؟
          </h2>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.35)', marginBottom: 36 }}>
            همین حالا محصولات را مشاهده کنید یا با ما تماس بگیرید
          </p>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/products" style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              background: `linear-gradient(135deg,${Y},${YD})`,
              color: '#000', textDecoration: 'none', borderRadius: 14,
              padding: '18px 40px', fontSize: 16, fontWeight: 700,
              boxShadow: '0 8px 40px rgba(251,192,45,0.4)',
            }}>مشاهده محصولات</Link>
            <Link to="/contact" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.7)',
              textDecoration: 'none', border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 14, padding: '18px 36px', fontSize: 15,
            }}>تماس با ما</Link>
          </div>
        </div>
      </Section>
    </div>
  )
}
