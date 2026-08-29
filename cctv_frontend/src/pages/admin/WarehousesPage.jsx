import { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import { UserStamp } from '../../components/ui'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const WAREHOUSE_TYPES = [
  { value: 'air_transit', label: 'در راه هوایی' },
  { value: 'sea_transit', label: 'در راه دریایی' },
  { value: 'shop1',       label: 'فروشگاه یک' },
  { value: 'shop2',       label: 'فروشگاه دو' },
  { value: 'assembly',    label: 'انبار مونتاژ' },
]

// ─── مودال ساخت انبار جدید ──────────────────────────────────
function WarehouseForm({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    name: '', code: '', warehouse_type: 'shop1', is_public: false, address: '',
  })
  const [msg, setMsg] = useState(null)

  const saveMut = useMutation({
    mutationFn: (payload) => api.post('/inventory/warehouses/', payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['warehouses'])
      toast.success('انبار جدید ساخته شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ساخت انبار' }),
  })

  function handleSubmit() {
    if (!form.name.trim() || !form.code.trim())
      return setMsg({ type: 'error', text: 'نام و کد انبار را وارد کنید' })
    saveMut.mutate({ ...form, name: form.name.trim(), code: form.code.trim() })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">🏬 انبار جدید</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">نام انبار *</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="input text-sm" placeholder="مثلاً فروشگاه مرکزی" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">کد انبار *</label>
              <input value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                className="input text-sm" placeholder="مثلاً SHOP3" dir="ltr" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">نوع انبار</label>
              <select value={form.warehouse_type} onChange={e => setForm(f => ({ ...f, warehouse_type: e.target.value }))}
                className="input text-sm">
                {WAREHOUSE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 text-sm text-gray-steel cursor-pointer">
                <input type="checkbox" checked={form.is_public}
                  onChange={e => setForm(f => ({ ...f, is_public: e.target.checked }))}
                  className="accent-brand w-4 h-4" />
                نمایش موجودی به مشتری
              </label>
            </div>
          </div>

          <div>
            <label className="label text-xs mb-1 block">آدرس</label>
            <input value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
              className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : '✓ ساخت انبار'}
          </button>
          <button onClick={onClose} className="btn-secondary text-sm py-2.5 px-6">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── مودال موجودی یک انبار ──────────────────────────────────
function StocksModal({ warehouse, onClose }) {
  const { data: stocks = [], isLoading } = useQuery({
    queryKey: ['warehouse-stocks', warehouse.id],
    queryFn: () => api.get(`/inventory/warehouses/${warehouse.id}/stocks/`).then(r => r.data),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">موجودی «{warehouse.name}»</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        {isLoading ? (
          <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : stocks.length === 0 ? (
          <div className="text-center py-10 text-gray-steel text-sm">این انبار موجودی ندارد</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['#', 'محصول', 'SKU', 'موجودی'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stocks.map((s, i) => (
                  <tr key={s.variant_id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{fmt(i + 1)}</td>
                    <td style={{ padding: '10px 12px' }}>{s.product_name}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{s.sku}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: '#00C896' }}>{fmt(s.quantity)}</td>
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

// ─── مودال انتقال کالا بین انبارها ──────────────────────────
function TransferModal({ warehouses, presetFrom, onClose }) {
  const qc = useQueryClient()
  const searchRef = useRef(null)

  const [form, setForm] = useState({
    from_warehouse_id: presetFrom || '', to_warehouse_id: '', variant_id: '', quantity: '', note: '',
  })
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [msg, setMsg] = useState(null)

  const { data: variantsData } = useQuery({
    queryKey: ['variants-list'],
    queryFn: () => api.get('/catalog/variants/').then(r => r.data),
  })

  const allVariants = Array.isArray(variantsData)
    ? variantsData
    : (variantsData?.results || variantsData?.data || [])

  const filtered = useMemo(() => {
    if (!search) return allVariants.slice(0, 30)
    const q = search.toLowerCase()
    return allVariants.filter(v =>
      (v.product_name || '').toLowerCase().includes(q) ||
      (v.sku || '').toLowerCase().includes(q) ||
      (v.category || '').toLowerCase().includes(q)
    ).slice(0, 30)
  }, [allVariants, search])

  const selectedInfo = allVariants.find(v => String(v.id) === String(form.variant_id))

  useEffect(() => {
    function onClickOutside(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const transferMut = useMutation({
    mutationFn: (payload) => api.post('/inventory/transfers/', payload).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries(['warehouses'])
      qc.invalidateQueries(['warehouse-stocks'])
      qc.invalidateQueries(['transfers-list'])
      toast.success(data.message || 'انتقال انجام شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در انتقال' }),
  })

  function handleSubmit() {
    if (!form.from_warehouse_id || !form.to_warehouse_id)
      return setMsg({ type: 'error', text: 'انبار مبدأ و مقصد را انتخاب کنید' })
    if (String(form.from_warehouse_id) === String(form.to_warehouse_id))
      return setMsg({ type: 'error', text: 'انبار مبدأ و مقصد نمی‌تواند یکی باشد' })
    if (!form.variant_id)
      return setMsg({ type: 'error', text: 'محصول را انتخاب کنید' })
    const qty = Number(form.quantity)
    if (!qty || qty <= 0)
      return setMsg({ type: 'error', text: 'تعداد معتبر وارد کنید' })
    setMsg(null)
    transferMut.mutate({ ...form, quantity: qty })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">🔀 انتقال کالا بین انبارها</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">از انبار *</label>
              <select value={form.from_warehouse_id}
                onChange={e => setForm(f => ({ ...f, from_warehouse_id: e.target.value }))}
                className="input text-sm">
                <option value="">انتخاب کنید</option>
                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label text-xs mb-1 block">به انبار *</label>
              <select value={form.to_warehouse_id}
                onChange={e => setForm(f => ({ ...f, to_warehouse_id: e.target.value }))}
                className="input text-sm">
                <option value="">انتخاب کنید</option>
                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
          </div>

          <div ref={searchRef} className="relative">
            <label className="label text-xs mb-1 block">محصول *</label>
            <input
              value={selectedInfo ? `${selectedInfo.product_name} (${selectedInfo.sku})` : search}
              onChange={e => {
                setSearch(e.target.value)
                setForm(f => ({ ...f, variant_id: '' }))
                setShowDropdown(true)
              }}
              onFocus={() => setShowDropdown(true)}
              className="input text-sm"
              placeholder="جستجوی نام یا SKU محصول..."
            />
            {showDropdown && !selectedInfo && (
              <div className="absolute z-10 w-full mt-1 card max-h-60 overflow-y-auto p-1">
                {filtered.length === 0 ? (
                  <div className="text-center py-4 text-gray-steel text-xs">محصولی یافت نشد</div>
                ) : filtered.map(v => (
                  <button key={v.id} type="button"
                    onClick={() => { setForm(f => ({ ...f, variant_id: v.id })); setShowDropdown(false) }}
                    className="w-full text-right px-3 py-2 rounded-lg hover:bg-white/10 text-sm">
                    {v.product_name}
                    <span className="text-gray-steel text-xs mr-2" dir="ltr">{v.sku}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">تعداد *</label>
              <input type="number" min="1" value={form.quantity}
                onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                className="input text-sm" placeholder="0" dir="ltr" />
            </div>
            <div>
              <label className="label text-xs mb-1 block">توضیحات</label>
              <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
                className="input text-sm" placeholder="اختیاری" />
            </div>
          </div>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={transferMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {transferMut.isPending ? 'در حال انتقال...' : '✓ انجام انتقال'}
          </button>
          <button onClick={onClose} className="btn-secondary text-sm py-2.5 px-6">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه مدیریت انبارها ────────────────────────────────────
export default function WarehousesPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [stocksOf, setStocksOf] = useState(null)
  const [transferFrom, setTransferFrom] = useState(null)   // null=بسته، ''=بدون پیش‌انتخاب
  const [confirmDelete, setConfirmDelete] = useState(null)

  const { data: warehousesData, isLoading } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => api.get('/inventory/warehouses/').then(r => r.data),
  })

  const { data: transfersData } = useQuery({
    queryKey: ['transfers-list'],
    queryFn: () => api.get('/inventory/transfers/').then(r => r.data),
  })

  const warehouses = Array.isArray(warehousesData)
    ? warehousesData
    : (warehousesData?.results || warehousesData?.data || [])
  const transfers = Array.isArray(transfersData)
    ? transfersData
    : (transfersData?.results || transfersData?.data || [])

  const delMut = useMutation({
    mutationFn: (id) => api.delete(`/inventory/warehouses/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries(['warehouses'])
      toast.success('انبار حذف شد')
      setConfirmDelete(null)
    },
    onError: (e) => {
      toast.error(e.response?.data?.error || 'خطا در حذف انبار')
      setConfirmDelete(null)
    },
  })

  const totalStock = warehouses.reduce((s, w) => s + (w.total_quantity || 0), 0)

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="font-display font-bold text-2xl text-white">انبارها</h1>
        <div className="flex gap-3">
          <button onClick={() => setTransferFrom('')}
            className="btn-secondary text-sm px-4 py-2">
            🔀 انتقال کالا
          </button>
          <button onClick={() => setShowForm(true)} className="btn-primary text-sm px-4 py-2">
            + انبار جدید
          </button>
        </div>
      </div>

      {/* خلاصه */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="card p-4">
          <div className="text-xs text-gray-steel mb-2">تعداد انبارهای فعال</div>
          <div className="text-xl font-bold text-white">{fmt(warehouses.length)}</div>
        </div>
        <div className="card p-4">
          <div className="text-xs text-gray-steel mb-2">جمع موجودی همه انبارها</div>
          <div className="text-xl font-bold text-green-400">{fmt(totalStock)} قلم</div>
        </div>
      </div>

      {/* لیست انبارها */}
      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : warehouses.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">🏬</div>
          <div className="text-gray-steel text-sm">هنوز انباری ثبت نشده — با دکمه «انبار جدید» شروع کنید</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {warehouses.map(w => (
            <div key={w.id} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-bold text-white text-lg">{w.name}</div>
                  <div className="text-xs text-gray-steel mt-1">{w.type} | کد: <span dir="ltr">{w.code}</span></div>
                </div>
                {w.is_public && <span className="badge badge-success">عمومی</span>}
              </div>

              <div className="flex items-end justify-between">
                <div>
                  <div className="text-[11px] text-gray-steel mb-1">موجودی</div>
                  <div className="text-lg font-bold text-green-400">{fmt(w.total_quantity)} قلم</div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setStocksOf(w)} className="btn-ghost text-xs px-3 py-1.5">
                    موجودی‌ها
                  </button>
                  <button onClick={() => setTransferFrom(String(w.id))}
                    className="text-xs px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 transition-all">
                    انتقال
                  </button>
                  <button onClick={() => setConfirmDelete(w)} disabled={delMut.isPending}
                    className="text-xs px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all disabled:opacity-50">
                    حذف
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* آخرین انتقال‌ها */}
      <h3 className="text-sm font-semibold text-white mb-4">آخرین انتقال‌ها</h3>
      <div className="card p-5">
        {transfers.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-sm">انتقالی ثبت نشده</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['تاریخ', 'محصول', 'از انبار', 'به انبار', 'تعداد', 'ثبت‌کننده', 'توضیحات'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transfers.map((t, i) => (
                  <tr key={t.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11, whiteSpace: 'nowrap' }} dir="ltr">{t.date}</td>
                    <td style={{ padding: '10px 12px' }}>
                      {t.product_name}
                      <span className="text-gray-steel text-xs mr-2" dir="ltr">{t.sku}</span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>{t.from_warehouse}</td>
                    <td style={{ padding: '10px 12px' }}>{t.to_warehouse}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: '#0066FF' }}>{fmt(t.quantity)}</td>
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                      <UserStamp createdBy={t.transferred_by === '—' ? '' : t.transferred_by} updatedBy={t.updated_by} />
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{t.note || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showForm && <WarehouseForm onClose={() => setShowForm(false)} />}
      {stocksOf && <StocksModal warehouse={stocksOf} onClose={() => setStocksOf(null)} />}
      {transferFrom !== null && (
        <TransferModal warehouses={warehouses} presetFrom={transferFrom} onClose={() => setTransferFrom(null)} />
      )}

      {/* تایید حذف */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="card p-6 w-full max-w-md">
            <h2 className="font-bold text-white text-lg mb-3">🗑 حذف انبار</h2>
            <p className="text-sm text-gray-steel mb-5">
              انبار «{confirmDelete.name}» حذف شود؟ این کار قابل بازگشت نیست.
              {confirmDelete.total_quantity > 0 && (
                <span className="block mt-2 text-red-400">
                  ⚠️ این انبار {fmt(confirmDelete.total_quantity)} قلم موجودی دارد — ابتدا باید موجودی را منتقل کنید.
                </span>
              )}
            </p>
            <div className="flex gap-3">
              <button onClick={() => delMut.mutate(confirmDelete.id)} disabled={delMut.isPending}
                className="flex-1 text-sm py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold transition-all disabled:opacity-50">
                {delMut.isPending ? 'در حال حذف...' : 'حذف انبار'}
              </button>
              <button onClick={() => setConfirmDelete(null)} className="btn-secondary text-sm py-2.5 px-6">انصراف</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
