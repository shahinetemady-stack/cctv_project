import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Trash2, Tag, ChevronDown, ChevronUp, Pencil } from 'lucide-react'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import CategoryFieldsManager from '../../components/admin/CategoryFieldsManager'

const TYPE_LABEL = { board: 'برد', lens: 'لنز', modem: 'مودم', housing: 'بدنه', accessory: 'لوازم جانبی', recorder: 'برد دستگاه ضبط', other: 'سایر' }

// ─── صفحه مدیریت دسته‌بندی ────────────────────────────────────
export default function AdminCategoriesPage() {
  const qc = useQueryClient()
  const [openId, setOpenId] = useState(null) // دسته بازشده برای مدیریت ویژگی‌ها
  const [newCat, setNewCat] = useState({ name: '', category_type: 'other', parent: '' })
  const [editCatId, setEditCatId] = useState(null) // دسته در حال ویرایش
  const [catForm, setCatForm] = useState({ name: '', category_type: 'other', sort_order: 0, parent: '' })

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ['admin-categories-full'],
    queryFn: () => api.get('/catalog/categories/admin/').then(r => r.data),
  })

  // درخت دو سطحی: ریشه‌ها + فرزندان هرکدام (به ترتیب)
  const roots = categories.filter(c => !c.parent)
  const childrenOf = (id) => categories.filter(c => c.parent === id)
  const ordered = roots.flatMap(r => [r, ...childrenOf(r.id)])
  const catName = (id) => categories.find(c => c.id === id)?.name || ''

  const createMut = useMutation({
    mutationFn: (d) => api.post('/catalog/categories/admin/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      setNewCat({ name: '', category_type: 'other', parent: '' })
      toast.success('دسته‌بندی ساخته شد')
    },
    onError: (e) => toast.error(e.response?.data?.parent?.[0] || JSON.stringify(e.response?.data || 'خطا')),
  })

  const deleteCatMut = useMutation({
    mutationFn: (id) => api.delete(`/catalog/categories/admin/${id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      toast.success('دسته حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف'),
  })

  // ویرایش دسته (نام/نوع/والد/ترتیب)
  const updateCatMut = useMutation({
    mutationFn: ({ id, ...d }) => api.patch(`/catalog/categories/admin/${id}/`, d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      setEditCatId(null)
      toast.success('دسته به‌روز شد')
    },
    onError: (e) => toast.error(e.response?.data?.parent?.[0] || e.response?.data?.error || 'خطا'),
  })

  return (
    <div className="container-main py-8 max-w-4xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">مدیریت دسته‌بندی</h1>

      {/* ساخت دسته جدید */}
      <div className="card p-4 mb-6 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="label text-xs mb-1 block">نام دسته جدید *</label>
          <input value={newCat.name} onChange={e => setNewCat(x => ({ ...x, name: e.target.value }))}
            className="input-dark text-xs w-full" placeholder="مثلاً: دستگاه ضبط DVR" />
        </div>
        <div>
          <label className="label text-xs mb-1 block">دسته والد</label>
          <select value={newCat.parent}
            onChange={e => {
              const pid = e.target.value
              const p = categories.find(c => c.id === Number(pid))
              // با انتخاب والد، نوع دسته به‌صورت پیش‌فرض از والد به ارث می‌رسد
              setNewCat(x => ({ ...x, parent: pid, category_type: p ? p.category_type : x.category_type }))
            }}
            className="input-dark text-xs w-40">
            <option value="">— (دسته اصلی)</option>
            {roots.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label text-xs mb-1 block">نوع دسته</label>
          {newCat.parent ? (
            <div className="input-dark text-xs w-36 opacity-60 select-none" title="نوع زیردسته از والد به ارث می‌رسد">
              {TYPE_LABEL[categories.find(c => c.id === Number(newCat.parent))?.category_type] || '—'}
              <span className="text-[9px] text-gray-steel block">از والد</span>
            </div>
          ) : (
            <select value={newCat.category_type} onChange={e => setNewCat(x => ({ ...x, category_type: e.target.value }))}
              className="input-dark text-xs w-36">
              {Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          )}
        </div>
        <button onClick={() => createMut.mutate({ ...newCat, parent: newCat.parent || null })}
          disabled={!newCat.name.trim() || createMut.isPending}
          className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 disabled:opacity-50">
          <Plus size={14} /> {newCat.parent ? 'ساخت زیردسته' : 'ساخت دسته'}
        </button>
      </div>

      {isLoading ? <PageLoader /> : (
        <div className="space-y-3">
          {ordered.map(c => (
            <div key={c.id} className={`card overflow-hidden ${c.parent ? 'mr-8 border-r-2 !border-[var(--color-brand)]' : ''}`}>
              {/* ردیف دسته */}
              <div className="flex items-center gap-3 px-4 py-3">
                <Tag size={16} className={`flex-shrink-0 ${c.parent ? 'text-gray-steel' : 'text-gold'}`} />
                <button onClick={() => setOpenId(openId === c.id ? null : c.id)}
                  className="flex-1 text-right font-semibold text-sm text-white hover:text-gold transition-colors">
                  {c.parent && <span className="text-gray-steel font-normal ml-1">└</span>}
                  {c.name}
                  {c.parent && <span className="text-[10px] font-normal text-gray-steel mr-2">زیردستهٔ {catName(c.parent)}</span>}
                </button>
                <span className="badge text-[10px]">{TYPE_LABEL[c.category_type] || c.category_type}</span>
                <span className="text-[11px] text-gray-steel">{c.product_count} محصول</span>
                <span className="text-[11px] text-gray-steel">{c.spec_fields.length} ویژگی</span>
                <button
                  onClick={() => {
                    setEditCatId(editCatId === c.id ? null : c.id)
                    setCatForm({ name: c.name, category_type: c.category_type, sort_order: c.sort_order, parent: c.parent || '' })
                    setOpenId(c.id)
                  }}
                  className="text-gray-steel hover:text-gold p-1 transition-colors" title="ویرایش دسته">
                  <Pencil size={14} />
                </button>
                <button onClick={() => setOpenId(openId === c.id ? null : c.id)}
                  className="text-gray-steel hover:text-white p-1" title="مدیریت ویژگی‌ها">
                  {openId === c.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                <button
                  onClick={() => { if (window.confirm(`دسته «${c.name}» حذف شود؟`)) deleteCatMut.mutate(c.id) }}
                  className="text-red-400 hover:text-red-300 p-1" title="حذف دسته">
                  <Trash2 size={15} />
                </button>
              </div>

              {/* پنل ویژگی‌های دسته */}
              {openId === c.id && (
                <div className="border-t border-[var(--color-border)] p-4 bg-[var(--color-brand-softer)]">
                  {/* فرم ویرایش دسته */}
                  {editCatId === c.id && (
                    <div className="flex flex-wrap items-end gap-2 mb-5 bg-[var(--color-bg-card)] border border-[var(--color-brand)] rounded-lg p-3">
                      <div>
                        <label className="label text-[10px] mb-1 block">نام دسته</label>
                        <input value={catForm.name} onChange={e => setCatForm(x => ({ ...x, name: e.target.value }))}
                          className="input-dark text-xs w-44" />
                      </div>
                      <div>
                        <label className="label text-[10px] mb-1 block">نوع دسته</label>
                        {catForm.parent ? (
                          <div className="input-dark text-xs w-32 opacity-60 select-none" title="نوع زیردسته از والد به ارث می‌رسد">
                            {TYPE_LABEL[categories.find(c => c.id === Number(catForm.parent))?.category_type] || '—'}
                            <span className="text-[9px] text-gray-steel block">از والد</span>
                          </div>
                        ) : (
                          <select value={catForm.category_type} onChange={e => setCatForm(x => ({ ...x, category_type: e.target.value }))}
                            className="input-dark text-xs w-32">
                            {Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                          </select>
                        )}
                      </div>
                      <div>
                        <label className="label text-[10px] mb-1 block">دسته والد</label>
                        <select value={catForm.parent} onChange={e => setCatForm(x => ({ ...x, parent: e.target.value }))}
                          className="input-dark text-xs w-36">
                          <option value="">— (دسته اصلی)</option>
                          {roots.filter(r => r.id !== c.id).map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="label text-[10px] mb-1 block">ترتیب</label>
                        <input type="number" value={catForm.sort_order} onChange={e => setCatForm(x => ({ ...x, sort_order: Number(e.target.value) }))}
                          className="input-dark text-xs w-20" dir="ltr" />
                      </div>
                      <button onClick={() => updateCatMut.mutate({ id: c.id, ...catForm, parent: catForm.parent || null })} disabled={!catForm.name.trim() || updateCatMut.isPending}
                        className="btn-primary text-xs px-4 py-2 disabled:opacity-50">ذخیره</button>
                      <button onClick={() => setEditCatId(null)} className="btn-secondary text-xs px-3 py-2">انصراف</button>
                    </div>
                  )}

                  <CategoryFieldsManager cat={c} parentCat={c.parent ? categories.find(x => x.id === c.parent) : null} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
