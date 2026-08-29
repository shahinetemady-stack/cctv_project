import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

export default function ContactPage() {
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then((r) => r.data),
    staleTime: 600000,
  })

  const item =
    'flex items-start gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-brand-softer)] p-4'
  const icon =
    'w-10 h-10 rounded-xl flex items-center justify-center text-lg border border-[rgba(251,192,45,0.15)] flex-shrink-0'

  return (
    <div className="container-main py-12 max-w-3xl">
      <h1 className="font-display font-bold text-3xl text-white mb-8">📞 تماس با ما</h1>

      <div className="grid gap-4">
        {settings?.contact_phone && (
          <div className={item}>
            <span className={icon}>📞</span>
            <div>
              <div className="text-sm font-bold text-white mb-1">تلفن فروشگاه</div>
              <a href={`tel:${settings.contact_phone}`} dir="ltr" className="text-sm text-gray-300 hover:text-gold transition-colors">
                {settings.contact_phone}
              </a>
            </div>
          </div>
        )}
        {settings?.contact_email && (
          <div className={item}>
            <span className={icon}>📧</span>
            <div>
              <div className="text-sm font-bold text-white mb-1">ایمیل</div>
              <a href={`mailto:${settings.contact_email}`} dir="ltr" className="text-sm text-gray-300 hover:text-gold transition-colors">
                {settings.contact_email}
              </a>
            </div>
          </div>
        )}
        {settings?.working_hours && (
          <div className={item}>
            <span className={icon}>🕐</span>
            <div>
              <div className="text-sm font-bold text-white mb-1">ساعات کاری</div>
              <span className="text-sm text-gray-300">{settings.working_hours}</span>
            </div>
          </div>
        )}
        {settings?.contact_address && (
          <div className={item}>
            <span className={icon}>📍</span>
            <div>
              <div className="text-sm font-bold text-white mb-1">آدرس</div>
              <span className="text-sm text-gray-300 leading-relaxed">{settings.contact_address}</span>
            </div>
          </div>
        )}

        {(settings?.china_phone || settings?.china_address || settings?.wechat_qr) && (
          <div className="mt-6">
            <h2 className="font-display font-bold text-xl text-white mb-4">🇨🇳 دفتر چین</h2>
            <div className="grid gap-4">
              {settings?.china_phone && (
                <div className={item}>
                  <span className={icon}>📞</span>
                  <div>
                    <div className="text-sm font-bold text-white mb-1">تلفن چین</div>
                    <a href={`tel:+${settings.china_phone.replace(/[^0-9]/g, '')}`} dir="ltr" className="text-sm text-gray-300 hover:text-gold transition-colors">
                      +{settings.china_phone.replace(/^00/, '')}
                    </a>
                  </div>
                </div>
              )}
              {settings?.china_address && (
                <div className={item}>
                  <span className={icon}>📍</span>
                  <div>
                    <div className="text-sm font-bold text-white mb-1">آدرس دفتر چین</div>
                    <span dir="ltr" className="block text-sm text-gray-300 leading-relaxed text-left">
                      {settings.china_address}
                    </span>
                  </div>
                </div>
              )}
              {settings?.wechat_qr && (
                <div className={item}>
                  <img src={settings.wechat_qr} alt="WeChat QR" loading="lazy"
                    className="w-32 h-32 rounded-2xl border border-[var(--color-border)] bg-white p-1.5" />
                  <div>
                    <div className="text-sm font-bold text-white mb-1">ویچت (WeChat)</div>
                    <span className="text-sm text-gray-300 leading-relaxed">
                      برای ارتباط مستقیم با دفتر چین در ویچت، کیوآرکد را اسکن کنید.
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
