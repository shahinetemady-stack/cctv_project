import { useState, useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Search } from 'lucide-react'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import AmountInput from '../../components/ui/AmountInput'
import usePermissions from '../../hooks/usePermissions'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// نرمال‌سازی برای جستجوی هوشمند — ارقام فارسی/عربی → لاتین، حروف عربی → فارسی
const normalize = (s) => String(s ?? '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
  .replace(/ك/g, 'ک').replace(/ي/g, 'ی')
  .toLowerCase()

// ناوبری کیبوردی بین اینپوت‌ها — Enter/↓ به آیتم بعدی، ↑ به قبلی (ذخیره با blur)
// هر اینپوت data-navgroup (و برای جدول دسته‌ها data-navcol = همان ستون) دارد
function handleNavKey(e) {
  if (!['Enter', 'ArrowDown', 'ArrowUp'].includes(e.key)) return
  e.preventDefault()
  const { navgroup, navcol } = e.target.dataset
  if (!navgroup) return
  const sel = `input[data-navgroup="${navgroup}"]` + (navcol ? `[data-navcol="${navcol}"]` : '')
  const inputs = [...document.querySelectorAll(sel)]
  const idx = inputs.indexOf(e.target)
  const next = inputs[idx + (e.key === 'ArrowUp' ? -1 : 1)]
  e.target.blur()
  if (next) { next.focus(); next.select() }
}

const CAT_FIELDS = ['shipping_cost_cny', 'clearance_cost_cny']

export default function PricingPage() {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [showCats, setShowCats] = useState(false)
  const [rate, setRate] = useState('')
  const [cats, setCats] = useState({})   // id → {shipping_cost_cny, clearance_cost_cny, profit_*}
  const [vars, setVars] = useState({})   // id → {purchase_price_cny}
  const [saving, setSaving] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['pricing'],
    queryFn: () => api.get('/catalog/pricing/').then(r => r.data),
  })
  const profitTypes = data?.profit_types || []

  // پر کردن state محلی از داده سرور
  useEffect(() => {
    if (!data) return
    setRate(String(data.rate_cny_to_irt || ''))
    setCats(Object.fromEntries(data.categories.map(c => [c.id, {
      shipping_cost_cny: String(c.shipping_cost_cny || 0),
      clearance_cost_cny: String(c.clearance_cost_cny || 0),
      ...Object.fromEntries(data.profit_types.map(t => [t.key, String(c[t.key] || 0)])),
    }])))
    const v = {}
    for (const p of data.products) {
      for (const variant of p.variants) {
        v[variant.id] = {
          purchase_price_cny: String(variant.purchase_price_cny || 0),
          discount_percent: String(variant.discount_percent || 0),
          month2_unavailable: !!variant.month2_unavailable,
        }
      }
    }
    setVars(v)
  }, [data])

  // مقدار مؤثر هر فیلد دسته — صفر یعنی ارث از والد
  const effective = useMemo(() => {
    const parentOf = Object.fromEntries((data?.categories || []).map(c => [c.id, c.parent]))
    const fields = [...CAT_FIELDS, ...profitTypes.map(t => t.key)]
    return (catId) => {
      const own = cats[catId] || {}
      const parent = cats[parentOf[catId]] || {}
      return Object.fromEntries(fields.map(f => [f, Number(own[f] || 0) || Number(parent[f] || 0)]))
    }
  }, [cats, data, profitTypes])

  // درخت دسته‌ها: والدها به ترتیب، زیردسته‌ها بلافاصله بعد از والد
  const tree = useMemo(() => {
    const list = data?.categories || []
    const roots = list.filter(c => !c.parent)
    const childrenOf = {}
    for (const c of list) if (c.parent) (childrenOf[c.parent] ||= []).push(c)
    const out = []
    for (const r of roots) {
      out.push({ ...r, depth: 0, hasChildren: !!(childrenOf[r.id] || []).length })
      for (const ch of (childrenOf[r.id] || [])) out.push({ ...ch, depth: 1 })
    }
    return out
  }, [data])

  const saveRate = async () => {
    setSaving('rate')
    try {
      await api.put('/catalog/exchange-rate/', { rate_cny_to_irt: Number(rate) || 0 })
      toast.success('نرخ یوان ذخیره شد')
      qc.invalidateQueries(['exchange-rate'])
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ذخیره نرخ')
    } finally { setSaving(null) }
  }

  const saveCat = async (id) => {
    setSaving(`cat-${id}`)
    try {
      const payload = {}
      for (const f of CAT_FIELDS) payload[f] = Number(cats[id]?.[f]) || 0
      for (const t of profitTypes) payload[t.key] = Number(cats[id]?.[t.key]) || 0
      await api.patch(`/catalog/pricing/categories/${id}/`, payload)
      toast.success('تنظیمات دسته ذخیره شد')
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ذخیره')
    } finally { setSaving(null) }
  }

  const saveVar = async (id) => {
    setSaving(`var-${id}`)
    try {
      const d = Math.min(100, Math.max(0, parseFloat(vars[id]?.discount_percent) || 0))
      await api.patch(`/catalog/pricing/variants/${id}/`, {
        purchase_price_cny: Number(vars[id]?.purchase_price_cny) || 0,
        discount_percent: d,
      })
      if (String(d) !== vars[id]?.discount_percent)
        setVars(s => ({ ...s, [id]: { ...s[id], discount_percent: String(d) } }))
      toast.success('قیمت یوان ذخیره شد')
      qc.invalidateQueries(['admin-products'])
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ذخیره')
    } finally { setSaving(null) }
  }

  // علامت‌گذاری «فروش دوماهه ندارد» برای یک واریانت
  const toggleMonth2 = async (id) => {
    const next = !vars[id]?.month2_unavailable
    setSaving(`m2-${id}`)
    try {
      await api.patch(`/catalog/pricing/variants/${id}/`, { month2_unavailable: next })
      setVars(s => ({ ...s, [id]: { ...s[id], month2_unavailable: next } }))
      toast.success(next ? 'ستون دوماهه «ندارد» شد' : 'فروش دوماهه فعال شد')
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ذخیره')
    } finally { setSaving(null) }
  }

  if (isLoading || !data) return <PageLoader />

  const rateIrt = Number(rate || 0)   // ریال
  const nq = normalize(q.trim())
  const products = data.products.filter(p =>
    !nq || normalize(p.name).includes(nq) || p.variants.some(v => normalize(v.sku).includes(nq))
  )

  const inputCls = 'input-dark text-xs w-16 text-center'
  const th = { padding: '8px 8px', textAlign: 'center', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 11, whiteSpace: 'nowrap' }
  const td = { padding: '6px 8px', borderBottom: '0.5px solid var(--color-border)' }

  return (
    <div className="container-main py-8 max-w-7xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">لیست قیمت</h1>

      {/* نرخ یوان روز — فقط با پرمیشن pricing_rate_view */}
      {can('pricing_rate_view') && (
      <div className="card p-4 mb-4 flex items-center gap-4 flex-wrap">
        <div className="text-sm font-semibold text-white">💱 نرخ یوان روز (ریال)</div>
        {can('exchange_rate_edit') ? (
          <div className="flex items-center gap-2">
            <AmountInput value={rate} onChange={e => setRate(e.target.value)} className="input-dark text-xs w-36" />
            <button onClick={saveRate} disabled={saving === 'rate'} className="btn-primary text-xs px-4 py-1.5 disabled:opacity-50">
              {saving === 'rate' ? '...' : 'ذخیره نرخ'}
            </button>
          </div>
        ) : (
          <div className="text-sm font-mono text-gold">{fmt(rate)}</div>
        )}
        <div className="text-[10px] text-gray-steel mr-auto">
          فرمول: (قیمت یوان + حمل + ترخیص) × نرخ یوان × (۱ + درصد سود) — رند به بالای ده‌هزار ریال، سپس تخفیف واریانت و رند مجدد
        </div>
      </div>
      )}

      {/* جستجوی سریع محصول */}
      <div className="card p-4 mb-6 flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={15} className="absolute top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" style={{ right: 12 }} />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="جستجوی محصول یا SKU برای دیدن قیمت..."
            className="input-dark text-sm w-full" style={{ paddingRight: '2.5rem' }} />
        </div>
        {q.trim() && (
          <span className="text-[11px] text-gray-steel">{products.length.toLocaleString('fa-IR')} محصول</span>
        )}
      </div>

      {/* هزینه‌ها و درصد سود دسته‌ها (درختی) — فقط با پرمیشن pricing_costs_view */}
      {can('pricing_costs_view') && (
      <div className="card p-4 mb-6">
        <button onClick={() => setShowCats(s => !s)} className="w-full flex items-center justify-between">
          <div className="text-sm font-semibold text-white">🚛 هزینه و سود هر دسته</div>
          <span className="text-xs text-gray-steel">
            {showCats ? '▲ بستن' : `▼ باز کردن (${tree.length.toLocaleString('fa-IR')} دسته)`}
          </span>
        </button>
        {showCats && (
        <>
        <div className="text-[10px] text-gray-steel mb-3 mt-2">
          حمل و ترخیص به یوان، سودها به درصد. مقادیر فقط روی زیردسته‌ها تعریف می‌شود و ذخیره با خروج از فیلد انجام می‌شود.
        </div>
        <div className="overflow-x-auto">
          <table style={{ borderCollapse: 'collapse', fontSize: 12, minWidth: '100%' }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid var(--color-border-strong)' }}>
                <th style={{ ...th, textAlign: 'right' }}>دسته</th>
                <th style={th}>حمل (یوان)</th>
                <th style={th}>ترخیص (یوان)</th>
                {profitTypes.map(t => <th key={t.key} style={th}>{t.label} ٪</th>)}
              </tr>
            </thead>
            <tbody>
              {tree.map(c => (
                <tr key={c.id} style={{ borderBottom: '0.5px solid var(--color-border)' }}>
                  <td style={{ ...td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <span className={c.depth ? 'text-gray-steel text-[11px]' : 'text-white font-semibold text-xs'}
                      style={{ paddingRight: c.depth ? 16 : 0 }}>
                      {c.depth ? '↳ ' : ''}{c.name}
                    </span>
                  </td>
                  {/* دسته اصلیِ دارای زیردسته — بدون ورودی؛ مقادیر فقط روی زیردسته‌ها */}
                  {c.depth === 0 && c.hasChildren ? (
                    <td colSpan={2 + profitTypes.length} style={{ ...td, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 10 }}>
                      مقادیر روی زیردسته‌ها تعریف می‌شود
                    </td>
                  ) : (
                    <>
                      {CAT_FIELDS.map(f => (
                        <td key={f} style={{ ...td, textAlign: 'center' }}>
                          <AmountInput value={cats[c.id]?.[f] || ''}
                            onChange={e => setCats(s => ({ ...s, [c.id]: { ...s[c.id], [f]: e.target.value } }))}
                            onBlur={() => saveCat(c.id)} placeholder="۰" className={inputCls}
                            data-navgroup="cats" data-navcol={f} onKeyDown={handleNavKey} />
                        </td>
                      ))}
                      {profitTypes.map(t => (
                        <td key={t.key} style={{ ...td, textAlign: 'center' }}>
                          <AmountInput value={cats[c.id]?.[t.key] || ''}
                            onChange={e => setCats(s => ({ ...s, [c.id]: { ...s[c.id], [t.key]: e.target.value } }))}
                            onBlur={() => saveCat(c.id)} placeholder="٪" className="input-dark text-xs w-14 text-center"
                            data-navgroup="cats" data-navcol={t.key} onKeyDown={handleNavKey} />
                        </td>
                      ))}
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
        )}
      </div>
      )}

      {/* جدول قیمت‌گذاری محصولات */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="text-sm font-semibold text-white">📦 قیمت‌گذاری محصولات</div>
        <div className="text-[10px] text-gray-steel">💡 با Enter یا ↑↓ بین محصولات جابه‌جا شوید — ذخیره خودکار است</div>
      </div>

      <div className="card overflow-x-auto">
        <table style={{ borderCollapse: 'collapse', fontSize: 12, minWidth: '100%' }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid var(--color-border-strong)' }}>
              <th style={{ ...th, textAlign: 'right', position: 'sticky', right: 0, background: 'var(--color-bg-elevated)', zIndex: 2 }}>محصول</th>
              <th style={th}>قیمت یوان</th>
              <th style={th}>تخفیف ٪</th>
              <th style={th}>موجودی</th>
              {profitTypes.map(t => <th key={t.key} style={th}>{t.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {products.map(p => p.variants.map((v, vi) => {
              const eff = effective(p.category_id)
              const costIrt = (Number(vars[v.id]?.purchase_price_cny || 0)
                + eff.shipping_cost_cny + eff.clearance_cost_cny) * rateIrt
              const disc = 1 - (parseFloat(vars[v.id]?.discount_percent) || 0) / 100
              // دقیقاً همان فرمول بک‌اند (pricing.py): اول قیمت پایه رند به بالای ده‌هزار،
              // بعد تخفیف واریانت و رند مجدد — وگرنه با قیمت نمایشی سایت اختلاف می‌خورد
              const priceFor = (key) => {
                const base = Math.ceil(costIrt * (1 + (eff[key] || 0) / 100) / 10000) * 10000
                return Math.ceil(base * disc / 10000) * 10000
              }
              return (
                <tr key={v.id} style={{ background: vi % 2 ? 'var(--color-brand-softer)' : 'transparent' }}>
                  <td style={{ ...td, textAlign: 'right', minWidth: 200, position: 'sticky', right: 0, zIndex: 1, background: vi % 2 ? 'var(--color-brand-softer)' : 'var(--color-bg-elevated)' }}>
                    <div className="font-semibold text-white text-xs">{p.name}{v.name_suffix ? ` — ${v.name_suffix}` : ''}</div>
                    <div className="text-[10px] text-gray-steel" dir="ltr">{v.sku} · {p.category_name}</div>
                  </td>
                  <td style={{ ...td, textAlign: 'center' }}>
                    <AmountInput value={vars[v.id]?.purchase_price_cny || ''}
                      onChange={e => setVars(s => ({ ...s, [v.id]: { ...s[v.id], purchase_price_cny: e.target.value } }))}
                      onBlur={() => saveVar(v.id)} className="input-dark text-xs text-center"
                      style={{ width: 40, padding: '2px 3px' }}
                      data-navgroup="products" onKeyDown={handleNavKey} />
                  </td>
                  <td style={{ ...td, textAlign: 'center' }}>
                    <AmountInput value={vars[v.id]?.discount_percent || ''}
                      onChange={e => setVars(s => ({ ...s, [v.id]: { ...s[v.id], discount_percent: e.target.value } }))}
                      onBlur={() => saveVar(v.id)} placeholder="۰" className="input-dark text-xs text-center"
                      style={{ width: 32, padding: '2px 3px' }}
                      data-navgroup="products" onKeyDown={handleNavKey} />
                  </td>
                  <td style={{ ...td, textAlign: 'center' }}>
                    <span className={v.available_stock > 0 ? 'badge-green' : 'badge-red'}>
                      {Number(v.available_stock || 0).toLocaleString('fa-IR')}
                    </span>
                  </td>
                  {profitTypes.map(t => {
                    // ستون دوماهه — قابل علامت‌گذاری «ندارد» برای هر واریانت
                    if (t.key === 'profit_month2_percent') {
                      const off = vars[v.id]?.month2_unavailable
                      return (
                        <td key={t.key} style={{ ...td, textAlign: 'center', whiteSpace: 'nowrap' }}>
                          {off ? (
                            <button onClick={() => toggleMonth2(v.id)} disabled={saving === `m2-${v.id}`}
                              title="برای فعال‌سازی مجدد کلیک کنید"
                              className="text-gray-steel text-sm font-bold line-through decoration-red-400/70">
                              ندارد
                            </button>
                          ) : (
                            <div className="flex flex-col items-center">
                              <span className="text-gold text-sm font-bold">
                                {fmt(priceFor(t.key))}
                              </span>
                              <button onClick={() => toggleMonth2(v.id)} disabled={saving === `m2-${v.id}`}
                                className="text-[9px] text-[var(--color-text-muted)] hover:text-red-400 transition-colors">
                                ✕ ندارد
                              </button>
                            </div>
                          )}
                        </td>
                      )
                    }
                    return (
                      <td key={t.key} style={{ ...td, textAlign: 'center', fontWeight: 700, whiteSpace: 'nowrap' }}
                        className="text-gold text-sm">
                        {fmt(priceFor(t.key))}
                      </td>
                    )
                  })}
                </tr>
              )
            }))}
          </tbody>
        </table>
        {products.length === 0 && (
          <div className="text-center py-12 text-gray-steel text-sm">محصولی یافت نشد</div>
        )}
      </div>
    </div>
  )
}
