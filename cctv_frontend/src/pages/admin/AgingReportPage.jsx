import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { formatPrice } from '../../utils/format'

// ─── گزارش aging مطالبات مشتریان ─────────────────────────────
export default function AgingReportPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['aging-report'],
    queryFn: () => api.get('/accounting/reports/aging/').then(r => r.data),
  })

  const rows = data?.results || data || []
  const debtors = rows.filter(r => Number(r.total) > 0)
  const sumTotal = debtors.reduce((s, r) => s + Number(r.total || 0), 0)
  const sumOverdue = debtors.reduce((s, r) => s + Number(r.overdue_1_15 || 0) + Number(r.overdue_15_plus || 0), 0)

  return (
    <div className="container-main py-8">
      <h1 className="font-display font-bold text-2xl text-white mb-6">مطالبات تاریخ‌گذشته</h1>

      {/* کارت‌های خلاصه */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold text-white">{debtors.length.toLocaleString('fa-IR')}</div>
          <div className="text-xs text-gray-steel mt-1">مشتریان بدهکار</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-lg font-bold text-brand">{formatPrice(sumTotal)}</div>
          <div className="text-xs text-gray-steel mt-1">جمع کل مطالبات</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-lg font-bold text-red-400">{formatPrice(sumOverdue)}</div>
          <div className="text-xs text-gray-steel mt-1">جمع معوقه</div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel">در حال بارگذاری...</div>
      ) : isError ? (
        <div className="text-center py-10">
          <div className="text-gray-steel mb-3">خطا در دریافت گزارش</div>
          <button onClick={() => refetch()} className="btn-secondary text-sm px-5 py-2">تلاش مجدد</button>
        </div>
      ) : rows.length === 0 ? (
        <div className="text-center py-10 text-gray-steel">داده‌ای یافت نشد</div>
      ) : (
        <div className="card overflow-hidden overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 800 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)' }}>
                {['مشتری', 'سررسید نرسیده', '۱–۱۵ روز معوق', 'بیش از ۱۵ روز معوق', 'جمع'].map(h => (
                  <th key={h} style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.user_id ?? i}
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px' }}>
                    <div style={{ color: 'var(--color-text-primary)', fontSize: 12 }}>{r.name || '—'}</div>
                    <div className="text-gray-steel text-[11px] mt-0.5" dir="ltr">{r.phone || ''}</div>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: 12 }}>{formatPrice(r.not_due)}</td>
                  <td style={{ padding: '10px 12px', fontSize: 12, color: '#FF9500' }}>{formatPrice(r.overdue_1_15)}</td>
                  <td style={{ padding: '10px 12px', fontSize: 12, color: '#FF3B3B', fontWeight: Number(r.overdue_15_plus) > 0 ? 700 : 400 }}>
                    {formatPrice(r.overdue_15_plus)}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{formatPrice(r.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
