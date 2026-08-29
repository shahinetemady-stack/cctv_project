import { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'
import { formatDate } from '../../utils/date'
import AmountInput from '../../components/ui/AmountInput'
import { UserStamp } from '../../components/ui'

const MOVEMENT_COLORS = {
  'موجودی اول دوره': '#FBC02D',
  'خرید': '#00C896',
  'فروش': '#FF3B3B',
  'انتقال ورودی': '#0066FF',
  'انتقال خروجی': '#FF9500',
  'تعدیل موجودی': '#8B5CF6',
  'مرجوعی': '#FF6B6B',
}

const MOVEMENT_TYPES = [
  { value: 'opening',      label: 'موجودی اول دوره', sign: '+', color: '#FBC02D' },
  { value: 'adjustment',   label: 'تعدیل موجودی',  sign: '±', color: '#8B5CF6' },
]

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

export default function KardexPage() {
  const queryClient = useQueryClient()
  const searchRef = useRef(null)
  const inputRef = useRef(null)

  const [selectedVariant, setSelectedVariant] = useState('')
  const [selectedWarehouse, setSelectedWarehouse] = useState('')
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 })
  const [showForm, setShowForm] = useState(false)
  const [formMsg, setFormMsg] = useState(null)
  const [adjSign, setAdjSign] = useState('+')

  const [form, setForm] = useState({
    warehouse_id: '', movement_type: 'opening',
    quantity: '', unit_price: '', reference: '', note: '',
  })

  const { data: variantsData, isLoading: loadingVariants } = useQuery({
    queryKey: ['variants-list'],
    queryFn: () => api.get('/catalog/variants/').then(r => r.data),
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
    queryFn: () => api.get(`/inventory/admin-stock/${selectedVariant}/`).then(r => r.data),
    enabled: !!selectedVariant,
  })

  const moveMutation = useMutation({
    mutationFn: (payload) => api.post('/inventory/movements/', payload).then(r => r.data),
    onSuccess: (data) => {
      setFormMsg({ type: 'success', text: data.message || 'موجودی با موفقیت ثبت شد' })
      setForm({ warehouse_id: '', movement_type: 'opening', quantity: '', unit_price: '', reference: '', note: '' })
      setAdjSign('+')
      queryClient.invalidateQueries(['kardex', selectedVariant])
      queryClient.invalidateQueries(['admin-stock', selectedVariant])
      queryClient.invalidateQueries(['variants-list'])
      setTimeout(() => { setFormMsg(null); setShowForm(false) }, 2500)
    },
    onError: (err) => {
      setFormMsg({ type: 'error', text: err.response?.data?.error || 'خطا در ثبت موجودی' })
    },
  })

  const allVariants = Array.isArray(variantsData)
    ? variantsData
    : (variantsData?.results || variantsData?.data || [])
  const warehouses = Array.isArray(warehousesData)
    ? warehousesData
    : (warehousesData?.results || warehousesData?.data || [])

  const filtered = useMemo(() => {
    if (!search) return allVariants.slice(0, 30)
    const q = search.toLowerCase()
    return allVariants.filter(v =>
      (v.product_name || '').toLowerCase().includes(q) ||
      (v.sku || '').toLowerCase().includes(q) ||
      (v.category || '').toLowerCase().includes(q)
    ).slice(0, 30)
  }, [allVariants, search])

  const selectedInfo = allVariants.find(v => String(v.id) === String(selectedVariant))
  const movements = Array.isArray(kardex) ? kardex : (kardex?.results || [])
  const totalIn = movements.filter(m => m.quantity > 0).reduce((s, m) => s + m.quantity, 0)
  const totalOut = movements.filter(m => m.quantity < 0).reduce((s, m) => s + Math.abs(m.quantity), 0)

  // محاسبه موقعیت dropdown با position fixed
  function updateDropdownPos() {
    if (!inputRef.current) return
    const rect = inputRef.current.getBoundingClientRect()
    setDropdownPos({
      top: rect.bottom + 4,
      left: rect.left,
      width: rect.width,
    })
  }

  function openDropdown() {
    updateDropdownPos()
    setShowDropdown(true)
  }

  // بستن dropdown با کلیک بیرون + بازمحاسبه با scroll/resize
  useEffect(() => {
    if (!showDropdown) return

    function handleClickOutside(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        // اگر کلیک روی dropdown هم نباشد، ببند
        const dropdown = document.getElementById('kardex-search-dropdown')
        if (!dropdown || !dropdown.contains(e.target)) {
          setShowDropdown(false)
        }
      }
    }
    function handleReposition() {
      updateDropdownPos()
    }
    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('scroll', handleReposition, true)
    window.addEventListener('resize', handleReposition)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('scroll', handleReposition, true)
      window.removeEventListener('resize', handleReposition)
    }
  }, [showDropdown])

  function handleSubmit() {
    if (!form.warehouse_id) return setFormMsg({ type: 'error', text: 'انبار را انتخاب کنید' })
    if (!form.quantity || Number(form.quantity) <= 0) return setFormMsg({ type: 'error', text: 'تعداد باید بیشتر از صفر باشد' })
    setFormMsg(null)
    const qty = Number(form.quantity)
    moveMutation.mutate({
      variant_id: selectedVariant,
      warehouse_id: form.warehouse_id,
      movement_type: form.movement_type,
      quantity: form.movement_type === 'adjustment' && adjSign === '-' ? -qty : qty,
      unit_price: Number(form.unit_price) || 0,
      reference: form.reference,
      note: form.note,
    })
  }

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">کاردکس موجودی</h1>
        {selectedVariant && (
          <button onClick={() => { setShowForm(true); setFormMsg(null) }}
            className="btn-primary text-sm px-4 py-2">
            + ثبت ورود / خروج موجودی
          </button>
        )}
      </div>

      {/* فیلترها */}
      <div className="card p-5 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div ref={searchRef}>
            <label className="label text-xs mb-1 block">جستجو و انتخاب محصول</label>
            <input
              ref={inputRef}
              value={search}
              onChange={e => { setSearch(e.target.value); openDropdown() }}
              onFocus={openDropdown}
              placeholder={loadingVariants ? 'در حال بارگذاری...' : 'نام محصول یا کد SKU...'}
              className="input text-sm"
              disabled={loadingVariants}
            />
            {selectedInfo && (
              <div className="text-xs text-green-400 mt-1">✓ {selectedInfo.product_name} [{selectedInfo.sku}]</div>
            )}
          </div>

          <div>
            <label className="label text-xs mb-1 block">فیلتر انبار</label>
            <select value={selectedWarehouse} onChange={e => setSelectedWarehouse(e.target.value)} className="input text-sm">
              <option value="">همه انبارها</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
            {selectedVariant && (
              <button onClick={() => { setSelectedVariant(''); setSearch(''); setSelectedWarehouse('') }}
                className="text-xs text-red-400 hover:text-red-300 mt-1 block">
                × پاک کردن
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Dropdown با position fixed — روی همه چیز ظاهر می‌شود */}
      {showDropdown && (
        <div
          id="kardex-search-dropdown"
          style={{
            position: 'fixed',
            top: dropdownPos.top,
            left: dropdownPos.left,
            width: dropdownPos.width,
            zIndex: 99999,
            background: '#0d1117',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 12,
            boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
            maxHeight: 320,
            overflowY: 'auto',
          }}>
          {loadingVariants ? (
            <div style={{ padding: 16, textAlign: 'center', color: '#888', fontSize: 13 }}>
              در حال بارگذاری محصولات...
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 16, textAlign: 'center', color: '#888', fontSize: 13 }}>
              {search ? 'نتیجه‌ای یافت نشد' : 'محصولی موجود نیست'}
            </div>
          ) : (
            filtered.map(v => (
              <button key={v.id}
                style={{
                  width: '100%', textAlign: 'right',
                  padding: '10px 14px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                  display: 'block',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                onClick={() => {
                  setSelectedVariant(String(v.id))
                  setSearch(v.product_name || '')
                  setShowDropdown(false)
                }}>
                <div style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>{v.product_name}</div>
                <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
                  SKU: {v.sku} {v.category ? `| ${v.category}` : ''}
                  <span style={{
                    marginRight: 8,
                    color: (v.stock_quantity || 0) > 0 ? '#00C896' : '#FF3B3B',
                  }}>
                    | موجودی: {fmt(v.stock_quantity)}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      )}

      {/* مودال ثبت موجودی */}
      {showForm && selectedVariant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="card p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-white text-lg">ثبت حرکت موجودی</h2>
              <button onClick={() => { setShowForm(false); setFormMsg(null) }}
                className="text-gray-steel hover:text-white text-2xl leading-none">×</button>
            </div>

            <div className="text-xs text-gray-steel mb-4 bg-white/5 rounded-lg px-3 py-2">
              محصول: <span className="text-white">{selectedInfo?.product_name}</span>
              <span className="mr-3">SKU: {selectedInfo?.sku}</span>
            </div>

            <div className="space-y-4">
              <div>
                <label className="label text-xs mb-1 block">انبار *</label>
                <select value={form.warehouse_id}
                  onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
                  className="input text-sm">
                  <option value="">انتخاب انبار...</option>
                  {warehouses.map(w => {
                    const stock = stockData?.stocks?.find(s => s.warehouse === w.name)
                    return (
                      <option key={w.id} value={w.id}>
                        {w.name} — موجودی: {stock ? fmt(stock.quantity) : '۰'}
                      </option>
                    )
                  })}
                </select>
              </div>

              <div>
                <label className="label text-xs mb-1 block">نوع حرکت *</label>
                <div className="grid grid-cols-3 gap-2">
                  {MOVEMENT_TYPES.map(t => (
                    <button key={t.value}
                      onClick={() => setForm(f => ({ ...f, movement_type: t.value }))}
                      style={{
                        borderColor: form.movement_type === t.value ? t.color : 'transparent',
                        background: form.movement_type === t.value ? t.color + '20' : 'rgba(255,255,255,0.05)',
                      }}
                      className="text-xs py-2 px-2 rounded-lg border-2 transition-all text-right">
                      <span style={{ color: t.color }} className="font-bold ml-1">{t.sign}</span>
                      {t.label}
                    </button>
                  ))}
                </div>
                {form.movement_type === 'adjustment' && (
                  <div className="mt-2">
                    <div className="grid grid-cols-2 gap-2">
                      <button type="button" onClick={() => setAdjSign('+')}
                        className={`text-xs py-2 rounded-lg border-2 transition-all ${adjSign === '+' ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-transparent bg-white/5'}`}>
                        + افزایش (اضافه شمارش)
                      </button>
                      <button type="button" onClick={() => setAdjSign('-')}
                        className={`text-xs py-2 rounded-lg border-2 transition-all ${adjSign === '-' ? 'border-red-500 bg-red-500/10 text-red-400' : 'border-transparent bg-white/5'}`}>
                        − کاهش (کسری شمارش)
                      </button>
                    </div>
                    <p className="text-[10px] text-[var(--color-text-muted)] mt-1.5 leading-relaxed">
                      تعدیل برای اصلاح شمارش است — فقط عدد اختلاف را وارد کنید (مثلاً اگر ۸۷۰ ثبت شده ولی ۹۱۰ شمرده‌اید: افزایش ۴۰).
                    </p>
                  </div>
                )}
                <p className="text-[10px] text-[var(--color-text-muted)] mt-2 leading-relaxed">
                  خرید، فروش و مرجوعی فقط از فاکتورهای مربوط (فاکتور خرید / فروش / مرجوعی) ثبت می‌شوند تا انبار و حسابداری هماهنگ بمانند.
                  برای جابجایی کالا بین انبارها از صفحه «انبارها» → «انتقال کالا» استفاده کنید تا انتقال دوطرفه ثبت شود (هم از مبدأ کم می‌شود، هم به مقصد اضافه).
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label text-xs mb-1 block">تعداد *</label>
                  <input type="number" min="1" value={form.quantity}
                    onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                    placeholder="عدد صحیح"
                    className="input text-sm" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">قیمت واحد (ریال)</label>
                  <AmountInput value={form.unit_price}
                    onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))}
                    placeholder="اختیاری"
                    className="input text-sm" />
                </div>
              </div>

              <div>
                <label className="label text-xs mb-1 block">شماره فاکتور / مرجع</label>
                <input type="text" value={form.reference}
                  onChange={e => setForm(f => ({ ...f, reference: e.target.value }))}
                  placeholder="اختیاری" className="input text-sm" />
              </div>

              <div>
                <label className="label text-xs mb-1 block">توضیحات</label>
                <textarea value={form.note}
                  onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                  placeholder="اختیاری" rows={2}
                  className="input text-sm resize-none" />
              </div>
            </div>

            {formMsg && (
              <div className={`mt-4 rounded-lg px-4 py-3 text-sm ${
                formMsg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                {formMsg.text}
              </div>
            )}

            <div className="flex gap-3 mt-5">
              <button onClick={handleSubmit} disabled={moveMutation.isPending}
                className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
                {moveMutation.isPending ? 'در حال ثبت...' : 'ثبت موجودی'}
              </button>
              <button onClick={() => { setShowForm(false); setFormMsg(null) }}
                className="btn-secondary text-sm py-2.5 px-5">انصراف</button>
            </div>
          </div>
        </div>
      )}

      {selectedVariant ? (
        <>
          <div className="card p-5 mb-6">
            <h2 className="font-semibold text-sm text-white mb-4">موجودی در انبارها</h2>
            <div className="grid grid-cols-5 gap-3">
              {warehouses.map(w => {
                const stock = stockData?.stocks?.find(s => s.warehouse === w.name)
                const qty = stock?.quantity ?? 0
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

          {movements.length > 0 && (
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="card p-4 text-center">
                <div className="text-xs text-gray-steel mb-1">کل ورودی</div>
                <div className="text-xl font-bold text-green-400">+{fmt(totalIn)}</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-xs text-gray-steel mb-1">کل خروجی</div>
                <div className="text-xl font-bold text-red-400">-{fmt(totalOut)}</div>
              </div>
              <div className="card p-4 text-center">
                <div className="text-xs text-gray-steel mb-1">تعداد تراکنش</div>
                <div className="text-xl font-bold text-white">{fmt(movements.length)}</div>
              </div>
            </div>
          )}

          <div className="card p-5">
            <h2 className="font-semibold text-sm text-white mb-4">تاریخچه حرکات</h2>
            {loadingKardex ? (
              <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
            ) : movements.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-3">📋</div>
                <div className="text-gray-steel text-sm mb-4">هنوز حرکتی ثبت نشده</div>
                <button onClick={() => setShowForm(true)} className="btn-primary text-sm px-6 py-2">
                  + ثبت اولین ورود موجودی
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                      {['تاریخ', 'انبار', 'نوع', 'تعداد', 'موجودی بعد', 'قیمت واحد', 'خریدار', 'شماره فاکتور', 'ثبت‌کننده'].map(h => (
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
                          color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }}>{formatDate(m.date)}</td>
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
                          {m.unit_price ? fmt(m.unit_price) + ' ریال' : '—'}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-primary)', fontSize: 12, whiteSpace: 'nowrap' }}>
                          {m.counterparty || '—'}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>
                          {m.reference || '—'}
                        </td>
                        <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                          <UserStamp createdBy={m.created_by} />
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
          <div className="text-5xl mb-4">📦</div>
          <div className="text-gray-steel">نام محصول یا کد SKU را جستجو کنید</div>
          {!loadingVariants && allVariants.length > 0 && (
            <div className="text-xs text-green-400 mt-2">{fmt(allVariants.length)} محصول آماده است</div>
          )}
        </div>
      )}
    </div>
  )
}
