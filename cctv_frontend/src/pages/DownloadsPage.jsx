import { Link } from 'react-router-dom'

const DOWNLOADS = [
  {
    category: '🔧 ابزارهای نرم‌افزاری',
    items: [
      { name: 'IPC Config Tool', desc: 'تنظیم سریع دوربین‌های IP از طریق شبکه', url: 'https://www.dahuasecurity.com/tools', size: '8 MB' },
      { name: 'SADP Tool', desc: 'جستجو و تنظیم دوربین‌های هایک‌ویژن', url: 'https://www.hikvision.com/en/support/tools/', size: '12 MB' },
      { name: 'IPCam Search', desc: 'اسکن شبکه برای یافتن دوربین‌ها', url: 'https://www.advanced.co.uk/tools', size: '3 MB' },
    ]
  },
  {
    category: '📱 اپلیکیشن موبایل',
    items: [
      { name: 'iDMSS Plus (iOS)', desc: 'مشاهده دوربین‌های داهوا روی آیفون', url: 'https://apps.apple.com/app/idmss-plus/id389563047', size: 'App Store' },
      { name: 'gDMSS Plus (Android)', desc: 'مشاهده دوربین‌های داهوا روی اندروید', url: 'https://play.google.com/store/apps/details?id=com.mm.android.DMSS', size: 'Play Store' },
      { name: 'Hik-Connect', desc: 'اپ رسمی هایک‌ویژن', url: 'https://www.hikvision.com/en/support/download/app/', size: 'App Store/Play Store' },
    ]
  },
  {
    category: '📚 راهنماها و مستندات',
    items: [
      { name: 'راهنمای نصب دوربین IP', desc: 'مراحل گام به گام نصب و راه‌اندازی', url: '/guides/part-selection', size: 'آنلاین' },
      { name: 'راهنمای انتخاب لنز', desc: 'نحوه انتخاب لنز مناسب بر اساس فاصله', url: '/blog', size: 'آنلاین' },
    ]
  },
  {
    category: '🛠️ SDK و ابزار توسعه',
    items: [
      { name: 'Dahua SDK', desc: 'کیت توسعه نرم‌افزار داهوا', url: 'https://developer.dahuasecurity.com', size: 'متغیر' },
      { name: 'Hikvision SDK', desc: 'کیت توسعه نرم‌افزار هایک‌ویژن', url: 'https://developer.hikvision.com', size: 'متغیر' },
    ]
  },
]

export default function DownloadsPage() {
  return (
    <div className="container-main py-12 max-w-4xl">
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-3xl text-white mb-3">⬇️ دانلودها</h1>
        <p className="text-gray-steel">نرم‌افزارها، اپلیکیشن‌ها و راهنماهای مورد نیاز</p>
      </div>

      <div className="space-y-8">
        {DOWNLOADS.map(cat => (
          <div key={cat.category}>
            <h2 className="font-bold text-white text-lg mb-4">{cat.category}</h2>
            <div className="grid grid-cols-1 gap-3">
              {cat.items.map(item => (
                <a key={item.name} href={item.url} target="_blank" rel="noopener noreferrer"
                  className="card p-4 flex items-center gap-4 hover:border-brand/30 transition-all group">
                  <div className="w-10 h-10 bg-brand/20 rounded-xl flex items-center justify-center flex-shrink-0 text-xl">
                    ⬇️
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-white group-hover:text-brand transition-colors">{item.name}</div>
                    <div className="text-xs text-gray-steel mt-0.5">{item.desc}</div>
                  </div>
                  <div className="text-xs text-gray-steel">{item.size}</div>
                </a>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="card p-6 mt-8 text-center">
        <div className="text-2xl mb-2">❓</div>
        <p className="text-sm text-gray-steel">نرم‌افزار مورد نیاز خود را پیدا نکردید؟</p>
        <Link to="/china-order" className="btn-primary text-sm px-6 py-2.5 mt-3 inline-block">
          درخواست تهیه نرم‌افزار
        </Link>
      </div>
    </div>
  )
}
