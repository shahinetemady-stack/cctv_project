import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'

const STATUS_FA = {
  pending: 'در انتظار', confirmed: 'تأیید شده',
  awaiting_payment: 'در انتظار پرداخت', paid: 'پرداخت شده',
  ready_to_ship: 'آماده ارسال', shipped: 'ارسال شده', cancelled: 'لغو شده',
}
const STATUS_COLOR = {
  pending: '#FF9500', confirmed: '#0066FF', awaiting_payment: '#8B5CF6',
  paid: '#00C896', ready_to_ship: '#00C896', shipped: '#0066FF', cancelled: '#FF3B3B',
}

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/stats/').then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: bs } = useQuery({
    queryKey: ['balance-sheet-dash'],
    queryFn: () => api.get('/accounting/reports/balance-sheet/').then(r => r.data),
    staleTime: 300000,
  })

  if (isLoading) return <PageLoader />
  if (isError) return (
    <div className="container-main py-20 text-center text-gray-steel">
      خطا در بارگذاری — با حساب ادمین وارد شوید
    </div>
  )

  const { sales, orders, users, inventory, monthly_sales, last_orders } = data
  const maxSale = Math.max(...monthly_sales.map(d => d.total), 1)

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-display font-bold text-2xl text-white">داشبورد مدیریت</h1>
        <span className="text-xs text-gray-steel">بروزرسانی خودکار هر دقیقه</span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block"></span>آمار فروش
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">امروز</div><div className="text-lg font-bold text-green-400">{fmt(sales.today)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">این هفته</div><div className="text-lg font-bold text-white">{fmt(sales.week)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">این ماه</div><div className="text-lg font-bold text-brand">{fmt(sales.month)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400 inline-block"></span>وضعیت سفارشات
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">امروز</div><div className="text-lg font-bold text-white">{fmt(orders.today)}</div><div className="text-[10px] text-gray-steel">سفارش</div></div>
            <div><div className="text-xs text-gray-steel mb-1">در انتظار</div><div className="text-lg font-bold text-orange-400">{fmt(orders.pending)}</div><div className="text-[10px] text-gray-steel">سفارش</div></div>
            <div><div className="text-xs text-gray-steel mb-1">پرداخت</div><div className="text-lg font-bold text-purple-400">{fmt(orders.awaiting_payment)}</div><div className="text-[10px] text-gray-steel">در انتظار</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-purple-400 inline-block"></span>کاربران
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">جدید امروز</div><div className="text-lg font-bold text-white">{fmt(users.new_today)}</div><div className="text-[10px] text-gray-steel">کاربر</div></div>
            <div><div className="text-xs text-gray-steel mb-1">درخواست همکار</div><div className="text-lg font-bold text-purple-400">{fmt(users.partner_requests)}</div><div className="text-[10px] text-gray-steel">در انتظار تأیید</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-orange-400 inline-block"></span>انبار
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">موجودی کم</div><div className="text-lg font-bold text-orange-400">{fmt(inventory.low_stock)}</div><div className="text-[10px] text-gray-steel">محصول</div></div>
            <div><div className="text-xs text-gray-steel mb-1">ناموجود</div><div className="text-lg font-bold text-red-400">{fmt(inventory.out_of_stock)}</div><div className="text-[10px] text-gray-steel">محصول</div></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block"></span>دریافت و پرداخت
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">طلب از مشتریان</div><div className="text-lg font-bold text-blue-400">{fmt(bs?.assets?.receivable)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">بدهی به تامین‌کنندگان</div><div className="text-lg font-bold text-red-400">{fmt(bs?.liabilities?.payable_irr)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">موجودی بانک</div><div className="text-lg font-bold text-green-400">{fmt(bs?.assets?.cash_irr)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs text-gray-steel mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand inline-block"></span>تراز کلی
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><div className="text-xs text-gray-steel mb-1">سود ناخالص</div><div className={`text-lg font-bold ${(bs?.profit?.gross_profit||0)>=0?'text-green-400':'text-red-400'}`}>{fmt(bs?.profit?.gross_profit)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">ارزش موجودی کالا</div><div className="text-lg font-bold text-white">{fmt(bs?.assets?.stock_value)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
            <div><div className="text-xs text-gray-steel mb-1">خالص دارایی</div><div className={`text-lg font-bold ${(bs?.equity||0)>=0?'text-green-400':'text-red-400'}`}>{fmt(bs?.equity)}</div><div className="text-[10px] text-gray-steel">تومان</div></div>
          </div>
        </div>
      </div>

      <div className="card p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-sm text-white">فروش ۶ ماه اخیر</h2>
          <span className="text-xs text-gray-steel">تومان</span>
        </div>
        <div className="flex items-end gap-3 h-32">
          {monthly_sales.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className="text-[10px] text-gray-steel">{d.count > 0 ? d.count : ''}</div>
              <div className="w-full rounded-t-lg transition-all duration-500"
                style={{ height: Math.max((d.total/maxSale)*90, d.total>0?4:0), background: i===monthly_sales.length-1?'#0066FF':'#0066FF33', minHeight: d.total>0?4:0 }} />
              <div className="text-[10px] text-gray-steel">{d.month}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <h2 className="font-semibold text-sm text-white mb-4">آخرین سفارشات</h2>
        <div className="space-y-0">
          {last_orders.map((o, i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-brand">{o.order_number}</span>
                <span className="text-xs text-gray-steel">{o.user}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ color: STATUS_COLOR[o.status], background: STATUS_COLOR[o.status]+'20' }}>
                  {STATUS_FA[o.status] || o.status}
                </span>
                <span className="text-xs font-bold text-white">{fmt(o.amount)} ت</span>
                <span className="text-[10px] text-gray-steel" dir="ltr">{o.created_at}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
