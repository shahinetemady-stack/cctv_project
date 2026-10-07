import { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import { UserStamp } from '../../components/ui'
import SearchSelect, { advanceFlow } from '../../components/ui/SearchSelect'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const WAREHOUSE_TYPES = [
  { value: 'air_transit', label: 'در راه هوایی' },
  { value: 'sea_transit', label: 'در راه دریایی' },
  { value: 'shop1',       label: 'فروشگاه یک' },
  { value: 'shop2',       label: 'فروشگاه دو' },
  { value: 'assembly',    label: 'انبار مونتاژ' },
]

// ─── مودال ساخت/ویرایش انبار ────────────────────────────────
function WarehouseForm({ warehouse, onClose }) {
  const qc = useQueryClient()
  const isEdit = !!warehouse
  const [form, setForm] = useState({
    name: warehouse?.name || '', code: warehouse?.code || '',
    warehouse_type: warehouse?.warehouse_type || 'shop1',
    is_public: warehouse?.is_public || false,
    is_active: warehouse?.is_active !== false,
    address: warehouse?.address || '',
  })
  const [msg, setMsg] = useState(null)

  const saveMut = useMutation({
    mutationFn: (payload) => isEdit
      ? api.patch(`/inventory/warehouses/${warehouse.id}/`, payload).then(r => r.data)
      : api.post('/inventory/warehouses/', payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['warehouses'])
      toast.success(isEdit ? 'انبار ویرایش شد' : 'انبار جدید ساخته شد')
      onClose()
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ذخیره انبار' }),
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
          <h2 className="font-bold text-white text-lg">{isEdit ? `✏️ ویرایش انبار «${warehouse.name}»` : '🏬 انبار جدید'}</h2>
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

          {isEdit && (
            <label className="flex items-center gap-2 text-sm text-gray-steel cursor-pointer">
              <input type="checkbox" checked={form.is_active}
                onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                className="accent-brand w-4 h-4" />
              انبار فعال است
              {!form.is_active && <span className="text-[10px] text-amber-400">(غیرفعال = از لیست انبارها و محاسبات موجودی خارج می‌شود)</span>}
            </label>
          )}
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={saveMut.isPending}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : isEdit ? '✓ ذخیره تغییرات' : '✓ ساخت انبار'}
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

// ─── مودال انتقال کالا بین انبارها (تکی و جمعی) ───────────────
function newRow() {
  return { variant_id: '', quantity: 0 }
}

function TransferModal({ warehouses, presetFrom, onClose }) {
  const qc = useQueryClient()

  const [form, setForm] = useState({
    from_warehouse_id: presetFrom || '', to_warehouse_id: '', note: '',
  })
  const [items, setItems] = useState([newRow()]) // [{variant_id, quantity}]
  const [msg, setMsg] = useState(null)

  const { data: variantsData } = useQuery({
    queryKey: ['variants-list'],
    queryFn: () => api.get('/catalog/variants/').then(r => r.data),
  })

  // موجودی انبار مبدأ — برای نمایش «موجود» کنار هر ردیف
  const { data: fromStocks = [] } = useQuery({
    queryKey: ['warehouse-stocks', form.from_warehouse_id],
    queryFn: () => api.get(`/inventory/warehouses/${form.from_warehouse_id}/stocks/`).then(r => r.data),
    enabled: !!form.from_warehouse_id,
  })
  const stockMap = useMemo(
    () => Object.fromEntries(fromStocks.map(s => [String(s.variant_id), s.quantity])),
    [fromStocks]
  )

  const allVariants = Array.isArray(variantsData)
    ? variantsData
    : (variantsData?.results || variantsData?.data || [])

  // گزینه‌های هر ردیف: فقط کالاهای انبار مبدأ که در ردیف‌های دیگر انتخاب نشده‌اند
  function rowOptions(item) {
    if (!form.from_warehouse_id) return []
    const others = new Set(items.filter(i => i !== item && i.variant_id).map(i => String(i.variant_id)))
    return allVariants
      .filter(v => stockMap[String(v.id)] !== undefined && !others.has(String(v.id)))
      .map(v => ({
        value: v.id,
        label: v.product_name,
        sub: `${v.sku || ''} | موجودی: ${Number(stockMap[String(v.id)]).toLocaleString('fa-IR')}`,
      }))
  }

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

  function updateRow(idx, patch) {
    setItems(list => list.map((it, i) => i === idx ? { ...it, ...patch } : it))
  }

  function addRow() {
    setItems(list => [...list, newRow()])
  }

  function removeRow(idx) {
    setItems(list => list.filter((_, i) => i !== idx))
  }

  function handleQtyEnter(idx, e) {
    if (idx === items.length - 1) addRow()
    setTimeout(() => advanceFlow('tr', e.target), 60)
  }

  function handleSubmit() {
    if (!form.from_warehouse_id || !form.to_warehouse_id)
      return setMsg({ type: 'error', text: 'انبار مبدأ و مقصد را انتخاب کنید' })
    if (String(form.from_warehouse_id) === String(form.to_warehouse_id))
      return setMsg({ type: 'error', text: 'انبار مبدأ و مقصد نمی‌تواند یکی باشد' })
    const validItems = items.filter(i => i.variant_id)
    if (validItems.length === 0)
      return setMsg({ type: 'error', text: 'حداقل یک قلم کالا انتخاب کنید' })
    for (const i of validItems) {
      const name = allVariants.find(v => String(v.id) === String(i.variant_id))?.product_name || `#${i.variant_id}`
      const qty = Number(i.quantity)
      if (!qty || qty <= 0)
        return setMsg({ type: 'error', text: `تعداد «${name}» معتبر نیست` })
      const avail = stockMap[String(i.variant_id)]
      if (avail !== undefined && qty > avail)
        return setMsg({ type: 'error', text: `موجودی «${name}» در انبار مبدأ ${avail} عدد است` })
    }
    setMsg(null)
    transferMut.mutate({
      ...form,
      items: validItems.map(i => ({ variant_id: i.variant_id, quantity: Number(i.quantity) })),
    })
  }

  const totalQty = items.reduce((s, i) => s + (Number(i.quantity) || 0), 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">🔀 انتقال کالا بین انبارها</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white text-2xl">×</button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-xs mb-1 block">از انبار *</label>
              <select value={form.from_warehouse_id}
                onChange={e => { setForm(f => ({ ...f, from_warehouse_id: e.target.value })); setItems([newRow()]) }}
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

          {/* اقلام انتقال — همان ساختار ردیف‌های فاکتور: کالا + تعداد */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label text-xs">اقلام انتقال *</label>
              <span className="text-[10px] text-gray-steel">
                {items.filter(i => i.variant_id).length} قلم — مجموع {totalQty} عدد
              </span>
            </div>
            <div className="space-y-3">
              {items.map((i, idx) => {
                const avail = i.variant_id ? stockMap[String(i.variant_id)] : undefined
                const over = avail !== undefined && Number(i.quantity) > avail
                return (
                  <div key={idx} className="bg-white/5 rounded-xl p-3">
                    <div className="grid grid-cols-4 gap-3">
                      <div className="col-span-3">
                        <label className="label text-[10px] mb-1 block">کالا *</label>
                        <SearchSelect
                          options={rowOptions(i)}
                          value={i.variant_id}
                          onChange={val => updateRow(idx, { variant_id: val })}
                          placeholder={form.from_warehouse_id ? 'جستجوی کالا (نام یا کد)...' : 'ابتدا انبار مبدأ را انتخاب کنید'}
                          className="input text-xs" flow="tr"
                        />
                      </div>
                      <div>
                        <label className="label text-[10px] mb-1 block">تعداد *</label>
                        <input type="number" min="0" value={i.quantity} data-flow="tr"
                          onChange={e => updateRow(idx, { quantity: e.target.value })}
                          onFocus={e => e.target.select()}
                          onKeyDown={e => {
                            if (e.key === 'Enter') {
                              e.preventDefault()
                              handleQtyEnter(idx, e)
                            }
                          }}
                          className="input text-xs" dir="ltr" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <div className="text-[10px] text-gray-steel">
                        {avail !== undefined && (
                          <>موجودی انبار مبدأ: <b className={over ? 'text-red-400' : 'text-green-400'}>{fmt(avail)}</b>
                          {over && <span className="text-red-400 mr-1">(بیشتر از موجودی!)</span>}</>
                        )}
                      </div>
                      {items.length > 1 && (
                        <button onClick={() => removeRow(idx)} className="text-xs text-red-400">× حذف</button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            <button type="button" onClick={addRow} className="text-xs text-brand mt-3">+ افزودن کالا</button>
          </div>

          <div>
            <label className="label text-xs mb-1 block">توضیحات</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))}
              className="input text-sm" placeholder="اختیاری" />
          </div>
        </div>

        {msg && (
          <div className="mt-4 rounded-lg px-4 py-2 text-sm bg-red-500/20 text-red-400">{msg.text}</div>
        )}

        <div className="flex gap-3 mt-5">
          <button onClick={handleSubmit} disabled={transferMut.isPending || !items.some(i => i.variant_id)}
            className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
            {transferMut.isPending ? 'در حال انتقال...' : items.filter(i => i.variant_id).length > 1 ? `✓ انتقال ${items.filter(i => i.variant_id).length} قلم کالا` : '✓ انجام انتقال'}
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
  const [editing, setEditing] = useState(null)
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
                  <button onClick={() => setEditing(w)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/15 text-amber-400 hover:bg-amber-500/25 transition-all">
                    ویرایش
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
                      <UserStamp createdBy={t.transferred_by === '—' ? '' : t.transferred_by} updatedBy={t.updated_by} createdAt={t.date} />
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
      {editing && <WarehouseForm warehouse={editing} onClose={() => setEditing(null)} />}
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
