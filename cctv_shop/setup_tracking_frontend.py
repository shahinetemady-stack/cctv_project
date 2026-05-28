import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── صفحه رهگیری ─────────────────────────────────────────────
tracking_page = '''import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function TrackingPage() {
  const { orderNumber } = useParams()
  const navigate = useNavigate()
  const [input, setInput] = useState(orderNumber || '')
  const [search, setSearch] = useState(orderNumber || '')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['track', search],
    queryFn: () => api.get(`/orders/${search}/track/`).then(r => r.data),
    enabled: !!search,
    retry: false,
  })

  function handleSearch(e) {
    e.preventDefault()
    if (input.trim()) {
      setSearch(input.trim())
      navigate(`/track/${input.trim()}`, { replace: true })
    }
  }

  return (
    <div className="container-main py-12 max-w-2xl">
      <div className="text-center mb-10">
        <div className="text-5xl mb-4">🚚</div>
        <h1 className="font-display font-bold text-3xl text-white mb-3">رهگیری مرسوله</h1>
        <p className="text-gray-steel text-sm">شماره سفارش خود را وارد کنید</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3 mb-8">
        <input value={input} onChange={e => setInput(e.target.value)}
          placeholder="مثلاً: ORD-20260514-E74246"
          className="input flex-1 text-sm font-mono" dir="ltr" />
        <button type="submit" className="btn-primary px-6 py-2.5 text-sm">
          رهگیری
        </button>
      </form>

      {isLoading && (
        <div className="text-center py-10 text-gray-steel">در حال جستجو...</div>
      )}

      {isError && (
        <div className="card p-6 text-center">
          <div className="text-4xl mb-3">❌</div>
          <div className="text-white font-semibold mb-2">سفارش یافت نشد</div>
          <div className="text-gray-steel text-sm">
            {error?.response?.data?.error || 'شماره سفارش را بررسی کنید'}
          </div>
        </div>
      )}

      {data && (
        <div className="space-y-4">
          {/* اطلاعات کلی */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="font-mono text-brand font-bold">{data.order_number}</div>
                <div className="text-xs text-gray-steel mt-0.5">{data.created_at}</div>
              </div>
              <span className="text-xs px-3 py-1 rounded-full"
                style={{
                  color: data.status === 'paid' ? '#00C896' : '#FF9500',
                  background: (data.status === 'paid' ? '#00C896' : '#FF9500') + '20'
                }}>
                {data.status_display}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-gray-steel mb-1">تعداد اقلام</div>
                <div className="font-bold text-white">{data.items_count}</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-gray-steel mb-1">مبلغ کل</div>
                <div className="font-bold text-white">{fmt(data.total)} ت</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-gray-steel mb-1">شرکت حمل</div>
                <div className="font-bold text-white">{data.courier_display || '—'}</div>
              </div>
            </div>
          </div>

          {/* کد رهگیری */}
          {data.tracking_code && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">کد رهگیری پستی</h3>
              <div className="flex items-center gap-3">
                <div className="font-mono text-xl text-brand bg-brand/10 px-4 py-2 rounded-lg flex-1 text-center" dir="ltr">
                  {data.tracking_code}
                </div>
                <button onClick={() => navigator.clipboard.writeText(data.tracking_code)}
                  className="btn-secondary text-xs px-3 py-2">
                  کپی
                </button>
              </div>
              {data.courier_display === 'پست' && (
                <a href={`https://tracking.post.ir/?id=${data.tracking_code}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-xs text-brand hover:text-brand/80 mt-2 block text-center">
                  رهگیری در سایت پست ایران ←
                </a>
              )}
            </div>
          )}

          {/* مراحل */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-5">وضعیت مرسوله</h3>
            <div className="relative">
              {/* خط اتصال */}
              <div className="absolute right-5 top-5 bottom-5 w-0.5 bg-white/10" />
              <div className="space-y-4">
                {data.steps?.map((step, i) => (
                  <div key={step.key} className="flex items-center gap-4 relative">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 z-10 text-lg border-2 transition-all ${
                      step.current ? 'border-brand bg-brand/20 scale-110' :
                      step.done ? 'border-green-400 bg-green-400/20' :
                      'border-white/20 bg-white/5'
                    }`}>
                      {step.icon}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-semibold ${
                        step.current ? 'text-brand' : step.done ? 'text-white' : 'text-gray-steel'
                      }`}>
                        {step.label}
                        {step.current && <span className="text-xs mr-2 text-brand">← وضعیت فعلی</span>}
                      </div>
                      {step.key === 'shipped' && data.shipped_at && (
                        <div className="text-xs text-gray-steel">{data.shipped_at}</div>
                      )}
                      {step.key === 'delivered' && data.delivered_at && (
                        <div className="text-xs text-gray-steel">{data.delivered_at}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
'''

with open(os.path.join(FRONTEND, 'pages', 'TrackingPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(tracking_page)
print("✓ TrackingPage.jsx ساخته شد")

# آپدیت App.jsx
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'TrackingPage' not in app:
    app = app.replace(
        "import ChinaOrderPage",
        "import TrackingPage from './pages/TrackingPage'\nimport ChinaOrderPage"
    )
    app = app.replace(
        '<Route path="china-order"',
        '<Route path="track" element={<TrackingPage />} />\n        <Route path="track/:orderNumber" element={<TrackingPage />} />\n        <Route path="china-order"'
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")

# اضافه کردن دکمه رهگیری در صفحه سفارشات کاربر
orders_page = os.path.join(FRONTEND, 'pages', 'account')
print("\nآدرس رهگیری:")
print("  /track — صفحه رهگیری")
print("  /track/ORD-XXXXXX — رهگیری مستقیم با شماره سفارش")
print("\nبرای تست در Django Admin:")
print("  http://127.0.0.1:8000/admin/orders/order/")
print("  فیلد delivery_status و tracking_code را پر کنید")
