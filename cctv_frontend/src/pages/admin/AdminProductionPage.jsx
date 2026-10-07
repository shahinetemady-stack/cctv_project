import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Trash2, Search, Factory, RotateCcw } from 'lucide-react'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import AmountInput from '../../components/ui/AmountInput'
import SearchSelect from '../../components/ui/SearchSelect'
import usePermissions from '../../hooks/usePermissions'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const normalize = (s) => String(s ?? '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
  .replace(/ك/g, 'ک').replace(/ي/g, 'ی')
  .toLowerCase()

// ─── مودال ساخت محصول نهایی ───
function NewProductModal({ categories, onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', category_id: '', model_number: '', sku: '' })
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    if (!form.name.trim()) return toast.error('نام محصول الزامی است')
    if (!form.category_id) return toast.error('دسته را انتخاب کنید')
    setBusy(true)
    try {
      const r = await api.post('/production/recipes/', {
        name: form.name.trim(), category_id: Number(form.category_id),
        model_number: form.model_number.trim(), sku: form.sku.trim(),
      })
      toast.success(`محصول نهایی با کد ${r.data.sku} ساخته شد`)
      onCreated(r.data)
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ساخت محصول')
    } finally { setBusy(false) }
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="card p-5 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-semibold text-white mb-4">محصول نهایی جدید (دوربین / دستگاه مونتاژی)</h3>
        <div className="space-y-3">
          <div>
            <label className="label text-xs block mb-1">نام محصول *</label>
            <input className="input-dark text-sm w-full" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="مثلاً دوربین مداربسته ۵ مگاپیکسل دام" />
          </div>
          <div>
            <label className="label text-xs block mb-1">دسته *</label>
            <select className="input-dark text-sm w-full" value={form.category_id}
              onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))}>
              <option value="">انتخاب دسته...</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label text-xs block mb-1">شماره مدل</label>
              <input className="input-dark text-sm w-full" value={form.model_number}
                onChange={e => setForm(f => ({ ...f, model_number: e.target.value }))} />
            </div>
            <div>
              <label className="label text-xs block mb-1">SKU (اختیاری)</label>
              <input className="input-dark text-sm w-full" dir="ltr" value={form.sku}
                onChange={e => setForm(f => ({ ...f, sku: e.target.value }))} placeholder="P-… خودکار" />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="btn-ghost text-xs px-4 py-1.5">انصراف</button>
          <button onClick={submit} disabled={busy} className="btn-primary text-xs px-4 py-1.5 disabled:opacity-50">
            {busy ? '...' : 'ساخت محصول'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── انتخاب قطعه با جستجو ───
function ComponentPicker({ variants, onPick }) {
  const [q, setQ] = useState('')
  const nq = normalize(q.trim())
  const results = useMemo(() => !nq ? [] :
    variants.filter(v => normalize(v.name).includes(nq) || normalize(v.sku).includes(nq)).slice(0, 8),
    [variants, nq])
  return (
    <div className="relative">
      <Search size={13} className="absolute top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" style={{ right: 8 }} />
      <input value={q} onChange={e => setQ(e.target.value)} placeholder="جستجوی قطعه (نام یا SKU)..."
        className="input-dark text-xs w-full" style={{ paddingRight: '1.75rem' }} />
      {results.length > 0 && (
        <div className="absolute z-20 top-full mt-1 right-0 left-0 card p-1 max-h-56 overflow-y-auto">
          {results.map(v => (
            <button key={v.id} type="button"
              onClick={() => { onPick(v); setQ('') }}
              className="w-full text-right px-2 py-1.5 rounded hover:bg-white/5 text-xs">
              <span className="text-white">{v.name}</span>
              <span className="text-gray-steel mr-2" dir="ltr">{v.sku}</span>
              <span className={`mr-2 ${v.stock_quantity > 0 ? 'text-green-400' : 'text-red-400'}`}>
                موجودی {fmt(v.stock_quantity)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── کارت یک رسیپی (محصول نهایی + BOM + اجرای مونتاژ) ───
function RecipeCard({ recipe, variants, warehouses, defaultWarehouseId, contacts, canManage, onChanged }) {
  const [items, setItems] = useState(recipe.items.map(i => ({ ...i })))
  const [dirty, setDirty] = useState(false)
  const [savingBom, setSavingBom] = useState(false)
  const [qty, setQty] = useState('1')
  const [warehouseId, setWarehouseId] = useState(String(defaultWarehouseId || ''))
  const [assemblerId, setAssemblerId] = useState('')
  const [labor, setLabor] = useState('')
  const [consumables, setConsumables] = useState('')
  const [note, setNote] = useState('')
  const [running, setRunning] = useState(false)

  const unitCost = items.reduce((s, i) => s + i.unit_cost_irr * i.quantity, 0)
  const laborN = Number(labor) || 0
  const consumablesN = Number(consumables) || 0

  const addComponent = (v) => {
    if (items.some(i => i.variant_id === v.id)) return toast.error('این قطعه قبلاً اضافه شده')
    if (v.id === recipe.variant_id) return toast.error('محصول نهایی نمی‌تواند قطعه خودش باشد')
    setItems(is => [...is, { variant_id: v.id, sku: v.sku, name: v.name, quantity: 1, unit_cost_irr: 0, stock_quantity: v.stock_quantity }])
    setDirty(true)
  }
  const setQtyOf = (vid, q) => {
    setItems(is => is.map(i => i.variant_id === vid ? { ...i, quantity: Math.max(1, Number(q) || 1) } : i))
    setDirty(true)
  }
  const removeItem = (vid) => { setItems(is => is.filter(i => i.variant_id !== vid)); setDirty(true) }

  const saveBom = async () => {
    if (!items.length) return toast.error('حداقل یک قطعه اضافه کنید')
    setSavingBom(true)
    try {
      await api.put(`/production/recipes/${recipe.id}/`, {
        items: items.map(i => ({ variant_id: i.variant_id, quantity: i.quantity })),
      })
      toast.success('دستوره مونتاژ ذخیره شد')
      setDirty(false)
      onChanged()
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در ذخیره دستوره')
    } finally { setSavingBom(false) }
  }

  const runAssembly = async () => {
    const q = Number(qty) || 0
    if (q < 1) return toast.error('تعداد تولید را وارد کنید')
    if (!recipe.items.length) return toast.error('ابتدا دستوره مونتاژ را ذخیره کنید')
    if (dirty) return toast.error('ابتدا تغییرات دستوره را ذخیره کنید')
    if (laborN + consumablesN > 0 && !assemblerId) return toast.error('برای اجرت/لوازم مصرفی، مونتاژکار را انتخاب کنید')
    setRunning(true)
    try {
      const r = await api.post('/production/orders/', {
        recipe_id: recipe.id, quantity: q,
        warehouse_id: warehouseId ? Number(warehouseId) : undefined,
        assembler_id: assemblerId ? Number(assemblerId) : undefined,
        labor_cost_irr: laborN, consumables_cost_irr: consumablesN,
        note,
      })
      toast.success(`${fmt(q)} دستگاه تولید و به انبار واریز شد — بهای واحد ${fmt(r.data.unit_cost_irr)} ریال`)
      setQty('1'); setNote(''); setLabor(''); setConsumables('')
      onChanged()
    } catch (e) {
      const d = e.response?.data
      if (d?.shortages) toast.error(`موجودی کافی نیست: ${d.shortages[0]}`, { duration: 6000 })
      else toast.error(d?.error || 'خطا در اجرای مونتاژ')
    } finally { setRunning(false) }
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div>
          <span className="font-semibold text-white text-sm">{recipe.product_name}</span>
          <span className="text-[10px] text-gray-steel mr-2" dir="ltr">{recipe.sku}</span>
          <span className="text-[10px] text-gray-steel mr-2">{recipe.category_name}</span>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-gray-steel">موجودی: <b className={recipe.stock_quantity > 0 ? 'text-green-400' : 'text-red-400'}>{fmt(recipe.stock_quantity)}</b></span>
          <span className="text-gray-steel">بهای واحد: <b className="text-gold">{fmt(unitCost)}</b> ریال</span>
        </div>
      </div>

      {/* BOM */}
      <table className="w-full text-xs mb-2" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr className="text-gray-steel border-b border-white/10">
            <th className="text-right py-1 font-normal">قطعه</th>
            <th className="text-center py-1 font-normal w-20">تعداد</th>
            <th className="text-center py-1 font-normal">موجودی</th>
            <th className="text-center py-1 font-normal w-10"></th>
          </tr>
        </thead>
        <tbody>
          {items.map(i => (
            <tr key={i.variant_id} className="border-b border-white/5">
              <td className="py-1.5">
                <span className="text-white">{i.name}</span>
                <span className="text-gray-steel text-[10px] mr-1" dir="ltr">{i.sku}</span>
              </td>
              <td className="py-1.5 text-center">
                {canManage ? (
                  <input type="number" min="1" value={i.quantity}
                    onChange={e => setQtyOf(i.variant_id, e.target.value)}
                    className="input-dark text-xs w-14 text-center" />
                ) : fmt(i.quantity)}
              </td>
              <td className={`py-1.5 text-center ${i.stock_quantity > 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(i.stock_quantity)}</td>
              <td className="py-1.5 text-center">
                {canManage && (
                  <button onClick={() => removeItem(i.variant_id)} className="text-gray-steel hover:text-red-400">
                    <Trash2 size={13} />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {canManage && (
        <div className="flex items-center gap-2 mb-3">
          <div className="flex-1"><ComponentPicker variants={variants} onPick={addComponent} /></div>
          {dirty && (
            <button onClick={saveBom} disabled={savingBom}
              className="btn-primary text-xs px-4 py-1.5 disabled:opacity-50 whitespace-nowrap">
              {savingBom ? '...' : 'ذخیره دستوره'}
            </button>
          )}
        </div>
      )}

      {/* اجرای مونتاژ */}
      {canManage && (
        <div className="pt-3 border-t border-white/5 space-y-2">
          <div className="flex items-end gap-2 flex-wrap">
            <div>
              <label className="label text-[10px] block mb-1">تعداد تولید</label>
              <input type="number" min="1" value={qty} onChange={e => setQty(e.target.value)}
                className="input-dark text-xs w-20 text-center" />
            </div>
            <div>
              <label className="label text-[10px] block mb-1">انبار</label>
              <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)}
                className="input-dark text-xs">
                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
            <div className="min-w-[180px]">
              <label className="label text-[10px] block mb-1">مونتاژکار (طرف حساب)</label>
              <SearchSelect
                options={contacts.map(c => ({ value: c.id, label: c.name, sub: c.phone }))}
                value={assemblerId}
                onChange={setAssemblerId}
                placeholder="جستجو و انتخاب مونتاژکار..."
                flow="asm"
              />
            </div>
            <div>
              <label className="label text-[10px] block mb-1">اجرت مونتاژ واحد (ریال)</label>
              <AmountInput value={labor} onChange={e => setLabor(e.target.value)}
                placeholder="۰" className="input-dark text-xs w-28 text-center" />
            </div>
            <div>
              <label className="label text-[10px] block mb-1">لوازم مصرفی واحد (ریال)</label>
              <AmountInput value={consumables} onChange={e => setConsumables(e.target.value)}
                placeholder="۰" className="input-dark text-xs w-28 text-center" />
            </div>
          </div>
          <div className="flex items-end gap-2 flex-wrap">
            <div className="flex-1 min-w-[140px]">
              <label className="label text-[10px] block mb-1">یادداشت</label>
              <input value={note} onChange={e => setNote(e.target.value)} className="input-dark text-xs w-full" />
            </div>
            <button onClick={runAssembly} disabled={running}
              className="btn-primary text-xs px-4 py-1.5 disabled:opacity-50 flex items-center gap-1">
              <Factory size={13} /> {running ? '...' : 'اجرای مونتاژ'}
            </button>
            {Number(qty) > 0 && (
              <span className="text-[10px] text-gray-steel">
                بهای کل: {fmt((unitCost + laborN + consumablesN) * (Number(qty) || 0))} ریال
                {(laborN + consumablesN) > 0 && ' (قطعات + اجرت واحد + لوازم واحد)'}
              </span>
            )}
          </div>
          {(laborN + consumablesN) > 0 && (
            <div className="text-[10px] text-orange-300/80">
              ⚠ اجرت و لوازم مصرفی «هر واحد» است — جزو بهای تمام‌شده کالا لحاظ و به‌صورت سند هزینه (نرخ واحد × تعداد) در حساب مونتاژکار ثبت می‌شود (بدهی ما به او).
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── صفحه اصلی ───
export default function AdminProductionPage() {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const [showNew, setShowNew] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['production-recipes'],
    queryFn: () => api.get('/production/recipes/').then(r => r.data),
  })
  const { data: variants = [] } = useQuery({
    queryKey: ['variants-list'],
    queryFn: () => api.get('/catalog/variants/').then(r => r.data),
  })
  const { data: categoriesRaw = [] } = useQuery({
    queryKey: ['admin-categories'],
    queryFn: () => api.get('/catalog/categories/admin/').then(r => r.data.results || r.data || []),
  })
  const { data: orders = [] } = useQuery({
    queryKey: ['production-orders'],
    queryFn: () => api.get('/production/orders/').then(r => r.data),
  })
  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => api.get('/accounting/contacts/').then(r => r.data),
  })

  const cancelMut = useMutation({
    mutationFn: (id) => api.post(`/production/orders/${id}/cancel/`).then(r => r.data),
    onSuccess: () => { toast.success('دستور برگشت داده شد'); refresh() },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در برگشت'),
  })

  const refresh = () => {
    qc.invalidateQueries(['production-recipes'])
    qc.invalidateQueries(['production-orders'])
    qc.invalidateQueries(['variants-list'])
  }

  if (isLoading || !data) return <PageLoader />
  const canManage = can('production_manage')

  // فقط دسته‌های زیردرخت «دوربین و دستگاه ضبط» برای محصول نهایی پیشنهاد می‌شود (بقیه هم مجاز)
  const categories = categoriesRaw
  const asmRoot = categories.find(c => c.name === 'دوربین و دستگاه ضبط' && !c.parent)
  const sortedCats = asmRoot
    ? [...categories.filter(c => c.id === asmRoot.id || c.parent === asmRoot.id),
       ...categories.filter(c => c.id !== asmRoot.id && c.parent !== asmRoot.id)]
    : categories

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
        <h1 className="font-display font-bold text-2xl text-white">🏭 امور تولید</h1>
        {canManage && (
          <button onClick={() => setShowNew(true)} className="btn-primary text-xs px-4 py-2 flex items-center gap-1">
            <Plus size={14} /> محصول نهایی جدید
          </button>
        )}
      </div>

      <div className="text-[11px] text-gray-steel mb-4">
        دستوره مونتاژ (BOM) هر محصول را تعریف کنید؛ با «اجرای مونتاژ» قطعات از انبار کم و محصول نهایی با بهای
        تمام‌شده محاسبه‌شده به انبار واریز می‌شود و بلافاصله با قیمت فرمول دسته‌اش در سایت قابل فروش است.
      </div>

      {/* رسیپی‌ها */}
      <div className="space-y-4 mb-10">
        {data.recipes.length === 0 && (
          <div className="card p-12 text-center">
            <div className="text-4xl mb-3">🏭</div>
            <div className="text-gray-steel text-sm">هنوز محصول نهایی تعریف نشده — با «محصول نهایی جدید» شروع کنید</div>
          </div>
        )}
        {data.recipes.map(r => (
          <RecipeCard key={r.id} recipe={r} variants={variants} warehouses={data.warehouses}
            defaultWarehouseId={data.default_warehouse_id} contacts={contacts} canManage={canManage} onChanged={refresh} />
        ))}
      </div>

      {/* تاریخچه دستورها */}
      <h2 className="text-sm font-semibold text-white mb-3">تاریخچه دستورهای مونتاژ</h2>
      <div className="card overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', minWidth: 640 }}>
          <thead>
            <tr className="text-gray-steel border-b border-white/10">
              {['محصول', 'تعداد', 'انبار', 'بهای واحد', 'بهای کل', 'مونتاژکار', 'وضعیت', 'ثبت‌کننده', 'تاریخ', ''].map(h => (
                <th key={h} className="py-2 px-2 font-normal text-center first:text-right">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {orders.map(o => (
              <tr key={o.id} className="border-b border-white/5">
                <td className="py-2 px-2 text-white">{o.product_name}</td>
                <td className="py-2 px-2 text-center">{fmt(o.quantity)}</td>
                <td className="py-2 px-2 text-center text-gray-steel">{o.warehouse_name}</td>
                <td className="py-2 px-2 text-center text-gold">{fmt(o.unit_cost_irr)}</td>
                <td className="py-2 px-2 text-center">
                  {fmt(o.total_cost_irr)}
                  {(o.labor_cost_irr + o.consumables_cost_irr) > 0 && (
                    <div className="text-[9px] text-gray-steel mt-0.5">
                      {o.labor_cost_irr > 0 && `اجرت ${fmt(o.labor_cost_irr)}/واحد`}
                      {o.labor_cost_irr > 0 && o.consumables_cost_irr > 0 && ' + '}
                      {o.consumables_cost_irr > 0 && `لوازم ${fmt(o.consumables_cost_irr)}/واحد`}
                    </div>
                  )}
                </td>
                <td className="py-2 px-2 text-center text-gray-steel">{o.assembler_name || '—'}</td>
                <td className="py-2 px-2 text-center">
                  <span className={o.status === 'done' ? 'badge-green' : 'badge-red'}>{o.status_display}</span>
                </td>
                <td className="py-2 px-2 text-center text-gray-steel">{o.created_by}</td>
                <td className="py-2 px-2 text-center text-gray-steel" dir="ltr">
                  {new Date(o.created_at).toLocaleDateString('fa-IR', { timeZone: 'Asia/Tehran' })}
                  {' '}
                  {new Date(o.created_at).toLocaleTimeString('fa-IR', { timeZone: 'Asia/Tehran', hour: '2-digit', minute: '2-digit' })}
                </td>
                <td className="py-2 px-2 text-center">
                  {o.status === 'done' && canManage && (
                    <button onClick={() => { if (confirm('این دستور برگشت داده شود؟ قطعات به انبار برمی‌گردند و محصول نهایی خارج می‌شود.')) cancelMut.mutate(o.id) }}
                      className="text-gray-steel hover:text-orange-400" title="برگشت دستور">
                      <RotateCcw size={13} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr><td colSpan={10} className="py-8 text-center text-gray-steel">هنوز دستوری ثبت نشده</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showNew && (
        <NewProductModal categories={sortedCats} onClose={() => setShowNew(false)}
          onCreated={() => { setShowNew(false); refresh() }} />
      )}
    </div>
  )
}
