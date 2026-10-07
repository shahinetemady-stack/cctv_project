import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts'
import {
  TrendingUp, ShoppingBag, Users, Package, Wallet,
  ArrowUpRight, ArrowDownRight, Boxes,
} from 'lucide-react'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import { formatDate } from '../../utils/date'
import AccountingChatBox from '../../components/admin/AccountingChatBox'

const STATUS_FA = {
  pending: 'در انتظار', confirmed: 'تأیید شده',
  awaiting_payment: 'در انتظار پرداخت', paid: 'پرداخت شده',
  ready_to_ship: 'آماده ارسال', shipped: 'ارسال شده', cancelled: 'لغو شده',
  draft: 'پیش‌نویس',
}
const STATUS_COLOR = {
  pending: '#FBBF24', confirmed: '#60A5FA', awaiting_payment: '#8B5CF6',
  paid: '#34D399', ready_to_ship: '#22D3EE', shipped: '#0EA5E9', cancelled: '#F87171',
  draft: '#71717A',
}
const PALETTE = ['#FBC02D', '#60A5FA', '#34D399', '#FBBF24', '#8B5CF6', '#F87171']
const AXIS = { fill: '#7C8DA6', fontSize: 11 }
const TOOLTIP_STYLE = {
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border-strong)',
  borderRadius: 12, fontSize: 12, direction: 'rtl', textAlign: 'right',
}

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function compact(n) {
  n = Number(n || 0)
  if (n >= 1e9) return `${(n / 1e9).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} میلیارد`
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} میلیون`
  if (n >= 1e3) return `${(n / 1e3).toLocaleString('fa-IR', { maximumFractionDigits: 0 })} هزار`
  return fmt(n)
}

// ─── کارت KPI ─────────────────────────────────────────────────
function Kpi({ icon: Icon, label, value, unit, sub, delta, color = '#FBC02D' }) {
  return (
    <div className="card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-steel">{label}</span>
        <span className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: color + '1A', color }}>
          <Icon size={16} />
        </span>
      </div>
      <div className="flex items-end gap-1.5">
        <span className="text-xl font-extrabold text-white leading-none">{fmt(value)}</span>
        {unit && <span className="text-[10px] text-gray-steel mb-0.5">{unit}</span>}
      </div>
      <div className="flex items-center gap-2 text-[10px]">
        {delta != null && (
          <span className={`inline-flex items-center gap-0.5 font-bold ${delta >= 0 ? 'text-alert-green' : 'text-alert-red'}`}>
            {delta >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
            {fmt(Math.abs(delta))}٪
          </span>
        )}
        {sub && <span className="text-gray-steel">{sub}</span>}
      </div>
    </div>
  )
}

// ─── قاب کارت نمودار ──────────────────────────────────────────
function ChartCard({ title, sub, children, className = '', height = 220 }) {
  return (
    <div className={`card p-5 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm text-white">{title}</h3>
        {sub && <span className="text-[10px] text-gray-steel">{sub}</span>}
      </div>
      <div dir="ltr" style={{ height }}>
        {children}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
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

  if (isError) return (
    <div className="container-main py-20 text-center text-gray-steel">
      خطا در بارگذاری — با حساب ادمین وارد شوید
    </div>
  )

  const {
    sales = {}, orders = {}, users = {}, inventory = {}, last_orders = [],
    daily_sales = [], prev_month_sales = 0,
    orders_by_status = [], top_products = [], sales_by_category = [],
    month_label = '',
  } = data || {}

  // برچسب شمسی برای محور روزها — مقدار ISO خام در day باقی می‌ماند
  const dailyChart = daily_sales.map(d => ({ ...d, label: formatDate(d.day, { short: true }) }))

  const momDelta = prev_month_sales > 0
    ? Math.round(((sales.month - prev_month_sales) / prev_month_sales) * 100)
    : null
  const totalOrders = orders_by_status.reduce((a, b) => a + b.count, 0)

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">داشبورد مدیریت</h1>
      </div>

      {/* ─── هشدار انقضای سرویس‌ها (دامنه/سرور/…) — فقط سوپریوزر ─── */}
      {(data?.expiring_services || []).length > 0 && (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 p-4">
          <div className="flex items-center gap-2 mb-2 text-red-400 font-semibold text-sm">
            ⚠️ هشدار انقضای سرویس
          </div>
          <div className="space-y-1">
            {data.expiring_services.map(s => (
              <div key={s.id} className="text-xs text-red-300 flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-white">{s.name}</span>
                <span className="text-gray-steel">({s.category_display}{s.provider ? ` — ${s.provider}` : ''})</span>
                <span>
                  {s.days_left < 0
                    ? `${Number(-s.days_left).toLocaleString('fa-IR')} روز پیش منقضی شده!`
                    : `${Number(s.days_left).toLocaleString('fa-IR')} روز مانده`}
                </span>
                <span className="text-gray-steel">{formatDate(s.expire_date)}</span>
                {s.auto_renew && <span className="text-sky-400">(تمدید خودکار فعال است)</span>}
              </div>
            ))}
          </div>
          <Link to="/admin/services" className="inline-block mt-2 text-xs text-brand hover:text-brand/80">
            مدیریت سرویس‌ها ←
          </Link>
        </div>
      )}

      {/* ─── راهنمای هوشمند حسابداری ────────────────────────── */}
      <div className="mb-4">
        <AccountingChatBox />
      </div>

      {/* ─── KPI ها ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <Kpi icon={TrendingUp} label="فروش امروز" value={sales.today} unit="ریال"
          sub={`هفته: ${compact(sales.week)}`} color="#FBC02D" />
        <Kpi icon={Wallet} label={month_label ? `فروش ${month_label}` : 'فروش این ماه'} value={sales.month} unit="ریال"
          delta={momDelta} sub={momDelta == null ? '—' : 'نسبت به ماه قبل'} color="#34D399" />
        <Kpi icon={ShoppingBag} label="سفارشات امروز" value={orders.today} unit="سفارش"
          sub={`در انتظار: ${fmt(orders.pending)} · پرداخت: ${fmt(orders.awaiting_payment)}`} color="#60A5FA" />
        <Kpi icon={Users} label="کاربران جدید امروز" value={users.new_today} unit="کاربر"
          sub={`درخواست همکار: ${fmt(users.partner_requests)}`} color="#8B5CF6" />
      </div>

      {/* ─── روند فروش + وضعیت سفارش‌ها ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <ChartCard title={month_label ? `روند فروش ${month_label}` : 'روند فروش ماه جاری'} sub="ریال" className="lg:col-span-2" height={240}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailyChart} margin={{ top: 5, right: 8, left: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="salesGold" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FBC02D" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#FBC02D" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(128,128,128,0.14)" vertical={false} />
              <XAxis dataKey="label" reversed tick={AXIS} axisLine={false} tickLine={false} dy={6} interval={4} />
              <YAxis orientation="right" width={56} tick={{ ...AXIS, fontSize: 10 }} axisLine={false} tickLine={false}
                tickFormatter={compact} />
              <Tooltip contentStyle={TOOLTIP_STYLE}
                formatter={(v) => [`${fmt(v)} ریال`, 'فروش']} labelFormatter={(l) => `روز ${l}`} />
              <Area type="monotone" dataKey="total" stroke="#FBC02D" strokeWidth={2} fill="url(#salesGold)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="وضعیت سفارش‌ها" sub={`مجموع: ${fmt(totalOrders)}`} height={240}>
          {totalOrders === 0 ? (
            <div className="h-full flex items-center justify-center text-gray-steel text-xs">سفارشی ثبت نشده</div>
          ) : (
            <div className="relative h-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={orders_by_status} dataKey="count" nameKey="status"
                    innerRadius="58%" outerRadius="85%" paddingAngle={3} strokeWidth={0} isAnimationActive={false}>
                    {orders_by_status.map(s => (
                      <Cell key={s.status} fill={STATUS_COLOR[s.status] || '#71717A'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE}
                    formatter={(v, name) => [`${fmt(v)} سفارش`, STATUS_FA[name] || name]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-extrabold text-white">{fmt(totalOrders)}</span>
                <span className="text-[10px] text-gray-steel">سفارش</span>
              </div>
            </div>
          )}
          <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 mt-2" dir="rtl">
            {orders_by_status.map(s => (
              <span key={s.status} className="inline-flex items-center gap-1 text-[10px] text-gray-steel">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: STATUS_COLOR[s.status] || '#71717A' }} />
                {STATUS_FA[s.status] || s.status} ({fmt(s.count)})
              </span>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* ─── فروش دسته‌ای + محصولات برتر ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard title="فروش بر اساس دسته‌بندی" sub="ریال" height={230}>
          {sales_by_category.length === 0 ? (
            <div className="h-full flex items-center justify-center text-gray-steel text-xs">داده‌ای نیست</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sales_by_category} margin={{ top: 5, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid stroke="rgba(128,128,128,0.14)" vertical={false} />
                <XAxis dataKey="name" reversed tick={{ ...AXIS, fontSize: 10 }} axisLine={false} tickLine={false} dy={6} />
                <YAxis orientation="right" width={56} tick={{ ...AXIS, fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={compact} />
                <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(251,192,45,0.06)' }}
                  formatter={(v) => [`${fmt(v)} ریال`, 'فروش']} />
                <Bar dataKey="total" radius={[6, 6, 0, 0]} isAnimationActive={false}>
                  {sales_by_category.map((c, i) => (
                    <Cell key={c.name} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="۵ محصول برتر بر اساس درآمد" sub="ریال" height={230}>
          {top_products.length === 0 ? (
            <div className="h-full flex items-center justify-center text-gray-steel text-xs">داده‌ای نیست</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top_products} layout="vertical" margin={{ top: 0, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid stroke="rgba(128,128,128,0.14)" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" orientation="right" width={150}
                  tick={{ ...AXIS, fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={(n) => n.length > 22 ? n.slice(0, 22) + '…' : n} />
                <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(251,192,45,0.06)' }}
                  formatter={(v, name, item) => [`${fmt(v)} ریال (${fmt(item.payload.qty)} عدد)`, 'درآمد']} />
                <Bar dataKey="revenue" radius={[0, 6, 6, 0]} fill="#FBC02D" barSize={18} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* ─── انبار + آخرین سفارشات ──────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="سلامت انبار" height={210}>
          <div className="h-full flex flex-col justify-center gap-3" dir="rtl">
            <div className="flex items-center gap-3">
              <span className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: '#FBBF241A', color: '#FBBF24' }}>
                <Boxes size={17} />
              </span>
              <div className="flex-1">
                <div className="text-[11px] text-gray-steel">موجودی کم (≤ ۵)</div>
                <div className="text-lg font-extrabold text-white">{fmt(inventory.low_stock)} <span className="text-[10px] font-normal text-gray-steel">محصول</span></div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: '#F871711A', color: '#F87171' }}>
                <Package size={17} />
              </span>
              <div className="flex-1">
                <div className="text-[11px] text-gray-steel">ناموجود</div>
                <div className="text-lg font-extrabold text-white">{fmt(inventory.out_of_stock)} <span className="text-[10px] font-normal text-gray-steel">محصول</span></div>
              </div>
            </div>
            <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[11px]">
              <span className="text-gray-steel">ارزش موجودی کالا</span>
              <span className="font-bold text-gold">{fmt(bs?.assets?.stock_value)} ریال</span>
            </div>
          </div>
        </ChartCard>

        <ChartCard title="آخرین سفارشات" height={210}>
          <div className="h-full overflow-y-auto space-y-0 -mx-2 px-2" dir="rtl">
            {last_orders.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-steel text-xs">سفارشی نیست</div>
            ) : last_orders.map((o, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <div className="flex flex-col">
                  <span className="text-[11px] text-gold">{o.order_number}</span>
                  <span className="text-[10px] text-gray-steel" dir="ltr">{o.user}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 rounded-full"
                    style={{ color: STATUS_COLOR[o.status], background: (STATUS_COLOR[o.status] || '#71717A') + '20' }}>
                    {STATUS_FA[o.status] || o.status}
                  </span>
                  <span className="text-[11px] font-bold text-white whitespace-nowrap">{fmt(o.amount)} ریال</span>
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
