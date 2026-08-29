import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { formatDate } from '../../utils/date'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// تاریخ محلی YYYY-MM-DD برای n روز قبل
const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toLocaleDateString('en-CA')
}

const QUICK_RANGES = [
  { label: '۳۰ روز اخیر', get: () => [daysAgo(30), daysAgo(0)] },
  { label: '۹۰ روز اخیر', get: () => [daysAgo(90), daysAgo(0)] },
]

// ─── گزارش پیش‌فاکتورهای ردشده ────────────────────────────────
export default function RejectReportPage() {
  const [from, setFrom] = useState(daysAgo(30))
  const [to, setTo] = useState(daysAgo(0))

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reject-report', from, to],
    queryFn: () => api.get('/orders/admin/reject-report/', {
      params: { from: from || undefined, to: to || undefined },
    }).then(r => r.data),
  })

  const items = data?.items || []

  return (
    <div className="container-main py-8">
      <div className="mb-6">
        <h1 className="font-display font-bold text-2xl text-white">گزارش رد سفارش‌ها</h1>
        <p className="text-xs text-gray-steel mt-1">
          پیش‌فاکتورهایی که توسط پرسنل رد شده‌اند، به همراه علت رد
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
      ) : (
        <>
          {/* خلاصه */}
          <div className="card p-4 mb-6 flex items-center gap-3">
            <span className="text-2xl">✗</span>
            <div>
              <div className="text-xs text-gray-steel">تعداد پیش‌فاکتورهای ردشده</div>
              <div className="text-xl font-bold text-red-400">{fmt(data?.total ?? items.length)}</div>
            </div>
          </div>

          {items.length === 0 ? (
            <div className="text-center py-10 text-gray-steel">در این بازه سفارش ردشده‌ای ثبت نشده است</div>
          ) : (
            <div className="card overflow-hidden overflow-x-auto">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 700 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)' }}>
                    {['شماره سفارش', 'مشتری', 'دلیل رد', 'تاریخ رد'].map(h => (
                      <th key={h} style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <tr key={it.order_number ?? i}
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span className="font-mono text-xs text-brand">{it.order_number}</span>
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: 12 }}>
                        <div style={{ color: 'var(--color-text-primary)' }}>{it.customer_name || '—'}</div>
                        <div className="text-gray-steel text-[11px] mt-0.5" dir="ltr">{it.customer_phone || ''}</div>
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--color-text-secondary)' }}>{it.reason || '—'}</td>
                      <td style={{ padding: '10px 12px', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(it.rejected_at, { withTime: true })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
