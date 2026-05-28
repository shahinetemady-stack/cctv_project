import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'

export default function PartSelectionGuidePage() {
  const { data } = useQuery({
    queryKey: ['part-selection-guide'],
    queryFn: () => api.get('/education/guides/part-selection/').then(r => r.data),
  })

  return (
    <div className="container-main py-12 max-w-4xl">
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-3xl text-white mb-3">🎯 راهنمای انتخاب قطعه</h1>
        <p className="text-gray-steel">چطور قطعه مناسب دوربین مداربسته را انتخاب کنیم؟</p>
      </div>

      {/* اینفوگرافیک */}
      <div className="grid grid-cols-4 gap-4 mb-10">
        {[
          { icon: '📐', title: 'محل نصب', desc: 'داخلی یا خارجی؟ فاصله دید؟' },
          { icon: '💡', title: 'نور محیط', desc: 'روز/شب؟ نور مصنوعی؟' },
          { icon: '📺', title: 'کیفیت تصویر', desc: '2MP, 4MP یا 8MP؟' },
          { icon: '🔌', title: 'زیرساخت', desc: 'کابل موجود؟ برق؟' },
        ].map(item => (
          <div key={item.title} className="card p-4 text-center">
            <div className="text-3xl mb-2">{item.icon}</div>
            <div className="text-sm font-semibold text-white mb-1">{item.title}</div>
            <div className="text-xs text-gray-steel">{item.desc}</div>
          </div>
        ))}
      </div>

      {/* محتوای راهنما */}
      {data?.guide?.content ? (
        <div className="card p-8 mb-8"
          dangerouslySetInnerHTML={{ __html: data.guide.content }} />
      ) : (
        <div className="card p-8 mb-8">
          <h2 className="font-bold text-white text-xl mb-6">مراحل انتخاب قطعه مناسب</h2>
          <div className="space-y-6">
            {[
              { step: '۱', title: 'تعیین کاربرد', desc: 'آیا دوربین برای نظارت داخلی است یا خارجی؟ آیا شب هم باید تصویر بگیرد؟' },
              { step: '۲', title: 'انتخاب رزولوشن', desc: '2 مگاپیکسل برای فضاهای کوچک، 4MP برای متوسط و 8MP برای فضاهای بزرگ مناسب است.' },
              { step: '۳', title: 'انتخاب لنز', desc: 'فاصله دید مستقیم با focal length لنز رابطه دارد. برای فضاهای باز لنز با focal بیشتر مناسب است.' },
              { step: '۴', title: 'انتخاب برد', desc: 'برد باید با لنز و رزولوشن سازگار باشد. به ولتاژ ورودی توجه کنید.' },
              { step: '۵', title: 'محاسبه کابل‌کشی', desc: 'طول مسیر کابل را حساب کنید. برای مسافت‌های طولانی از کابل با سطح مقطع بیشتر استفاده کنید.' },
            ].map(item => (
              <div key={item.step} className="flex gap-4">
                <div className="w-10 h-10 bg-brand rounded-full flex items-center justify-center text-white font-bold flex-shrink-0">
                  {item.step}
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                  <p className="text-sm text-gray-steel">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ویدیوهای مرتبط */}
      {data?.videos?.length > 0 && (
        <div>
          <h2 className="font-bold text-white text-xl mb-4">🎬 ویدیوهای آموزشی</h2>
          <div className="grid grid-cols-2 gap-4">
            {data.videos.map(v => (
              <Link key={v.slug} to={`/videos/${v.slug}`}
                className="card p-4 hover:border-brand/30 transition-all flex items-center gap-3">
                <div className="w-12 h-12 bg-brand/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <span className="text-xl">▶️</span>
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{v.title}</div>
                  <div className="text-xs text-gray-steel">⏱ {v.duration} دقیقه</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
