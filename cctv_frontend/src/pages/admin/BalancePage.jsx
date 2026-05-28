import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function BalancePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['balance-report'],
    queryFn: () => api.get('/accounting/reports/balance/').then(r => r.data),
  })

  const contacts = data?.contacts || []
  const totalDebtIrr = contacts.filter(c => c.balance_irr > 0).reduce((s, c) => s + c.balance_irr, 0)
  const totalCreditIrr = contacts.filter(c => c.balance_irr < 0).reduce((s, c) => s + Math.abs(c.balance_irr), 0)
  const totalDebtCny = contacts.filter(c => c.balance_cny > 0).reduce((s, c) => s + c.balance_cny, 0)
  const totalCreditCny = contacts.filter(c => c.balance_cny < 0).reduce((s, c) => s + Math.abs(c.balance_cny), 0)

  return (
    <div className="container-main py-8 max-w-5xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">تراز حساب‌ها</h1>

      {/* خلاصه */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بدهکاران (ریال)</div>
          <div className="text-lg font-bold text-red-400">{fmt(totalDebtIrr)}</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بستانکاران (ریال)</div>
          <div className="text-lg font-bold text-green-400">{fmt(totalCreditIrr)}</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بدهکاران (یوان)</div>
          <div className="text-lg font-bold text-red-400">{fmt(totalDebtCny)} ¥</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">جمع بستانکاران (یوان)</div>
          <div className="text-lg font-bold text-green-400">{fmt(totalCreditCny)} ¥</div>
        </div>
      </div>

      {/* جدول تراز */}
      <div className="card p-5">
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-12 text-gray-steel">هنوز تراکنشی ثبت نشده</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['طرف حساب', 'نوع', 'وضعیت ریالی', 'مانده ریال', 'وضعیت یوانی', 'مانده یوان'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contacts.map((c, i) => (
                <tr key={c.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{c.name}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{c.contact_type_display}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896',
                      background: (c.balance_irr > 0 ? '#FF3B3B' : '#00C896') + '20',
                      padding: '2px 10px', borderRadius: 20, fontSize: 11
                    }}>{c.status_irr}</span>
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_irr > 0 ? '#FF3B3B' : '#00C896' }}>
                    {fmt(Math.abs(c.balance_irr))} ت
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {c.balance_cny !== 0 && (
                      <span style={{
                        color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896',
                        background: (c.balance_cny > 0 ? '#FF3B3B' : '#00C896') + '20',
                        padding: '2px 10px', borderRadius: 20, fontSize: 11
                      }}>{c.status_cny}</span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: c.balance_cny > 0 ? '#FF3B3B' : '#00C896' }}>
                    {c.balance_cny !== 0 ? `${fmt(Math.abs(c.balance_cny))} ¥` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
