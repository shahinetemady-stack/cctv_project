import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import { formatDate } from '../../utils/date'

const ACTION_COLORS = {
  login:  '#00C896',
  logout: '#888888',
  create: '#0066FF',
  update: '#FF9500',
  delete: '#FF3B3B',
}

export default function AdminLogsPage() {
  const [filters, setFilters] = useState({ action: '', date: '', page: 1 })
  const set = (k, v) => setFilters(f => ({ ...f, [k]: v, page: k === 'page' ? v : 1 }))

  const { data, isLoading } = useQuery({
    queryKey: ['activity-logs', filters],
    queryFn: () => api.get('/users/activity-logs/', {
      params: {
        ...(filters.action ? { action: filters.action } : {}),
        ...(filters.date ? { date: filters.date } : {}),
        page: filters.page,
      },
    }).then(r => r.data),
  })

  const rows = data?.results || []

  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">📋 لاگ فعالیت‌ها</h1>

      {/* فیلترها */}
      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap">
        <select value={filters.action} onChange={e => set('action', e.target.value)} className="input-dark text-xs w-36">
          <option value="">همه رویدادها</option>
          <option value="login">ورود</option>
          <option value="logout">خروج</option>
          <option value="create">ایجاد</option>
          <option value="update">ویرایش</option>
          <option value="delete">حذف</option>
        </select>
        <input type="date" value={filters.date} onChange={e => set('date', e.target.value)} className="input-dark text-xs w-40" />
        {(filters.action || filters.date) && (
          <button onClick={() => setFilters({ action: '', date: '', page: 1 })} className="text-xs text-red-400 hover:text-red-300">
            ✕ پاک کردن فیلتر
          </button>
        )}
        <span className="text-[11px] text-gray-steel mr-auto">
          {data ? `${Number(data.total).toLocaleString('fa-IR')} رویداد` : ''}
        </span>
      </div>

      <div className="card overflow-x-auto">
        {isLoading ? <PageLoader /> : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid var(--color-border-strong)' }}>
                {['#', 'زمان', 'کاربر', 'رویداد', 'متد', 'مسیر', 'وضعیت'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 11 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.id} style={{ borderBottom: '0.5px solid var(--color-border)', background: i % 2 ? 'var(--color-brand-softer)' : 'transparent' }}>
                  <td style={{ padding: '8px 12px', color: 'var(--color-text-muted)', fontSize: 10 }}>{((filters.page - 1) * 50 + i + 1).toLocaleString('fa-IR')}</td>
                  <td style={{ padding: '8px 12px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }} dir="ltr">{formatDate(r.created_at, { withTime: true })}</td>
                  <td style={{ padding: '8px 12px', fontWeight: 600 }}>{r.user}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      color: ACTION_COLORS[r.action] || '#888',
                      background: (ACTION_COLORS[r.action] || '#888') + '20',
                      padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap',
                    }}>{r.action_display}</span>
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11, color: 'var(--color-text-secondary)' }} dir="ltr">{r.method}</td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11, color: 'var(--color-text-secondary)' }} dir="ltr">{r.path}</td>
                  <td style={{ padding: '8px 12px', fontSize: 11, color: r.status < 400 ? '#00C896' : '#FF3B3B' }} dir="ltr">{r.status}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={7} className="text-center py-12 text-gray-steel text-sm">رویدادی یافت نشد</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* صفحه‌بندی */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button onClick={() => set('page', Math.max(1, filters.page - 1))} disabled={filters.page <= 1}
            className="btn-secondary text-xs px-4 py-2 disabled:opacity-40">→ قبلی</button>
          <span className="text-xs text-gray-steel">صفحه {filters.page.toLocaleString('fa-IR')} از {data.pages.toLocaleString('fa-IR')}</span>
          <button onClick={() => set('page', Math.min(data.pages, filters.page + 1))} disabled={filters.page >= data.pages}
            className="btn-secondary text-xs px-4 py-2 disabled:opacity-40">بعدی ←</button>
        </div>
      )}
    </div>
  )
}
