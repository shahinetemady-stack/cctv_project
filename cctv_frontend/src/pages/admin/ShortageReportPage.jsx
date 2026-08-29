import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// تاریخ محلی YYYY-MM-DD برای n روز قبل
const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toLocaleDateString('en-CA')
}

const QUICK_RANGES = [
  { label: 'ماه گذشته', get: () => {
      // ماه میلادی گذشته — از اولین تا آخرین روز
      const d = new Date()
      const first = new Date(d.getFullYear(), d.getMonth() - 1, 1)
      const last = new Date(d.getFullYear(), d.getMonth(), 0)
      return [first.toLocaleDateString('en-CA'), last.toLocaleDateString('en-CA')]
    } },
  { label: '۳۰ روز اخیر', get: () => [daysAgo(30), daysAgo(0)] },
  { label: '۹۰ روز اخیر', get: () => [daysAgo(90), daysAgo(0)] },
]

// ─── گزارش مازاد تقاضا (کسری موجودی هنگام تایید) ─────────────
export default function ShortageReportPage() {
  const [from, setFrom] = useState(daysAgo(30))
  const [to, setTo] = useState(daysAgo(0))

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['shortage-report', from, to],
    queryFn: () => api.get('/orders/admin/shortage-report/', {
      params: { from: from || undefined, to: to || undefined },
    }).then(r => r.data),
  })

  const items = data?.items || []

  return (
    <div className="container-main py-8">
      <div className="mb-6">
        <h1 className="font-display font-bold text-2xl text-white">گزارش مازاد تقاضا</h1>
        <p className="text-xs text-gray-steel mt-1">
          بر اساس کاهش/حذف اقلام توسط پرسنل هنگام تایید پیش‌فاکتور
        </p>
      </div>

      {/* بازه زمانی */}
      <div className="flex items-end gap-3 mb-6 flex-wrap">
        <div>
          <label className="label text-xs mb-1 block">از تاریخ</label>
          <input type="date" value={from} onChange={e => setFrom(e.target.value)}
            className="input text-sm" dir="ltr" />
        </div>
        <div>
          <label className="label text-xs mb-1 block">تا تاریخ</label>
          <input type="date" value={to} onChange={e => setTo(e.target.value)}
            className="input text-sm" dir="ltr" />
        </div>
        <div className="flex gap-2">
          {QUICK_RANGES.map(q => (
            <button key={q.label} onClick={() => { const [f, t] = q.get(); setFrom(f); setTo(t) }}
              className="text-xs px-4 py-2.5 rounded-xl border border-white/10 text-gray-steel hover:border-brand/40 hover:text-brand transition-all">
              {q.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel">در حال بارگذاری...</div>
      ) : isError ? (
        <div className="text-center py-10">
          <div className="text-gray-steel mb-3">خطا در دریافت گزارش</div>
          <button onClick={() => refetch()} className="btn-secondary text-sm px-5 py-2">تلاش مجدد</button>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-10 text-gray-steel">در این بازه مازاد تقاضایی ثبت نشده است</div>
      ) : (
        <div className="card overflow-hidden overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 700 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)' }}>
                {['کالا', 'SKU', 'جمع مازاد تقاضا', 'جمع درخواستی', 'تعداد سفارش‌ها'].map(h => (
                  <th key={h} style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={it.variant_id ?? i}
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-primary)', fontSize: 12 }}>{it.product_name}</td>
                  <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-secondary)' }} dir="ltr">{it.sku}</td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: '#FF3B3B' }}>{fmt(it.total_shortage)}</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(it.total_requested)}</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(it.orders_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
