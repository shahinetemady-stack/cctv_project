// مدیریت ویژگی‌های یک دسته — مشترک بین صفحه «مدیریت دسته‌بندی» (آکاردئون هر دسته)
// و صفحه «ویژگی‌های دسته‌ها». این ویژگی‌ها در ویرایشگر محصول (کاتالوگ) پر می‌شوند.
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, X, Eye, EyeOff, Pencil, RotateCcw } from 'lucide-react'
import api from '../../services/api'

const FIELD_TYPE_LABEL = { text: 'متن', select: 'لیست کشویی', checkbox: 'تیک' }

// ─── فرم افزودن ویژگی سفارشی ──────────────────────────────────
function AddFieldForm({ categoryId, onDone }) {
  const qc = useQueryClient()
  const [f, setF] = useState({ label: '', field_type: 'text', choices: '' })

  const addMut = useMutation({
    mutationFn: (d) => api.post(`/catalog/categories/admin/${categoryId}/fields/`, d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      setF({ label: '', field_type: 'text', choices: '' })
      toast.success('ویژگی اضافه شد')
      onDone?.()
    },
    onError: (e) => toast.error(e.response?.data?.error || JSON.stringify(e.response?.data || 'خطا')),
  })

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div>
        <label className="label text-xs mb-1 block">نام ویژگی *</label>
        <input value={f.label} onChange={e => setF(x => ({ ...x, label: e.target.value }))}
          className="input-dark text-xs w-40" placeholder="مثلاً: تعداد کانال" />
      </div>
      <div>
        <label className="label text-xs mb-1 block">نوع</label>
        <select value={f.field_type} onChange={e => setF(x => ({ ...x, field_type: e.target.value }))}
          className="input-dark text-xs w-32">
          <option value="text">متن</option>
          <option value="select">لیست کشویی</option>
          <option value="checkbox">تیک</option>
        </select>
      </div>
      {f.field_type === 'select' && (
        <div className="flex-1 min-w-[180px]">
          <label className="label text-xs mb-1 block">گزینه‌ها (با ویرگول) *</label>
          <input value={f.choices} onChange={e => setF(x => ({ ...x, choices: e.target.value }))}
            className="input-dark text-xs w-full" placeholder="۴ کانال, ۸ کانال, ۱۶ کانال" />
        </div>
      )}
      <button onClick={() => addMut.mutate(f)}
        disabled={!f.label.trim() || (f.field_type === 'select' && !f.choices.trim()) || addMut.isPending}
        className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 disabled:opacity-50">
        <Plus size={14} /> افزودن
      </button>
    </div>
  )
}

// ─── مدیریت برندهای یک دسته — زیر ویژگی‌های پایه ──────────────
function BrandsSection({ cat }) {
  const qc = useQueryClient()
  const [newBrand, setNewBrand] = useState('')
  const [editing, setEditing] = useState(null) // نام برند در حال ویرایش
  const [newName, setNewName] = useState('')

  const invalidate = () => {
    qc.invalidateQueries(['admin-categories-full'])
    qc.invalidateQueries(['product-brands'])
  }

  const addMut = useMutation({
    mutationFn: (name) => api.post(`/catalog/categories/admin/${cat.id}/brands/`, { name }).then(r => r.data),
    onSuccess: () => { invalidate(); setNewBrand(''); toast.success('برند اضافه شد') },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در افزودن برند'),
  })

  const renameMut = useMutation({
    mutationFn: ({ from, to }) => api.post(`/catalog/categories/admin/${cat.id}/brands/rename/`, { from, to }).then(r => r.data),
    onSuccess: (d) => {
      invalidate()
      setEditing(null)
      toast.success(d.updated > 0
        ? `${d.updated} محصول از «${d.from}» به «${d.to}» منتقل شد`
        : `برند «${d.from}» به «${d.to}» تغییر نام داد`)
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ویرایش برند'),
  })

  const submitRename = () => {
    const to = newName.trim()
    if (!to || to === editing) { setEditing(null); return }
    renameMut.mutate({ from: editing, to })
  }

  const brands = cat.brands || []

  return (
    <div className="mb-5">
      <div className="text-xs font-bold text-gold mb-1">برندهای «{cat.name}»</div>
      <div className="text-[10px] text-gray-steel mb-3">
        دراپ‌داون برند در ویرایشگر محصول از همین لیست پر می‌شود — برای اصلاح غلط تایپی روی برند کلیک کنید؛ محصولاتش به نام جدید منتقل می‌شوند.
      </div>
      {brands.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {brands.map(b => (
            <div key={b} className="flex items-center gap-2 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg px-3 py-2">
              {editing === b ? (
                <>
                  <input value={newName} onChange={e => setNewName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && submitRename()}
                    autoFocus dir="auto"
                    className="input-dark text-xs flex-1" />
                  <button onClick={submitRename} disabled={renameMut.isPending}
                    className="btn-primary text-xs px-3 py-1.5 disabled:opacity-50">ذخیره</button>
                  <button onClick={() => setEditing(null)} className="btn-secondary text-xs px-3 py-1.5">انصراف</button>
                </>
              ) : (
                <>
                  <span className="text-xs font-semibold text-white flex-1" dir="auto">{b}</span>
                  <button onClick={() => { setEditing(b); setNewName(b) }}
                    className="text-gray-steel hover:text-gold p-0.5 transition-colors" title="ویرایش نام برند">
                    <Pencil size={13} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <input value={newBrand} onChange={e => setNewBrand(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && newBrand.trim() && addMut.mutate(newBrand.trim())}
            placeholder="نام برند جدید..."
            dir="auto" className="input-dark text-xs w-full" />
        </div>
        <button onClick={() => addMut.mutate(newBrand.trim())}
          disabled={!newBrand.trim() || addMut.isPending}
          className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 disabled:opacity-50">
          <Plus size={14} /> افزودن برند
        </button>
      </div>
    </div>
  )
}

// ─── پنل کامل ویژگی‌های یک دسته ────────────────────────────────
export default function CategoryFieldsManager({ cat, parentCat = null }) {
  const qc = useQueryClient()
  const [editField, setEditField] = useState(null) // { key, label, choices } — فیلد پایه در حال ویرایش

  const deleteFieldMut = useMutation({
    mutationFn: (id) => api.delete(`/catalog/spec-fields/${id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      toast.success('ویژگی حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف'),
  })

  // تاگل «نمایش در فیلترهای سایت» یک ویژگی سفارشی
  const toggleFilterableMut = useMutation({
    mutationFn: ({ id, is_filterable }) => api.patch(`/catalog/spec-fields/${id}/`, { is_filterable }).then(r => r.data),
    onSuccess: (d) => {
      qc.invalidateQueries(['admin-categories-full'])
      toast.success(d.is_filterable ? 'ویژگی در فیلترهای سایت نمایش داده می‌شود' : 'ویژگی از فیلترهای سایت حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  // تاگل مخفی/نمایان یک فیلد پایه در فرم ویرایش محصول
  const toggleHiddenMut = useMutation({
    mutationFn: ({ key, hide }) => {
      const hidden = new Set(cat.hidden_fields || [])
      hide ? hidden.add(key) : hidden.delete(key)
      return api.patch(`/catalog/categories/admin/${cat.id}/`, { hidden_fields: [...hidden] }).then(r => r.data)
    },
    onSuccess: () => qc.invalidateQueries(['admin-categories-full']),
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  // بازنویسی لیبل/گزینه یک فیلد پایه
  const saveOverrideMut = useMutation({
    mutationFn: ({ key, label, choices }) => {
      const overrides = { ...(cat.field_overrides || {}) }
      overrides[key] = { label, choices }
      return api.patch(`/catalog/categories/admin/${cat.id}/`, { field_overrides: overrides }).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      setEditField(null)
      toast.success('ویژگی به‌روز شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  const resetOverrideMut = useMutation({
    mutationFn: ({ key }) => {
      const overrides = { ...(cat.field_overrides || {}) }
      delete overrides[key]
      return api.patch(`/catalog/categories/admin/${cat.id}/`, { field_overrides: overrides }).then(r => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries(['admin-categories-full'])
      toast.success('به حالت پیش‌فرض برگشت')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })

  // زیردسته هم ویژگی مستقل دارد (مثل تفاوت مشخصات دوربین و دستگاه ضبط) —
  // ویژگی‌های دسته اصلی به ارث می‌رسد و اینجا فقط ویژگی‌های اختصاصی زیردسته مدیریت می‌شود.
  // فیلدهای پایه و برندها فقط روی دسته اصلی مدیریت می‌شوند.
  const isChild = !!parentCat

  return (
    <div>
      {isChild && (
        <div className="text-[11px] text-gray-steel bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg px-3 py-2 mb-4">
          ویژگی‌های دسته اصلی «{parentCat.name}» به این زیردسته هم می‌رسد —
          اینجا فقط ویژگی‌های <b className="text-white">اختصاصی «{cat.name}»</b> را مدیریت می‌کنید
          (برای فیلدهای پایه و برندها، دسته اصلی را انتخاب کنید).
        </div>
      )}

      {/* ویژگی‌های پایه (از مدل — متصل به کاتالوگ) — فقط روی دسته اصلی */}
      {!isChild && (
      <>
      <div className="text-xs font-bold text-gold mb-1">ویژگی‌های پایه «{cat.name}»</div>
      <div className="text-[10px] text-gray-steel mb-3">بخشی از هسته فروشگاه‌اند (فیلتر/جستجو) — فقط می‌توانید از فرم ویرایش محصول مخفی‌شان کنید.</div>
      <div className="space-y-1.5 mb-5">
        {cat.builtin_fields.map(f => {
          const hidden = (cat.hidden_fields || []).includes(f.key)
          const ov = (cat.field_overrides || {})[f.key] || {}
          const label = ov.label || f.label
          const choices = ov.choices ?? f.choices
          const hasOverride = !!(ov.label || ov.choices)

          // حالت ویرایش فیلد
          if (editField?.key === f.key) {
            return (
              <div key={f.key} className="flex flex-wrap items-end gap-2 bg-[var(--color-bg-card)] border border-[var(--color-brand)] rounded-lg px-3 py-2">
                <div>
                  <label className="label text-[10px] mb-1 block">لیبل</label>
                  <input value={editField.label} onChange={e => setEditField(x => ({ ...x, label: e.target.value }))}
                    className="input-dark text-xs w-36" />
                </div>
                {f.field_type === 'select' && (
                  <div className="flex-1 min-w-[160px]">
                    <label className="label text-[10px] mb-1 block">گزینه‌ها (با ویرگول)</label>
                    <input value={editField.choices} onChange={e => setEditField(x => ({ ...x, choices: e.target.value }))}
                      className="input-dark text-xs w-full" />
                  </div>
                )}
                <button onClick={() => saveOverrideMut.mutate({ key: f.key, label: editField.label, choices: editField.choices })}
                  disabled={!editField.label.trim() || saveOverrideMut.isPending}
                  className="btn-primary text-xs px-3 py-1.5 disabled:opacity-50">ذخیره</button>
                <button onClick={() => setEditField(null)} className="btn-secondary text-xs px-3 py-1.5">انصراف</button>
              </div>
            )
          }

          return (
            <div key={f.key} className={`flex items-center gap-3 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg px-3 py-2 ${hidden ? 'opacity-40' : ''}`}>
              <span className="text-xs font-semibold text-white">{label}</span>
              <span className="text-[10px] text-gray-steel font-mono" dir="ltr">{f.key}</span>
              <span className="badge text-[10px]">{FIELD_TYPE_LABEL[f.field_type]}</span>
              {choices && <span className="text-[10px] text-gray-steel">{choices}</span>}
              <span className="mr-auto flex items-center gap-1">
                {hasOverride && (
                  <button onClick={() => resetOverrideMut.mutate({ key: f.key })}
                    className="text-gray-steel hover:text-gold p-0.5 transition-colors" title="بازنشانی به پیش‌فرض">
                    <RotateCcw size={12} />
                  </button>
                )}
                <button onClick={() => setEditField({ key: f.key, label, choices: choices || '' })}
                  className="text-gray-steel hover:text-gold p-0.5 transition-colors" title="ویرایش لیبل/گزینه">
                  <Pencil size={13} />
                </button>
                <button onClick={() => toggleHiddenMut.mutate({ key: f.key, hide: !hidden })}
                  className="text-gray-steel hover:text-gold p-0.5 transition-colors"
                  title={hidden ? 'نمایش در فرم ویرایش' : 'مخفی از فرم ویرایش'}>
                  {hidden ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </span>
            </div>
          )
        })}
      </div>

      <BrandsSection cat={cat} />
      </>
      )}

      <div className="text-xs font-bold text-gold mb-3">ویژگی‌های سفارشی «{cat.name}»</div>

      {cat.spec_fields.length === 0 ? (
        <div className="text-xs text-gray-steel mb-3">هنوز ویژگی‌ای تعریف نشده — از فرم زیر اضافه کنید.</div>
      ) : (
        <div className="space-y-1.5 mb-4">
          {cat.spec_fields.map(f => (
            <div key={f.id} className="flex items-center gap-3 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-white">{f.label}</span>
              <span className="text-[10px] text-gray-steel font-mono" dir="ltr">{f.key}</span>
              <span className="badge text-[10px]">{FIELD_TYPE_LABEL[f.field_type]}</span>
              {f.choices && <span className="text-[10px] text-gray-steel">{f.choices}</span>}
              <span className="mr-auto flex items-center gap-1.5">
                <button onClick={() => toggleFilterableMut.mutate({ id: f.id, is_filterable: !f.is_filterable })}
                  className={`text-[10px] px-2 py-1 rounded-full border transition-colors ${f.is_filterable !== false
                    ? 'border-brand/50 text-brand bg-brand/10'
                    : 'border-white/10 text-gray-steel hover:text-white'}`}
                  title={f.is_filterable !== false ? 'در فیلترهای سایت فعال است — برای حذف کلیک کنید' : 'در فیلترهای سایت نیست — برای افزودن کلیک کنید'}>
                  {f.is_filterable !== false ? '✓ فیلتر سایت' : 'فیلتر سایت'}
                </button>
                <button onClick={() => { if (window.confirm(`ویژگی «${f.label}» حذف شود؟`)) deleteFieldMut.mutate(f.id) }}
                  className="text-red-400 hover:text-red-300 p-0.5" title="حذف ویژگی">
                  <X size={14} />
                </button>
              </span>
            </div>
          ))}
        </div>
      )}

      <AddFieldForm categoryId={cat.id} />
    </div>
  )
}
