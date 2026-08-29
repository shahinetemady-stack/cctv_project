import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function pct(n) { return Number(n || 0).toFixed(1) + '%' }

function ProfitTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['profit-report'],
    queryFn: () => api.get('/accounting/reports/profit/').then(r => r.data),
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!data) return null

  const s = data.summary

  return (
    <div>
      {/* خلاصه */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">کل فروش</div>
          <div className="text-base sm:text-lg font-bold text-white">{fmt(s.total_revenue)} ریال</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">بهای تمام شده</div>
          <div className="text-base sm:text-lg font-bold text-orange-400">{fmt(s.total_cost)} ریال</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">سود ناخالص ریالی</div>
          <div className={`text-base sm:text-lg font-bold ${s.total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(s.total_profit)} ریال</div>
          <div className="text-xs text-gray-steel mt-0.5">حاشیه: {pct(s.profit_margin)}</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-xs text-gray-steel mb-1">سود به یوان روز</div>
          <div className={`text-base sm:text-lg font-bold ${s.total_profit_cny >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(s.total_profit_cny)} ¥</div>
          <div className="text-xs text-gray-steel mt-0.5">نرخ روز: {fmt(s.exchange_rate)} ریال</div>
        </div>
      </div>

      {/* جدول */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">جزئیات سود هر فروش</h3>
        {data.items.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-sm">هنوز فاکتور فروش تأیید شده‌ای وجود ندارد</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['کالا', 'SKU', 'فاکتور', 'تعداد', 'قیمت فروش', 'بهای تمام شده', 'سود واحد', 'سود کل', 'سود یوانی'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((item, i) => (
                  <tr key={i} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '8px 10px' }}>{item.product}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{item.sku}</td>
                    <td style={{ padding: '8px 10px', color: '#0066FF', fontSize: 11 }}>{item.invoice_number}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>{fmt(item.quantity)}</td>
                    <td style={{ padding: '8px 10px' }}>{fmt(item.unit_price)}</td>
                    <td style={{ padding: '8px 10px', color: '#FF9500' }}>{fmt(item.unit_cost)}</td>
                    <td style={{ padding: '8px 10px', fontWeight: 600, color: item.profit_per_unit >= 0 ? '#00C896' : '#FF3B3B' }}>{fmt(item.profit_per_unit)}</td>
                    <td style={{ padding: '8px 10px', fontWeight: 700, color: item.profit_total >= 0 ? '#00C896' : '#FF3B3B' }}>{fmt(item.profit_total)}</td>
                    <td style={{ padding: '8px 10px', color: item.profit_cny >= 0 ? '#00C896' : '#FF3B3B' }}>{fmt(item.profit_cny)} ¥</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function BalanceSheetTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['balance-sheet'],
    queryFn: () => api.get('/accounting/reports/balance-sheet/').then(r => r.data),
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (!data) return null

  const { assets, liabilities, equity, profit } = data

  return (
    <div className="space-y-6">
      {/* سود/زیان */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">📊 سود و زیان</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <div className="bg-white/5 rounded-xl p-4 text-center">
            <div className="text-xs text-gray-steel mb-1">کل فروش</div>
            <div className="text-base sm:text-lg font-bold text-white">{fmt(profit.total_revenue)} ریال</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 text-center">
            <div className="text-xs text-gray-steel mb-1">بهای تمام شده فروش</div>
            <div className="text-base sm:text-lg font-bold text-orange-400">{fmt(profit.total_cost)} ریال</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 text-center">
            <div className="text-xs text-gray-steel mb-1">سود ناخالص</div>
            <div className={`text-base sm:text-lg font-bold ${profit.gross_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(profit.gross_profit)} ریال</div>
            <div className="text-xs text-gray-steel mt-0.5">حاشیه {profit.margin}%</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 text-center">
            <div className="text-xs text-gray-steel mb-1">سود به یوان</div>
            <div className={`text-base sm:text-lg font-bold ${profit.gross_profit_cny >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(profit.gross_profit_cny)} ¥</div>
            <div className="text-xs text-gray-steel mt-0.5">نرخ: {fmt(data.exchange_rate)} ریال</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* دارایی‌ها */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-green-400 mb-4">💰 دارایی‌ها</h3>
          <div className="space-y-3">
            {[
              { label: 'موجودی کالا (بهای تمام شده)', value: assets.stock_value, color: 'var(--color-text-primary)' },
              { label: 'طلب از مشتریان', value: assets.receivable, color: '#0066FF' },
              { label: 'موجودی صندوق/بانک (ریال)', value: assets.cash_irr, color: '#00C896' },
              { label: 'موجودی ارزی (یوان)', value: assets.cash_cny, suffix: ' ¥', color: '#FF9500' },
              { label: 'معادل ریالی موجودی ارزی', value: assets.cash_cny_irr, color: '#8B5CF6' },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between gap-2 bg-white/5 rounded-lg px-4 py-2.5">
                <div className="text-xs text-gray-steel">{item.label}</div>
                <div className="text-xs sm:text-sm font-bold text-left" style={{ color: item.color }}>
                  {fmt(item.value)}{item.suffix || ' ریال'}
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between gap-2 bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3">
              <div className="text-sm font-bold text-green-400">جمع دارایی‌ها</div>
              <div className="text-base sm:text-lg font-bold text-green-400 whitespace-nowrap">{fmt(assets.total)} ریال</div>
            </div>
          </div>
        </div>

        {/* بدهی‌ها */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-red-400 mb-4">📋 بدهی‌ها</h3>
          <div className="space-y-3">
            {[
              { label: 'بدهی به تامین‌کنندگان (ریال)', value: liabilities.payable_irr, color: '#FF3B3B' },
              { label: 'بدهی به شرکت‌های حمل (یوان)', value: liabilities.payable_cny, suffix: ' ¥', color: '#FF9500' },
              { label: 'معادل ریالی بدهی ارزی', value: liabilities.payable_cny_irr, color: '#FF6B6B' },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between gap-2 bg-white/5 rounded-lg px-4 py-2.5">
                <div className="text-xs text-gray-steel">{item.label}</div>
                <div className="text-xs sm:text-sm font-bold text-left" style={{ color: item.color }}>
                  {fmt(item.value)}{item.suffix || ' ریال'}
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
              <div className="text-sm font-bold text-red-400">جمع بدهی‌ها</div>
              <div className="text-base sm:text-lg font-bold text-red-400 whitespace-nowrap">{fmt(liabilities.total)} ریال</div>
            </div>

            {/* خالص دارایی */}
            <div className="flex items-center justify-between gap-2 bg-brand/10 border border-brand/30 rounded-lg px-4 py-3 mt-4">
              <div className="text-sm font-bold text-brand">خالص دارایی (حقوق صاحب)</div>
              <div className={`text-base sm:text-lg font-bold whitespace-nowrap ${equity >= 0 ? 'text-brand' : 'text-red-400'}`}>{fmt(equity)} ریال</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function FinancialReportsPage() {
  const [tab, setTab] = useState('profit')

  const tabs = [
    { key: 'profit', label: '📈 سود و زیان' },
    { key: 'balance', label: '⚖️ تراز کلی' },
  ]

  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">گزارشات مالی پیشرفته</h1>
      <div className="flex gap-2 mb-6 border-b border-white/10">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${tab === t.key ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'profit' && <ProfitTab />}
      {tab === 'balance' && <BalanceSheetTab />}
    </div>
  )
}

import { useState } from 'react'
