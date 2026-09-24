import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { PageLoader } from '../components/ui'

// تبدیل ریال به تومان با ارقام فارسی
const formatToman = (rial) =>
  new Intl.NumberFormat('fa-IR').format(Math.round(Number(rial || 0) / 10)) + ' تومان'

const faNum = (n) => new Intl.NumberFormat('fa-IR').format(n || 0)

const DEFAULT_BENEFITS = 'مزایای این سطح به‌زودی اعلام می‌شود.'

export default function ClubPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['club-info'],
    queryFn: () => api.get('/users/club-info/').then(r => r.data),
    staleTime: 600000,
    retry: 1,
  })

  if (isLoading) return <PageLoader />

  if (isError) {
    return (
      <div className="container-main py-20 text-center max-w-sm">
        <div className="text-5xl mb-4">⚠️</div>
        <h2 className="font-display font-bold text-xl text-white mb-3">خطا در دریافت اطلاعات</h2>
        <p className="text-gray-steel text-sm mb-6">اطلاعات باشگاه در دسترس نیست — دوباره تلاش کنید.</p>
        <button onClick={() => refetch()} className="btn-primary">تلاش مجدد</button>
      </div>
    )
  }

  const tiers = data?.tiers || []
  const period = data?.period_months || 3

  // متن آستانه هر سطح
  const thresholdText = (key) => {
    if (key === 'silver') return 'شروع همکاری'
    if (key === 'gold') return `از ${formatToman(data?.silver_to_gold_amount)} خرید در ${faNum(period)} ماه`
    if (key === 'platinum') return `از ${formatToman(data?.gold_to_platinum_amount)} خرید در ${faNum(period)} ماه`
    return ''
  }

  const targetKeys = ['gold', 'platinum']

  const rules = [
    `ارتقا به‌صورت خودکار انجام می‌شود؛ وقتی مجموع خرید آنلاین پرداخت‌شده در بازه ${faNum(period)} ماه (به‌همراه سابقه خرید ثبت‌شده شما) به آستانه سطح بالاتر برسد.`,
    'سطح همکاری با مجموع خرید ۳ ماهه به‌صورت خودکار ارتقا یا تنزل می‌یابد — سطح دائمی نیست.',
    'سفارش‌های مرجوعی، لغوشده و خریدهای اعتباری معوق در محاسبه مجموع خرید لحاظ نمی‌شوند.',
    'ارزیابی سطوح به‌صورت روزانه انجام می‌شود و پس از ارتقا با پیامک به شما اطلاع‌رسانی می‌گردد.',
  ]

  return (
    <div className="container-main py-12 max-w-4xl">
      {/* هیرو */}
      <div className="text-center mb-12">
        <div className="text-5xl mb-4">🤝</div>
        <h1 className="font-display font-bold text-3xl text-white mb-4">باشگاه همکاران دوربین‌کار</h1>
        <p className="text-gray-steel text-sm leading-7 max-w-xl mx-auto">
          همکاری با نصاب‌ها و فروشندگان تجهیزات نظارت تصویری — با خرید بیشتر، سطح بالاتر و مزایای ویژه‌تر.
        </p>
        <Link to="/auth/register" className="btn-primary inline-block mt-6">ثبت‌نام همکار</Link>
      </div>

      {/* کارت‌های سطح */}
      <div className="grid md:grid-cols-3 gap-4 mb-12">
        {tiers.map(t => {
          const isTarget = targetKeys.includes(t.key)
          return (
            <div key={t.key}
              className={`card p-5 flex flex-col ${isTarget ? 'border-gold/40 border-r-4' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-display font-bold text-white text-sm">{t.title}</h3>
                {isTarget && <span className="text-gold text-xs">🎯</span>}
              </div>
              <div className="text-[11px] text-gold mb-3">{thresholdText(t.key)}</div>
              <p className="text-xs text-gray-300 leading-6 whitespace-pre-line flex-1">
                {t.benefits?.trim() ? t.benefits : DEFAULT_BENEFITS}
              </p>
            </div>
          )
        })}
      </div>

      {/* قوانین باشگاه */}
      <div className="card p-6">
        <h2 className="font-display font-bold text-lg text-white mb-4">📜 قوانین باشگاه</h2>
        <ul className="space-y-3">
          {rules.map((r, i) => (
            <li key={i} className="text-xs text-gray-300 leading-6 flex gap-2">
              <span className="text-gold shrink-0">•</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
