import HeroSection from '../../components/home/HeroSection'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function HomePage() {
  const { data: featured = [] } = useQuery({
    queryKey: ['featured-products'],
    queryFn: () => api.get('/catalog/products/?featured=true&limit=6').then(r => r.data.results || r.data),
    staleTime: 60000,
  })
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 60000,
  })

  return (
    <div style={{ background: '#030303', minHeight: '100vh' }}>

      {/* ── Hero Section با اسکرول انفجاری ── */}
      <HeroSection />

      {/* ── محصولات برگزیده ── */}
      <section style={{
        background: '#050505',
        padding: '80px 60px',
        borderTop: '0.5px solid rgba(255,255,255,0.04)',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            marginBottom: 40,
            direction: 'rtl',
          }}>
            <div>
              <p style={{ fontSize: 11, color: '#ffa500', letterSpacing: '2px', marginBottom: 6, fontFamily: 'monospace' }}>
                FEATURED PRODUCTS
              </p>
              <h2 style={{ fontSize: 28, fontWeight: 700, color: '#fff', fontFamily: 'Tahoma' }}>
                پرفروش‌ترین قطعات
              </h2>
            </div>
            <div style={{ flex: 1, height: '0.5px', background: 'rgba(255,255,255,0.06)' }} />
            <Link to="/products" style={{
              color: '#ffa500',
              textDecoration: 'none',
              fontSize: 13,
              fontFamily: 'Tahoma',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              مشاهده همه
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#ffa500" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </Link>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 16,
          }}>
            {featured.map(product => (
              <Link key={product.id} to={`/products/${product.slug}`} style={{ textDecoration: 'none' }}>
                <div style={{
                  background: '#0a0a0a',
                  border: '0.5px solid rgba(255,255,255,0.06)',
                  borderRadius: 12,
                  overflow: 'hidden',
                  transition: 'border-color 0.2s, transform 0.2s',
                }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'rgba(255,165,0,0.25)'
                    e.currentTarget.style.transform = 'translateY(-2px)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'
                    e.currentTarget.style.transform = 'translateY(0)'
                  }}
                >
                  {/* تصویر */}
                  <div style={{
                    height: 140,
                    background: '#111',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    position: 'relative',
                  }}>
                    {product.image ? (
                      <img src={product.image} alt={product.name}
                        style={{ width: '100%', height: '100%', objectFit: 'contain', padding: 16 }} />
                    ) : (
                      <div style={{
                        width: 60, height: 40,
                        background: '#1a1a1a',
                        borderRadius: 6,
                        border: '0.5px solid rgba(255,255,255,0.08)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <div style={{
                          width: 20, height: 20,
                          borderRadius: '50%',
                          border: '1px solid rgba(255,255,255,0.15)',
                        }} />
                      </div>
                    )}
                    {product.is_new && (
                      <div style={{
                        position: 'absolute', top: 8, right: 8,
                        background: 'rgba(255,165,0,0.15)',
                        border: '0.5px solid rgba(255,165,0,0.3)',
                        borderRadius: 4,
                        padding: '2px 8px',
                        fontSize: 9,
                        color: '#ffa500',
                        fontFamily: 'monospace',
                      }}>NEW</div>
                    )}
                  </div>
                  {/* اطلاعات */}
                  <div style={{ padding: '14px 14px', direction: 'rtl' }}>
                    <div style={{
                      fontSize: 12,
                      color: 'rgba(255,255,255,0.6)',
                      fontFamily: 'Tahoma',
                      marginBottom: 6,
                      lineHeight: 1.4,
                    }}>{product.name}</div>
                    {product.category_name && (
                      <div style={{
                        fontSize: 10,
                        color: 'rgba(255,255,255,0.2)',
                        fontFamily: 'Tahoma',
                        marginBottom: 10,
                      }}>{product.category_name}</div>
                    )}
                    <div style={{
                      fontSize: 13,
                      color: '#ffa500',
                      fontFamily: 'Tahoma',
                      fontWeight: 600,
                      direction: 'ltr',
                      textAlign: 'right',
                    }}>
                      {product.min_price ? `${fmt(product.min_price)} ت` : 'استعلام قیمت'}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── دسته‌بندی‌ها ── */}
      <section style={{
        background: '#030303',
        padding: '80px 60px',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 50, direction: 'rtl' }}>
            <p style={{ fontSize: 11, color: '#ffa500', letterSpacing: '2px', fontFamily: 'monospace', marginBottom: 10 }}>
              CATEGORIES
            </p>
            <h2 style={{ fontSize: 28, fontWeight: 700, color: '#fff', fontFamily: 'Tahoma' }}>
              قطعات بر اساس نوع
            </h2>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 16,
          }}>
            {[
              { icon: '🔬', title: 'سنسور تصویر', desc: 'Sony، Samsung، OmniVision', color: '#6495ED', href: '/products?cat=sensor' },
              { icon: '🔭', title: 'لنز', desc: 'ثابت، موتورایز، فیش‌آی', color: '#C0C0C0', href: '/products?cat=lens' },
              { icon: '💡', title: 'LED مادون قرمز', desc: 'فاصله ۲۰ تا ۱۰۰ متر', color: '#FF6B35', href: '/products?cat=ir' },
              { icon: '🖥️', title: 'پردازنده تصویر', desc: 'HiSilicon، Ambarella', color: '#00C896', href: '/products?cat=isp' },
              { icon: '⚡', title: 'برد اصلی', desc: 'PCB، مدارهای کامل', color: '#4CAF50', href: '/products?cat=board' },
              { icon: '🔧', title: 'متفرقه', desc: 'کابل، منبع تغذیه، جعبه', color: '#9E9E9E', href: '/products?cat=other' },
            ].map((cat, i) => (
              <Link key={i} to={cat.href} style={{ textDecoration: 'none' }}>
                <div style={{
                  background: '#0a0a0a',
                  border: `0.5px solid ${cat.color}15`,
                  borderRadius: 12,
                  padding: '24px',
                  direction: 'rtl',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  transition: 'border-color 0.2s, background 0.2s',
                }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = cat.color + '35'
                    e.currentTarget.style.background = cat.color + '06'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = cat.color + '15'
                    e.currentTarget.style.background = '#0a0a0a'
                  }}
                >
                  <div style={{
                    width: 48, height: 48,
                    borderRadius: 10,
                    background: cat.color + '10',
                    border: `0.5px solid ${cat.color}25`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 22,
                    flexShrink: 0,
                  }}>{cat.icon}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', fontFamily: 'Tahoma', marginBottom: 4 }}>
                      {cat.title}
                    </div>
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'Tahoma' }}>
                      {cat.desc}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA بنر ── */}
      <section style={{
        background: '#070707',
        padding: '60px',
        borderTop: '0.5px solid rgba(255,255,255,0.04)',
        borderBottom: '0.5px solid rgba(255,255,255,0.04)',
      }}>
        <div style={{
          maxWidth: 1200, margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          direction: 'rtl',
        }}>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: '#fff', fontFamily: 'Tahoma', marginBottom: 10 }}>
              قطعه‌ای که نمی‌یابید؟
            </h2>
            <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.35)', fontFamily: 'Tahoma' }}>
              سفارش مستقیم از چین — تحویل ۲ تا ۳ هفته
            </p>
          </div>
          <Link to="/china-order" style={{
            background: '#ffa500',
            color: '#000',
            textDecoration: 'none',
            borderRadius: 10,
            padding: '14px 32px',
            fontSize: 14,
            fontWeight: 700,
            fontFamily: 'Tahoma',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexShrink: 0,
          }}>
            سفارش از چین
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M12 5l7 7-7 7" stroke="#000" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </Link>
        </div>
      </section>

      {/* ── واتساپ/تلگرام ── */}
      {settings?.whatsapp_number && (
        <a href={`https://wa.me/${settings.whatsapp_number}`}
          target="_blank" rel="noopener noreferrer"
          style={{
            position: 'fixed',
            bottom: 24, left: 24,
            width: 52, height: 52,
            borderRadius: '50%',
            background: '#25D366',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            boxShadow: '0 4px 20px rgba(37,211,102,0.3)',
            textDecoration: 'none',
          }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="white">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
          </svg>
        </a>
      )}
    </div>
  )
}
