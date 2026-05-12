import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'

const MOVEMENT_COLORS = {
  'خرید': '#00C896', 'فروش': '#FF3B3B',
  'انتقال ورودی': '#0066FF', 'انتقال خروجی': '#FF9500',
  'تعدیل موجودی': '#8B5CF6', 'مرجوعی': '#FF6B6B',
}

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function KardexPage() {
  const [selectedVariant, setSelectedVariant] = useState('')
  const [selectedWarehouse, setSelectedWarehouse] = useState('')
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)

  const { data: productsData } = useQuery({
    queryKey: ['products-list'],
    queryFn: () => api.get('/catalog/products/', { params: { page_size: 200 } }).then(r => r.data),
  })

  const { data: warehousesData } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => api.get('/inventory/warehouses/').then(r => r.data),
  })

  const { data: kardex, isLoading: loadingKardex } = useQuery({
    queryKey: ['kardex', selectedVariant, selectedWarehouse],
    queryFn: () => api.get(`/inventory/kardex/${selectedVariant}/`, {
      params: selectedWarehouse ? { warehouse: selectedWarehouse } : {}
    }).then(r => r.data),
    enabled: !!selectedVariant,
  })

  const { data: stockData } = useQuery({
    queryKey: ['admin-stock', selectedVariant],
    queryFn: () => api.get(`/inventory/stock/${selectedVariant}/`).then(r => r.data),
    enabled: !!selectedVariant,
  })

  const products = productsData?.results || productsData || []
  const warehouses = warehousesData || []

  // همه variant ها با اطلاعات محصول
  const allVariants = useMemo(() => {
    const result = []
    products.forEach(p => {
      if (p.variants?.length) {
        p.variants.forEach(v => {
          result.push({ id: v.id, sku: v.sku, productName: p.name, category: p.category_name || '' })
        })
      }
    })
    return result
  }, [products])

  // فیلتر بر اساس جستجو
  const filtered = useMemo(() => {
    if (!search) return allVariants.slice(0, 20)
    const q = search.toLowerCase()
    return allVariants.filter(v =>
      v.productName.includes(search) || v.sku.toLowerCase().includes(q) || v.category.includes(search)
    ).slice(0, 20)
  }, [allVariants, search])

  const selectedInfo = allVariants.find(v => String(v.id) === String(selectedVariant))

  const movements = kardex || []
  const totalIn = movements.filter(m => m.quantity > 0).reduce((s, m) => s + m.quantity, 0)
  const totalOut = movements.filter(m => m.quantity < 0).reduce((s, m) => s + Math.abs(m.quantity), 0)

  return (
    <div className="container-main py-8 max-w-5xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">کاردکس موجودی</h1>

      {/* فیلترها */}
      <div className="card p-5 mb-6">
        <div className="grid grid-cols-2 gap-4">

          {/* جستجوی محصول با dropdown */}
          <div className="relative">
            <label className="label text-xs mb-1 block">جستجو و انتخاب محصول</label>
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setShowDropdown(true) }}
              onFocus={() => setShowDropdown(true)}
              placeholder="نام محصول یا کد SKU..."
              className="input text-sm"
            />
            {showDropdown && filtered.length > 0 && (
              <div className="absolute z-50 top-full right-0 left-0 mt-1 bg-navy border border-white/10 rounded-xl shadow-xl overflow-hidden max-h-64 overflow-y-auto">
                {filtered.map(v => (
                  <button key={v.id}
                    className="w-full text-right px-4 py-3 hover:bg-white/5 transition-colors border-b border-white/5 last:border-0"
                    onClick={() => {
                      setSelectedVariant(String(v.id))
                      setSearch(v.productName)
                      setShowDropdown(false)
                    }}>
                    <div className="text-sm text-white">{v.productName}</div>
                    <div className="text-xs text-gray-steel mt-0.5">SKU: {v.sku} | {v.category}</div>
                  </button>
                ))}
              </div>
            )}
            {selectedInfo && (
              <div className="text-xs text-green-400 mt-1">
                ✓ انتخاب شده: {selectedInfo.productName} [{selectedInfo.sku}]
              </div>
            )}
          </div>

          {/* فیلتر انبار */}
          <div>
            <label className="label text-xs mb-1 block">فیلتر انبار</label>
            <select value={selectedWarehouse} onChange={e => setSelectedWarehouse(e.target.value)}
              className="input text-sm">
              <option value="">همه انبارها</option>
              {warehouses.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            {selectedVariant && (
              <button
                onClick={() => { setSelectedVariant(''); setSearch(''); setSelectedWarehouse('') }}
                className="text-xs text-red-400 hover:text-red-300 mt-1 block">
                × پاک کردن
              </button>
            )}
          </div>
        </div>
      </div>

      {selectedVariant ? (
        <>
          {/* موجودی هر انبار */}
          <div className="card p-5 mb-6">
            <h2 className="font-semibold text-sm text-white mb-4">موجودی در انبارها</h2>
            <div className="grid grid-cols-5 gap-3">
              {warehouses.map(w => {
                const stock = stockData?.stocks?.find(s => s.warehouse === w.name)
                const qty = stock?.quantity || 0
                return (
                  <div key={w.id}
                    onClick={() => setSelectedWarehouse(String(w.id) === selectedWarehouse ? '' : String(w.id))}
                    className={`text-center p-3 rounded-xl cursor-pointer transition-all
                      ${String(w.id) === selectedWarehouse ? 'bg-brand/20 border border-brand/40' : 'bg-white/5 hover:bg-white/10'}`}>
                    <div className="text-xs text-gray-steel mb-1">{w.name}</div>
                    <div className={`text-xl font-bold ${qty === 0 ? 'text-red-400' : qty <= 5 ? 'text-orange-400' : 'text-green-400'}`}>
                      {fmt(qty)}
                    </div>
                    <div className="text-[10px] text-gray-steel">عدد</div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* خلاصه آمار */}
          {movements.length > 0 && (
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="card p-4 text-center">
                <div className="text-xs text-gray-steel mb-1">کل ورودی</div>
                <div className="text-xl font-bold text-green-400">+{fmt(totalIn)}</div>
                <div className="text-[10px] text-gray-steel">عدد</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-xs text-gray-steel mb-1">کل خروجی</div>
                <div className="text-xl font-bold text-red-400">-{fmt(totalOut)}</div>
                <div className="text-[10px] text-gray-steel">عدد</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-xs text-gray-steel mb-1">تعداد تراکنش</div>
                <div className="text-xl font-bold text-white">{fmt(movements.length)}</div>
                <div className="text-[10px] text-gray-steel">رکورد</div>
              </div>
            </div>
          )}

          {/* جدول کاردکس */}
          <div className="card p-5">
            <h2 className="font-semibold text-sm text-white mb-4">تاریخچه حرکات</h2>
            {loadingKardex ? (
              <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
            ) : movements.length === 0 ? (
              <div className="text-center py-8 text-gray-steel">هنوز حرکتی ثبت نشده</div>
            ) : (
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['تاریخ', 'انبار', 'نوع', 'تعداد', 'موجودی بعد', 'قیمت واحد', 'مرجع'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 500,
                          color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {movements.map((m, i) => (
                      <tr key={i} style={{
                        borderBottom: '0.5px solid rgba(255,255,255,0.05)',
                        background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                      }}>
                        <td style={{ padding: '10px 12px', direction: 'ltr', textAlign: 'right',
                          color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{m.date}</td>
                        <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>{m.warehouse}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{
                            color: MOVEMENT_COLORS[m.type] || '#888',
                            background: (MOVEMENT_COLORS[m.type] || '#888') + '20',
                            padding: '2px 10px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap',
                          }}>{m.type}</span>
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 700, whiteSpace: 'nowrap',
                          color: m.quantity > 0 ? '#00C896' : '#FF3B3B' }}>
                          {m.quantity > 0 ? '+' : ''}{fmt(m.quantity)}
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 500 }}>{fmt(m.balance_after)}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)' }}>
                          {m.unit_price ? fmt(m.unit_price) + ' ت' : '—'}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>
                          {m.reference || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-4">📊</div>
          <div className="text-gray-steel">نام محصول یا کد SKU را جستجو کنید</div>
        </div>
      )}
    </div>
  )
}
