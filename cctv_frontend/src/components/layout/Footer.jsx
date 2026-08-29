import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import api from '../../services/api'

const QUICK_LINKS = [
  ['محصولات', '/products'],
  ['مقالات', '/blog'],
  ['ویدیوها', '/videos'],
  ['سفارش از چین', '/china-order'],
  ['دانلودها', '/downloads'],
  ['پکیج‌ها', '/packages'],
  ['قوانین', '/terms'],
  ['حریم خصوصی', '/privacy'],
  ['درباره ما', '/about'],
  ['ورود', '/auth/login'],
  ['ثبت‌نام همکار', '/auth/register'],
]

function FooterHeading({ children }) {
  return (
    <h4 className="flex items-center gap-2 text-sm font-bold text-[var(--color-text-primary)] mb-4">
      <span className="w-1 h-4 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
      {children}
    </h4>
  )
}

function FooterLink({ to, children }) {
  return (
    <Link
      to={to}
      className="group flex items-center gap-2 py-1.5 text-[13px] text-[var(--color-text-secondary)] hover:text-gold transition-colors"
    >
      <span className="w-1 h-1 rounded-full bg-[var(--color-text-muted)] group-hover:bg-gold group-hover:shadow-[0_0_6px_rgba(251,192,45,0.8)] transition-all" />
      {children}
    </Link>
  )
}

// ─── نماد اعتماد الکترونیکی (اینماد) ─────────────────────────
function EnamadSeal({ id, code }) {
  if (!id || !code) return null
  return (
    <a
      referrerPolicy="origin"
      target="_blank"
      rel="noopener noreferrer"
      href={`https://trustseal.enamad.ir/?id=${id}&code=${code}`}
      title="نماد اعتماد الکترونیکی"
      aria-label="نماد اعتماد الکترونیکی"
      className="inline-flex items-center justify-center w-24 h-24 rounded-2xl border border-[var(--color-border)] bg-white/5 hover:border-gold/40 transition-colors overflow-hidden"
    >
      <img
        referrerPolicy="origin"
        src={`https://trustseal.enamad.ir/logo.aspx?id=${id}&Code=${code}`}
        alt="نماد اعتماد الکترونیکی"
        code={code}
        loading="lazy"
        className="w-20 h-20 object-contain cursor-pointer"
      />
    </a>
  )
}

// ─── فوتر سایت — تم Dark Gold ──────────────────────────────────
export default function Footer() {
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then((r) => r.data),
    staleTime: 0,
  })

  const [email, setEmail] = useState('')
  const [subscribed, setSubscribed] = useState(false)

  const handleSubscribe = (e) => {
    e.preventDefault()
    if (!email) return
    // TODO: ارسال به API
    setSubscribed(true)
    setTimeout(() => {
      setSubscribed(false)
      setEmail('')
    }, 2500)
  }

  const socials = [
    settings?.whatsapp_number && {
      label: 'واتساپ',
      href: `https://wa.me/${settings.whatsapp_number.replace(/[^0-9]/g, '')}`,
      color: '#25D366',
      icon: (
        <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
        </svg>
      ),
    },
    settings?.bale_username && {
      label: 'بله',
      href: `https://ble.ir/${settings.bale_username}`,
      color: '#0088cc',
      icon: <span className="text-xs font-bold">بله</span>,
    },
    settings?.eitaa_username && {
      label: 'ایتا',
      href: `https://eitaa.com/${settings.eitaa_username}`,
      color: '#8B5CF6',
      icon: <span className="text-xs font-bold">ایتا</span>,
    },
    settings?.telegram_username && {
      label: 'تلگرام',
      href: `https://t.me/${settings.telegram_username}`,
      color: '#0088cc',
      icon: (
        <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
          <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
        </svg>
      ),
    },
    settings?.instagram_username && {
      label: 'اینستاگرام',
      href: `https://instagram.com/${settings.instagram_username}`,
      color: '#E1306C',
      icon: (
        <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
        </svg>
      ),
    },
  ].filter(Boolean)

  return (
    <footer className="relative z-[1] mt-24 md:mt-32 overflow-hidden">
      {/* خط طلایی بالای فوتر */}
      <div
        aria-hidden="true"
        className="h-px w-full"
        style={{
          background:
            'linear-gradient(to left, transparent 0%, rgba(251,192,45,0.5) 50%, transparent 100%)',
        }}
      />

      {/* هاله‌های طلایی پس‌زمینه */}
      <div aria-hidden="true" className="absolute inset-0 pointer-events-none">
        <div
          className="absolute -top-24 right-[15%] w-72 h-72 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(251,192,45,0.07), transparent 65%)' }}
        />
        <div
          className="absolute bottom-0 left-[8%] w-80 h-80 rounded-full blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(251,192,45,0.05), transparent 65%)' }}
        />
      </div>

      <div className="container-site relative">
        {/* ─── کارت خبرنامه ─── */}
        <div className="glass-gold rounded-3xl p-6 md:p-10 mt-10 md:mt-14">
          <div className="flex flex-col md:flex-row md:items-center gap-6 md:gap-10">
            <div className="flex-1">
              <h3 className="text-lg md:text-2xl font-extrabold tracking-tight">
                <span className="ml-2">✨</span>
                <span className="gold-text">از جدیدترین قطعات و تخفیف‌ها جا نمون</span>
              </h3>
              <p className="section-sub">
                عضو خبرنامه ما بشو و اولین نفری باش که از تخفیف‌های ویژه و محصولات جدید مطلع می‌شه
              </p>
            </div>
            <form onSubmit={handleSubscribe} className="flex gap-2 w-full md:w-auto">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ایمیلت رو وارد کن..."
                required
                className="input-dark flex-1 md:w-72 text-sm"
              />
              <button
                type="submit"
                disabled={subscribed}
                className={
                  subscribed
                    ? 'badge badge-success !px-5 !py-2.5 !text-sm font-bold'
                    : 'btn-gold text-sm whitespace-nowrap'
                }
              >
                {subscribed ? (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  'عضویت'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* ─── گرید اصلی ─── */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-8 py-12 md:py-16">
          {/* ستون برند */}
          <div>
            <div className="flex items-center gap-2.5 mb-5">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'var(--gradient-gold)', boxShadow: 'var(--shadow-gold)' }}
              >
                <svg className="w-5 h-5" style={{ color: 'var(--color-brand-contrast)' }} fill="currentColor" viewBox="0 0 24 24">
                  <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.889L15 14v-4zM3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                </svg>
              </div>
              <span className="font-display font-bold text-[var(--color-text-primary)] text-lg tracking-tight">
                {settings?.site_name || 'فروشگاه قطعات دوربین'}
              </span>
            </div>
            <p className="text-[13px] leading-relaxed text-[var(--color-text-secondary)]">
              تأمین‌کننده تخصصی قطعات دوربین مداربسته — سنسور، لنز، برد، ISP و بیشتر
              با بیش از یک دهه تجربه در بازار ایران
            </p>
            {socials.length > 0 && (
              <div className="flex flex-wrap gap-2.5 mt-6">
                {socials.map((s) => (
                  <a
                    key={s.label}
                    href={s.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={s.label}
                    aria-label={s.label}
                    className="w-10 h-10 rounded-xl flex items-center justify-center border transition-all hover:-translate-y-0.5"
                    style={{
                      color: s.color,
                      background: s.color + '12',
                      borderColor: s.color + '30',
                    }}
                  >
                    {s.icon}
                  </a>
                ))}
              </div>
            )}
            <div className="mt-6">
              <EnamadSeal id={settings?.enamad_id} code={settings?.enamad_code} />
            </div>
          </div>

          {/* دسترسی سریع */}
          <div className="hidden md:block">
            <FooterHeading>دسترسی سریع</FooterHeading>
            <ul>
              {QUICK_LINKS.slice(0, 6).map(([label, href]) => (
                <li key={href}>
                  <FooterLink to={href}>{label}</FooterLink>
                </li>
              ))}
            </ul>
          </div>

          {/* لینک‌های مفید */}
          <div className="hidden md:block">
            <FooterHeading>لینک‌های مفید</FooterHeading>
            <ul>
              {QUICK_LINKS.slice(6).map(([label, href]) => (
                <li key={href}>
                  <FooterLink to={href}>{label}</FooterLink>
                </li>
              ))}
            </ul>
          </div>

          {/* تماس با ما */}
          <div>
            <FooterHeading>تماس با ما</FooterHeading>
            <ul className="space-y-3">
              {settings?.contact_phone && (
                <li className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)]">📞</span>
                  <a href={`tel:${settings.contact_phone}`} dir="ltr" className="text-[13px] text-[var(--color-text-secondary)] hover:text-gold transition-colors">
                    {settings.contact_phone}
                  </a>
                </li>
              )}
              {settings?.contact_email && (
                <li className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)]">📧</span>
                  <a href={`mailto:${settings.contact_email}`} dir="ltr" className="text-[13px] text-[var(--color-text-secondary)] hover:text-gold transition-colors">
                    {settings.contact_email}
                  </a>
                </li>
              )}
              {settings?.working_hours && (
                <li className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)]">🕐</span>
                  <span className="text-[13px] text-[var(--color-text-secondary)]">{settings.working_hours}</span>
                </li>
              )}
              {settings?.contact_address && (
                <li className="flex items-start gap-2.5">
                  <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)] flex-shrink-0">📍</span>
                  <span className="text-[13px] text-[var(--color-text-secondary)] leading-relaxed">{settings.contact_address}</span>
                </li>
              )}
              {(settings?.china_phone || settings?.china_address || settings?.wechat_qr) && (
                <li className="pt-4 mt-1 border-t border-[var(--color-border)]">
                  <span className="block text-[13px] font-bold text-[var(--color-text-primary)] mb-3">🇨🇳 دفتر چین</span>
                  <ul className="space-y-3">
                    {settings?.china_phone && (
                      <li className="flex items-center gap-2.5">
                        <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)]">📞</span>
                        <a href={`tel:+${settings.china_phone.replace(/[^0-9]/g, '')}`} dir="ltr" className="text-[13px] text-[var(--color-text-secondary)] hover:text-gold transition-colors">
                          +{settings.china_phone.replace(/^00/, '')}
                        </a>
                      </li>
                    )}
                    {settings?.china_address && (
                      <li className="flex items-start gap-2.5">
                        <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)] flex-shrink-0">📍</span>
                        <span dir="ltr" className="text-[13px] text-[var(--color-text-secondary)] leading-relaxed text-left">{settings.china_address}</span>
                      </li>
                    )}
                    {settings?.wechat_qr && (
                      <li className="flex items-center gap-3">
                        <img src={settings.wechat_qr} alt="WeChat QR" loading="lazy"
                          className="w-20 h-20 rounded-xl border border-[var(--color-border)] bg-white p-1" />
                        <span className="text-[11px] text-[var(--color-text-muted)] leading-relaxed">برای ارتباط در ویچت،<br />کیوآرکد را اسکن کنید</span>
                      </li>
                    )}
                  </ul>
                </li>
              )}
              {!settings && (
                <>
                  <li className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)]">📞</span>
                    <span className="text-[13px] text-[var(--color-text-secondary)]" dir="ltr">021-XXXXXXXX</span>
                  </li>
                  <li className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-[var(--color-brand-softer)] border border-[rgba(251,192,45,0.15)]">🕐</span>
                    <span className="text-[13px] text-[var(--color-text-secondary)]">شنبه تا پنج‌شنبه، ۹–۱۸</span>
                  </li>
                </>
              )}
            </ul>
          </div>
        </div>

        {/* ─── نوار پایانی ─── */}
        <div className="border-t border-[var(--color-border)] py-5 mb-2 flex flex-col md:flex-row items-center justify-between gap-3">
          <span className="text-xs text-[var(--color-text-muted)]">
            © ۱۴۰۳ {settings?.site_name || 'فروشگاه قطعات دوربین مداربسته'} — تمامی حقوق محفوظ است
          </span>
          <div className="flex items-center gap-2">
            <span className="badge badge-gold !text-[10px]">ساخته شده با ❤️ در ایران</span>
            <span className="text-[10px] font-mono text-[var(--color-text-muted)]">CCTV PARTS v1.0</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
