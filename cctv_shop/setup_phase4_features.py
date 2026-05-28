import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── قابلیت ۱۸: نمودار قیمت در صفحه محصول ───────────────────
price_chart_component = '''
// ─── نمودار تغییر قیمت ───────────────────────────────────────
function PriceChart({ slug }) {
  const { data: history = [] } = useQuery({
    queryKey: ['price-history', slug],
    queryFn: () => api.get(`/catalog/products/${slug}/price-history/`).then(r => r.data),
    staleTime: 3600000,
  })

  if (history.length < 2) return null

  const prices = history.map(h => h.price)
  const dates = history.map(h => h.date.slice(5))
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const W = 500, H = 120, PL = 10, PR = 10, PT = 10, PB = 30

  const points = prices.map((p, i) => {
    const x = PL + (i / (prices.length - 1)) * (W - PL - PR)
    const y = PT + (1 - (p - min) / range) * (H - PT - PB)
    return [x, y]
  })

  const polyline = points.map(p => p.join(',')).join(' ')
  const latest = prices[prices.length - 1]
  const prev = prices[prices.length - 2]
  const change = ((latest - prev) / prev * 100).toFixed(1)
  const isUp = latest >= prev

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display font-bold text-xl text-white">📈 تغییر قیمت ۳۰ روزه</h2>
        <span className={`text-sm font-bold px-3 py-1 rounded-full ${isUp ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
          {isUp ? '▲' : '▼'} {Math.abs(change)}%
        </span>
      </div>
      <div className="card p-4">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{height: 120}}>
          {/* خط راهنما */}
          {[0, 0.5, 1].map((t, i) => (
            <line key={i}
              x1={PL} x2={W-PR}
              y1={PT + t*(H-PT-PB)}
              y2={PT + t*(H-PT-PB)}
              stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
          ))}
          {/* نمودار */}
          <polyline points={polyline}
            fill="none" stroke="#0066FF" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" />
          {/* سایه زیر نمودار */}
          <polyline
            points={`${points[0][0]},${H-PB} ${polyline} ${points[points.length-1][0]},${H-PB}`}
            fill="url(#grad)" opacity="0.3" />
          <defs>
            <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0066FF" />
              <stop offset="100%" stopColor="#0066FF" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* نقطه آخر */}
          <circle cx={points[points.length-1][0]} cy={points[points.length-1][1]}
            r="4" fill="#0066FF" />
          {/* برچسب‌های تاریخ */}
          {[0, Math.floor(dates.length/2), dates.length-1].map(i => (
            <text key={i} x={points[i][0]} y={H-5}
              textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="9">
              {dates[i]}
            </text>
          ))}
        </svg>
        <div className="flex justify-between text-xs text-gray-steel mt-1">
          <span>کمترین: {min.toLocaleString('fa-IR')} ت</span>
          <span>بیشترین: {max.toLocaleString('fa-IR')} ت</span>
        </div>
      </div>
    </section>
  )
}

'''

# اضافه کردن به ProductDetailPage
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')
with open(page_path, encoding='utf-8') as f:
    content = f.read()

if 'PriceChart' not in content:
    content = content.replace(
        '// ─── جایگزین‌های پیشنهادی',
        price_chart_component + '// ─── جایگزین‌های پیشنهادی'
    )
    content = content.replace(
        '      {/* جایگزین‌های پیشنهادی */}',
        '      {/* نمودار قیمت */}\n      <PriceChart slug={product.slug} />\n\n      {/* جایگزین‌های پیشنهادی */}'
    )
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ PriceChart به ProductDetailPage اضافه شد")

# ─── قابلیت ۱۹: صفحه دانلودها ────────────────────────────────
downloads_page = '''import { Link } from 'react-router-dom'

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
'''

with open(os.path.join(FRONTEND, 'pages', 'DownloadsPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(downloads_page)
print("✓ DownloadsPage ساخته شد")

# ─── قابلیت ۲۰: قوانین و حریم خصوصی ─────────────────────────
terms_page = '''import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

export default function TermsPage() {
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 600000,
  })

  return (
    <div className="container-main py-12 max-w-3xl">
      <h1 className="font-display font-bold text-3xl text-white mb-8">📋 قوانین و مقررات</h1>
      <div className="card p-8 space-y-6 text-sm text-gray-300 leading-loose">
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۱. شرایط استفاده</h2>
          <p>با استفاده از این سایت، شما با تمام قوانین و مقررات آن موافقت می‌کنید. این سایت متعلق به {settings?.site_name || "فروشگاه قطعات دوربین"} است.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۲. سفارش و پرداخت</h2>
          <p>تمام سفارشات پس از تأیید موجودی کالا و دریافت پرداخت، پردازش می‌شوند. قیمت‌ها ممکن است بدون اطلاع قبلی تغییر کنند.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۳. ارسال کالا</h2>
          <p>ارسال در سراسر ایران انجام می‌شود. زمان تحویل بسته به موقعیت جغرافیایی ۲ تا ۷ روز کاری است.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۴. ضمانت و مرجوعی</h2>
          <p>کالاهای معیوب تا ۷ روز پس از دریافت قابل مرجوع هستند. ضمانت اصالت کالا از سمت فروشگاه تضمین می‌شود.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۵. تماس با ما</h2>
          <p>برای هرگونه سؤال با {settings?.contact_phone || "ما"} تماس بگیرید.</p>
          {settings?.working_hours && <p>ساعات کاری: {settings.working_hours}</p>}
        </section>
      </div>
    </div>
  )
}
'''

privacy_page = '''import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

export default function PrivacyPage() {
  const { data: settings } = useQuery({
    queryKey: ['site-settings'],
    queryFn: () => api.get('/core/settings/').then(r => r.data),
    staleTime: 600000,
  })

  return (
    <div className="container-main py-12 max-w-3xl">
      <h1 className="font-display font-bold text-3xl text-white mb-8">🔒 حریم خصوصی</h1>
      <div className="card p-8 space-y-6 text-sm text-gray-300 leading-loose">
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۱. اطلاعات جمع‌آوری شده</h2>
          <p>اطلاعاتی مانند نام، شماره تماس و آدرس برای پردازش سفارشات جمع‌آوری می‌شود. این اطلاعات به اشخاص ثالث فروخته نمی‌شود.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۲. استفاده از اطلاعات</h2>
          <p>اطلاعات شما برای پردازش سفارش، ارسال اطلاع‌رسانی‌های مرتبط و بهبود خدمات استفاده می‌شود.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۳. امنیت اطلاعات</h2>
          <p>تمام اطلاعات شما با استفاده از پروتکل‌های امنیتی استاندارد رمزگذاری و محافظت می‌شود.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۴. کوکی‌ها</h2>
          <p>این سایت از کوکی‌ها برای بهبود تجربه کاربری استفاده می‌کند. با استفاده از سایت با این سیاست موافقت می‌کنید.</p>
        </section>
        <section>
          <h2 className="font-bold text-white text-lg mb-3">۵. تماس</h2>
          <p>برای هرگونه سؤال درباره حریم خصوصی با {settings?.contact_email || settings?.contact_phone || "ما"} تماس بگیرید.</p>
        </section>
      </div>
    </div>
  )
}
'''

with open(os.path.join(FRONTEND, 'pages', 'TermsPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(terms_page)
with open(os.path.join(FRONTEND, 'pages', 'PrivacyPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(privacy_page)
print("✓ TermsPage و PrivacyPage ساخته شدند")

# ─── قابلیت ۲۱: آپلود Excel ──────────────────────────────────
excel_page = '''import { useState, useRef } from 'react'
import api from '../services/api'
import * as XLSX from 'xlsx'

const TEMPLATE_HEADERS = [
  'name', 'category', 'brand', 'model_number', 'description',
  'sensor_name', 'voltage', 'lens_name', 'board_name',
  'sku', 'purchase_price_cny', 'profit_percent', 'stock_quantity'
]

function downloadTemplate() {
  const ws = XLSX.utils.aoa_to_sheet([
    TEMPLATE_HEADERS,
    ['نام محصول نمونه', 'لنز دوربین مداربسته', 'YTOT', 'YT-1000', 'توضیحات',
     'Sony IMX335', '12V', 'لنز 3.6mm', '', 'SKU001', '15.5', '30', '100']
  ])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'محصولات')
  XLSX.writeFile(wb, 'products_template.xlsx')
}

export default function BulkUploadPage() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState([])
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const fileRef = useRef()

  function handleFile(e) {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)

    const reader = new FileReader()
    reader.onload = (ev) => {
      const wb = XLSX.read(ev.target.result, { type: 'binary' })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })
      setPreview(rows.slice(0, 6))
    }
    reader.readAsBinaryString(f)
  }

  async function handleUpload() {
    if (!file) return
    setStatus('loading')
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post('/catalog/products/bulk-upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)
      setStatus('success')
    } catch (e) {
      setStatus('error')
      setResult({ error: e.response?.data?.error || 'خطا در آپلود' })
    }
  }

  return (
    <div className="container-main py-12 max-w-3xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-display font-bold text-2xl text-white">📊 آپلود دسته‌جمعی محصولات</h1>
        <button onClick={downloadTemplate}
          className="btn-secondary text-sm px-4 py-2 flex items-center gap-2">
          ⬇️ دانلود Template
        </button>
      </div>

      {/* راهنما */}
      <div className="card p-5 mb-6">
        <h3 className="font-semibold text-white mb-3">مراحل آپلود:</h3>
        <ol className="space-y-2 text-sm text-gray-steel list-decimal list-inside">
          <li>فایل Template را دانلود کنید</li>
          <li>اطلاعات محصولات را در فایل Excel وارد کنید</li>
          <li>فایل تکمیل شده را آپلود کنید</li>
          <li>پیش‌نمایش را بررسی و تأیید کنید</li>
        </ol>
      </div>

      {/* آپلود */}
      <div className="card p-6 mb-6">
        <div
          onClick={() => fileRef.current.click()}
          className="border-2 border-dashed border-white/20 rounded-xl p-10 text-center cursor-pointer hover:border-brand/50 transition-all">
          <div className="text-4xl mb-3">📁</div>
          <div className="text-white font-semibold mb-1">
            {file ? file.name : 'کلیک کنید یا فایل را اینجا رها کنید'}
          </div>
          <div className="text-xs text-gray-steel">فرمت‌های مجاز: .xlsx, .xls</div>
        </div>
        <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
      </div>

      {/* پیش‌نمایش */}
      {preview.length > 0 && (
        <div className="card p-5 mb-6 overflow-x-auto">
          <h3 className="font-semibold text-white mb-3">پیش‌نمایش فایل:</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            {preview.map((row, i) => (
              <tr key={i} style={{ background: i === 0 ? 'rgba(0,102,255,0.1)' : 'transparent' }}>
                {row.map((cell, j) => (
                  <td key={j} style={{ padding: '6px 10px', borderBottom: '1px solid rgba(255,255,255,0.05)',
                    color: i === 0 ? '#0066FF' : '#fff', fontWeight: i === 0 ? 600 : 400 }}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </table>
        </div>
      )}

      {/* نتیجه */}
      {result && (
        <div className={`card p-5 mb-6 ${status === 'success' ? 'border-green-500/30' : 'border-red-500/30'}`}>
          {status === 'success' ? (
            <div className="text-green-400">
              <div className="font-bold mb-2">✅ آپلود موفق</div>
              <div className="text-sm">ایجاد شده: {result.created} | آپدیت: {result.updated} | خطا: {result.errors}</div>
            </div>
          ) : (
            <div className="text-red-400">❌ {result.error}</div>
          )}
        </div>
      )}

      <button onClick={handleUpload} disabled={!file || status === 'loading'}
        className="btn-primary w-full py-3 text-sm font-semibold disabled:opacity-50">
        {status === 'loading' ? 'در حال آپلود...' : '📤 آپلود و وارد کردن محصولات'}
      </button>
    </div>
  )
}
'''

with open(os.path.join(FRONTEND, 'pages', 'BulkUploadPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(excel_page)
print("✓ BulkUploadPage ساخته شد")

# آپدیت App.jsx
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

imports_to_add = ""
if 'DownloadsPage' not in app:
    imports_to_add += "import DownloadsPage from './pages/DownloadsPage'\n"
if 'TermsPage' not in app:
    imports_to_add += "import TermsPage from './pages/TermsPage'\n"
if 'PrivacyPage' not in app:
    imports_to_add += "import PrivacyPage from './pages/PrivacyPage'\n"
if 'BulkUploadPage' not in app:
    imports_to_add += "import BulkUploadPage from './pages/BulkUploadPage'\n"

if imports_to_add:
    app = app.replace("import TrackingPage", imports_to_add + "import TrackingPage")

routes_to_add = ""
if 'downloads' not in app:
    routes_to_add += '\n        <Route path="downloads" element={<DownloadsPage />} />'
if 'terms' not in app:
    routes_to_add += '\n        <Route path="terms" element={<TermsPage />} />'
if 'privacy' not in app:
    routes_to_add += '\n        <Route path="privacy" element={<PrivacyPage />} />'
if 'bulk-upload' not in app:
    routes_to_add += '\n        <Route path="admin/bulk-upload" element={<RequireAuth><BulkUploadPage /></RequireAuth>} />'

if routes_to_add:
    app = app.replace('<Route path="track"', routes_to_add + '\n        <Route path="track"')

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(app)
print("✓ App.jsx آپدیت شد")

# آپدیت Footer — اضافه کردن لینک‌ها
footer_path = os.path.join(FRONTEND, 'components', 'layout', 'Footer.jsx')
with open(footer_path, encoding='utf-8') as f:
    footer = f.read()

if '/terms' not in footer:
    footer = footer.replace(
        "['🇨🇳 سفارش از چین', '/china-order'],",
        "['🇨🇳 سفارش از چین', '/china-order'],\n                ['⬇️ دانلودها', '/downloads'],\n                ['📋 قوانین', '/terms'],\n                ['🔒 حریم خصوصی', '/privacy'],"
    )
    with open(footer_path, 'w', encoding='utf-8') as f:
        f.write(footer)
    print("✓ لینک‌های footer اضافه شدند")

# آپدیت Layout — اضافه کردن bulk-upload به sidebar
layout_path = os.path.join(FRONTEND, 'components', 'layout', 'Layout.jsx')
with open(layout_path, encoding='utf-8') as f:
    layout = f.read()

if 'bulk-upload' not in layout:
    layout = layout.replace(
        "{ label: 'نقش‌ها و پرسنل',",
        "{ label: 'آپلود Excel',        path: '/admin/bulk-upload', perm: 'products_edit', icon: '📊' },\n  { label: 'نقش‌ها و پرسنل',"
    )
    with open(layout_path, 'w', encoding='utf-8') as f:
        f.write(layout)
    print("✓ آپلود Excel به sidebar اضافه شد")

print("\nصفحات جدید:")
print("  /downloads — دانلودها")
print("  /terms — قوانین و مقررات")
print("  /privacy — حریم خصوصی")
print("  /admin/bulk-upload — آپلود دسته‌جمعی Excel")
