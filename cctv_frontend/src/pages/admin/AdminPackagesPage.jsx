import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Search, X, Package, Upload, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../../services/api'
import { mediaUrl } from '../../utils/media'
import { formatPrice, formatNumber } from '../../utils/format'
import { PageLoader } from '../../components/ui'
import CharCount from '../../components/ui/CharCount'

// ─── هدر مشترک بخش‌ها (همان سبک صفحه محصولات) ────────────────
const SectionTitle = ({ children }) => (
  <div className="text-xs font-bold text-gold mb-2 flex items-center gap-2">
    <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
    {children}
  </div>
)

const EMPTY_FORM = {
  name: '', description: '', discount_percent: '0', min_quantity: '1',
  is_active: true, is_featured: false,
  meta_title: '', meta_description: '', keywords: '', geo_tags: '',
}

// ─── ویرایشگر اقلام پکیج (جستجوی debounce‌شده محصول) ─────────
function ItemsEditor({ items, setItems }) {
  const [q, setQ] = useState('')
  const [dq, setDq] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDq(q), 300)
    return () => clearTimeout(t)
  }, [q])

  const { data: matches = [], isFetching } = useQuery({
    queryKey: ['pkg-item-search', dq],
    queryFn: () => api.get('/catalog/products/', { params: { search: dq, page_size: 50 } })
      .then(r => r.data.results || []),
    enabled: open,
  })

  // انتخاب محصول → واریانت‌هایش از endpoint ادمین گرفته می‌شود (برای قیمت زنده)
  const add = async (p) => {
    setQ(''); setDq('')
    try {
      const detail = await api.get(`/catalog/products/admin/${p.id}/`).then(r => r.data)
      const variants = (detail.variants || []).filter(v => v.is_active)
      if (!variants.length) { toast.error('این محصول واریانت فعالی ندارد'); return }
      const v0 = variants[0]
      setItems(list => [...list, {
        product_id: p.id, product_name: p.name, variants,
        variant_id: v0.id, sku: v0.sku, unit_price: v0.final_price, quantity: 1,
      }])
    } catch {
      toast.error('خطا در دریافت واریانت‌های محصول')
    }
  }

  const setVariant = (idx, variantId) => {
    setItems(list => list.map((it, i) => {
      if (i !== idx) return it
      const v = it.variants.find(x => x.id === Number(variantId))
      return v ? { ...it, variant_id: v.id, sku: v.sku, unit_price: v.final_price } : it
    }))
  }
  const setQty = (idx, qty) =>
    setItems(list => list.map((it, i) => i === idx ? { ...it, quantity: Math.max(1, Number(qty) || 1) } : it))
  const remove = (idx) => setItems(list => list.filter((_, i) => i !== idx))

  return (
    <div className="mb-5">
      <SectionTitle>اقلام پکیج</SectionTitle>

      {items.length > 0 && (
        <div className="space-y-2 mb-3">
          {items.map((it, idx) => (
            <div key={idx} className="flex items-center gap-2 flex-wrap rounded-lg border border-[var(--color-border)] bg-black/20 px-3 py-2">
              <span className="text-xs flex-1 min-w-[140px]">{it.product_name}</span>
              {it.variants.length > 1 ? (
                <select value={it.variant_id} onChange={e => setVariant(idx, e.target.value)}
                  className="input-dark text-[11px] w-36">
                  {it.variants.map(v => (
                    <option key={v.id} value={v.id}>
                      {v.sku}{v.name_suffix ? ` — ${v.name_suffix}` : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-[10px] text-gray-steel" dir="ltr">{it.sku}</span>
              )}
              <input type="number" min="1" value={it.quantity} onChange={e => setQty(idx, e.target.value)}
                className="input-dark text-[11px] w-16 text-center" dir="ltr" title="تعداد" />
              <span className="text-[10px] text-gray-steel w-24 text-left" dir="ltr">
                {formatNumber(it.unit_price * it.quantity)}
              </span>
              <button onClick={() => remove(idx)} className="text-gray-steel hover:text-red-400 transition-colors" title="حذف">
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="relative">
        <Search size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
        <input value={q} onChange={e => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          placeholder="جستجوی محصول برای افزودن به پکیج..."
          className="input-dark text-xs w-full" style={{ paddingRight: '2rem' }} />
        {open && (matches.length > 0 || isFetching) && (
          <div className="absolute z-10 mt-1 w-full card p-1.5 max-h-48 overflow-y-auto">
            {isFetching && matches.length === 0 && (
              <div className="text-[11px] text-gray-steel px-2 py-1.5">در حال بارگذاری...</div>
            )}
            {matches.map(p => (
              <button key={p.id} onClick={() => add(p)}
                className="w-full text-right text-xs px-2.5 py-2 rounded-lg hover:bg-[var(--color-brand-softer)] transition-colors">
                {p.name}
              </button>
            ))}
            {!isFetching && matches.length === 0 && (
              <div className="text-[11px] text-gray-steel px-2 py-1.5">موردی یافت نشد</div>
            )}
          </div>
        )}
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">
        اقلام با دکمه «ذخیره» همراه پکیج ذخیره می‌شوند. پکیج خالی از قلم هم مجاز است.
      </div>
    </div>
  )
}

// ─── بخش تصویر پکیج ──────────────────────────────────────────
function ImageSection({ packageId, imageUrl, pendingFile, setPendingFile }) {
  const qc = useQueryClient()
  const [pending, setPending] = useState(false)
  const [preview, setPreview] = useState(null)

  const shown = preview || (imageUrl ? mediaUrl(imageUrl) : null)

  const upload = async (file) => {
    if (!file) return
    if (!packageId) {
      // پکیج هنوز ساخته نشده — فایل نگه داشته می‌شود و بعد از ساخت آپلود می‌شود
      setPendingFile(file)
      setPreview(URL.createObjectURL(file))
      return
    }
    setPending(true)
    try {
      const fd = new FormData()
      fd.append('image', file)
      await api.post(`/catalog/packages/admin/${packageId}/image/`, fd)
      qc.invalidateQueries(['admin-packages'])
      qc.invalidateQueries(['admin-package', packageId])
      toast.success('تصویر پکیج آپلود شد')
    } catch (e) {
      toast.error(e.response?.data?.error || 'خطا در آپلود تصویر')
    } finally {
      setPending(false)
    }
  }

  const clear = async () => {
    if (!packageId) { setPendingFile(null); setPreview(null); return }
    setPending(true)
    try {
      await api.delete(`/catalog/packages/admin/${packageId}/image/`)
      qc.invalidateQueries(['admin-packages'])
      qc.invalidateQueries(['admin-package', packageId])
      toast.success('تصویر حذف شد')
    } catch {
      toast.error('خطا در حذف تصویر')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mb-5">
      <SectionTitle>تصویر پکیج</SectionTitle>
      <div className="flex items-center gap-3">
        {shown ? (
          <div className="relative">
            <img src={shown} alt="تصویر پکیج" className="w-24 h-24 object-cover rounded-xl bg-white/5" />
            <button onClick={clear} disabled={pending}
              className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-red-500/80 text-white flex items-center justify-center hover:bg-red-500 disabled:opacity-50"
              title="حذف تصویر">
              <X size={12} />
            </button>
          </div>
        ) : (
          <div className="w-24 h-24 rounded-xl bg-white/5 flex items-center justify-center text-gray-steel">
            <Package size={24} className="opacity-40" />
          </div>
        )}
        <label className={`btn-secondary text-xs px-3 py-2 cursor-pointer inline-flex items-center gap-1.5 ${pending ? 'opacity-50 pointer-events-none' : ''}`}>
          <Upload size={13} />
          {pending ? 'در حال آپلود...' : shown ? 'تعویض تصویر' : 'آپلود تصویر'}
          <input type="file" accept="image/*" className="hidden"
            onChange={e => { upload(e.target.files?.[0]); e.target.value = '' }} />
        </label>
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] mt-1">
        ابعاد پیشنهادی: ۱۶۰۰×۱۰۰۰ پیکسل (نسبت ۱۶:۱۰) — فرمت JPG یا WebP.
      </div>
      {!packageId && pendingFile && (
        <div className="text-[10px] text-[var(--color-text-muted)] mt-1">تصویر بعد از ساخت پکیج آپلود می‌شود.</div>
      )}
    </div>
  )
}

// ─── مودال ساخت/ویرایش پکیج ──────────────────────────────────
function PackageEditor({ packageId, onClose }) {
  const qc = useQueryClient()
  const isNew = !packageId
  const [form, setForm] = useState(isNew ? EMPTY_FORM : null)
  const [items, setItems] = useState([])
  const [imageUrl, setImageUrl] = useState(null)
  const [pendingFile, setPendingFile] = useState(null)
  const [seoOpen, setSeoOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: pkg, isLoading } = useQuery({
    queryKey: ['admin-package', packageId],
    queryFn: () => api.get(`/catalog/packages/admin/${packageId}/`).then(r => r.data),
    enabled: !isNew,
  })

  // مقداردهی فقط یک‌بار — همان الگوی ProductEditor (refetch نباید ویرایش‌ها را بپوشاند)
  useEffect(() => {
    if (pkg) {
      setForm(f => f ?? {
        name: pkg.name || '', description: pkg.description || '',
        discount_percent: String(parseFloat(pkg.discount_percent || 0)),
        min_quantity: String(pkg.min_quantity || 1),
        is_active: !!pkg.is_active, is_featured: !!pkg.is_featured,
        meta_title: pkg.meta_title || '', meta_description: pkg.meta_description || '',
        keywords: pkg.keywords || '', geo_tags: pkg.geo_tags || '',
      })
      setItems(list => list.length ? list : (pkg.items_detail || []).map(it => ({
        product_id: it.product_id, product_name: it.product_name,
        variants: [{ id: it.variant_id, sku: it.sku, final_price: it.unit_price }],
        variant_id: it.variant_id, sku: it.sku, unit_price: it.unit_price, quantity: it.quantity,
      })))
      setImageUrl(u => u ?? pkg.image)
    }
  }, [pkg])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  // پیش‌نمایش زنده قیمت بر اساس اقلام فعلی فرم
  const discount = Math.min(100, Math.max(0, parseFloat(form?.discount_percent) || 0))
  const liveOriginal = items.reduce((s, it) => s + (it.unit_price || 0) * it.quantity, 0)
  const liveFinal = Math.ceil(liveOriginal * (1 - discount / 100))

  const saveMut = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        discount_percent: String(discount),
        min_quantity: Math.max(1, Number(form.min_quantity) || 1),
        items: items.map(it => ({ variant_id: it.variant_id, quantity: it.quantity })),
      }
      const saved = isNew
        ? await api.post('/catalog/packages/admin/', payload).then(r => r.data)
        : await api.patch(`/catalog/packages/admin/${packageId}/`, payload).then(r => r.data)
      // آپلود تصویر معلق بعد از ساخت پکیج جدید
      if (isNew && pendingFile) {
        const fd = new FormData()
        fd.append('image', pendingFile)
        await api.post(`/catalog/packages/admin/${saved.id}/image/`, fd)
      }
      return saved
    },
    onSuccess: () => {
      qc.invalidateQueries(['admin-packages'])
      if (packageId) qc.invalidateQueries(['admin-package', packageId])
      toast.success(isNew ? 'پکیج ساخته شد' : 'پکیج ذخیره شد')
      onClose()
    },
    onError: (e) => {
      const d = e.response?.data
      const first = d && typeof d === 'object' ? Object.entries(d)[0] : null
      toast.error(first ? `${first[0]}: ${[].concat(first[1])[0]}` : (e.message || 'خطا در ذخیره'))
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/catalog/packages/admin/${packageId}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-packages'])
      toast.success('پکیج حذف شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف پکیج'),
  })

  const SEO_HINTS = {
    meta_title: '۵۰–۶۰ کاراکتر — عنوان آبی لینک در نتایج گوگل؛ نام پکیج + فایده اصلی',
    meta_description: 'حداکثر ۱۶۰ کاراکتر — متن خاکستری زیر عنوان در گوگل؛ فایده اصلی + میزان تخفیف',
    keywords: 'با ویرگول جدا کن — مثلاً: پکیج دوربین مداربسته، پکیج نظارتی، خرید پکیج دوربین',
    geo_tags: 'شهر/مناطق هدف فروش با ویرگول — مثلاً: تهران، کرج، البرز',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white text-lg">{isNew ? 'پکیج جدید' : 'ویرایش پکیج'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>

        {!isNew && (isLoading || !form) ? <PageLoader /> : form && (
          <>
            {/* اطلاعات اصلی */}
            <div className="mb-5">
              <SectionTitle>اطلاعات اصلی</SectionTitle>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="label text-xs mb-1 block">نام پکیج *</label>
                  <input value={form.name} onChange={e => set('name', e.target.value)}
                    className="input-dark text-xs w-full" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">تخفیف (٪)</label>
                  <input type="number" min="0" max="100" step="0.01" dir="ltr"
                    value={form.discount_percent} onChange={e => set('discount_percent', e.target.value)}
                    className="input-dark text-xs w-full" />
                </div>
                <div>
                  <label className="label text-xs mb-1 block">حداقل تعداد سفارش</label>
                  <input type="number" min="1" dir="ltr"
                    value={form.min_quantity} onChange={e => set('min_quantity', e.target.value)}
                    className="input-dark text-xs w-full" />
                </div>
                <div className="col-span-2 md:col-span-3">
                  <label className="label text-xs mb-1 block">توضیحات</label>
                  <textarea value={form.description} onChange={e => set('description', e.target.value)}
                    rows={3} className="input-dark text-xs w-full" />
                </div>
                <label className="flex items-center gap-2 cursor-pointer mt-2">
                  <input type="checkbox" checked={form.is_active} onChange={e => set('is_active', e.target.checked)}
                    className="w-4 h-4 accent-[#FBC02D]" />
                  <span className="text-xs text-gray-steel">فعال (نمایش در فروشگاه)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer mt-2">
                  <input type="checkbox" checked={form.is_featured} onChange={e => set('is_featured', e.target.checked)}
                    className="w-4 h-4 accent-[#FBC02D]" />
                  <span className="text-xs text-gray-steel">پکیج ویژه</span>
                </label>
              </div>
            </div>

            <ItemsEditor items={items} setItems={setItems} />

            {/* پیش‌نمایش زنده قیمت */}
            <div className="mb-5 rounded-lg border border-[var(--color-border)] bg-black/20 px-4 py-3 flex items-center gap-6 flex-wrap text-xs">
              <span className="text-gray-steel">قیمت اصلی: <b className="text-white">{formatPrice(liveOriginal)}</b></span>
              <span className="text-gray-steel">با تخفیف {formatNumber(discount)}٪: <b className="text-gold">{formatPrice(liveFinal)}</b></span>
              <span className="text-green-400">صرفه‌جویی: {formatPrice(liveOriginal - liveFinal)}</span>
            </div>

            <ImageSection packageId={packageId} imageUrl={imageUrl}
              pendingFile={pendingFile} setPendingFile={setPendingFile} />

            {/* سئو — تاشو */}
            <div className="mb-5">
              <button onClick={() => setSeoOpen(o => !o)}
                className="w-full flex items-center justify-between text-xs font-bold text-gold mb-2">
                <span className="flex items-center gap-2">
                  <span className="w-1 h-3 rounded-full" style={{ background: 'var(--gradient-gold)' }} />
                  سئو و جغرافیا (SEO/GEO)
                </span>
                {seoOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {seoOpen && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <label className="label text-xs mb-1 block">عنوان متا (Meta Title)</label>
                      <input value={form.meta_title} onChange={e => set('meta_title', e.target.value)}
                        className="input-dark text-xs w-full" />
                      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">{SEO_HINTS.meta_title}</div>
                      <CharCount value={form.meta_title} min={50} max={60} />
                    </div>
                    <div className="col-span-2">
                      <label className="label text-xs mb-1 block">توضیح متا (Meta Description)</label>
                      <textarea value={form.meta_description} onChange={e => set('meta_description', e.target.value)}
                        rows={2} className="input-dark text-xs w-full" />
                      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">{SEO_HINTS.meta_description}</div>
                      <CharCount value={form.meta_description} min={70} max={160} />
                    </div>
                    <div>
                      <label className="label text-xs mb-1 block">کلمات کلیدی</label>
                      <input value={form.keywords} onChange={e => set('keywords', e.target.value)}
                        className="input-dark text-xs w-full" />
                      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">{SEO_HINTS.keywords}</div>
                    </div>
                    <div>
                      <label className="label text-xs mb-1 block">شهرهای هدف (GEO)</label>
                      <input value={form.geo_tags} onChange={e => set('geo_tags', e.target.value)}
                        className="input-dark text-xs w-full" />
                      <div className="text-[10px] text-[var(--color-text-muted)] mt-1 leading-relaxed">{SEO_HINTS.geo_tags}</div>
                    </div>
                  </div>
                  {pkg?.slug && (
                    <div className="text-[10px] text-[var(--color-text-muted)] mt-2 leading-relaxed border-t border-white/5 pt-2">
                      آدرس پکیج: <span className="font-mono text-brand" dir="ltr">/packages/{pkg.slug}</span>
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="flex gap-2 pt-2 border-t border-[var(--color-border)]">
              <button onClick={() => saveMut.mutate()} disabled={!form.name.trim() || saveMut.isPending}
                className="btn-primary px-6 py-2.5 disabled:opacity-50">
                {saveMut.isPending ? 'در حال ذخیره...' : isNew ? 'ساخت پکیج' : 'ذخیره تغییرات'}
              </button>
              <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
              {!isNew && (confirmDelete ? (
                <div className="mr-auto flex items-center gap-2">
                  <span className="text-[11px] text-red-400">پکیج برای همیشه حذف شود؟</span>
                  <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                    className="text-xs px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 disabled:opacity-50">
                    {deleteMut.isPending ? '...' : 'بله، حذف کن'}
                  </button>
                  <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-steel hover:text-white">خیر</button>
                </div>
              ) : (
                <button onClick={() => setConfirmDelete(true)}
                  className="mr-auto text-xs px-4 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors">
                  🗑 حذف پکیج
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─── صفحه مدیریت پکیج‌ها ─────────────────────────────────────
export default function AdminPackagesPage() {
  const [editing, setEditing] = useState(null)   // id پکیج در حال ویرایش
  const [creating, setCreating] = useState(false)

  const { data: packages = [], isLoading } = useQuery({
    queryKey: ['admin-packages'],
    queryFn: () => api.get('/catalog/packages/admin/').then(r => r.data.results || r.data || []),
  })

  return (
    <div className="container-main py-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="font-display font-bold text-2xl text-white">مدیریت پکیج‌ها</h1>
        <button onClick={() => setCreating(true)} className="btn-primary text-sm px-5 py-2.5">
          + پکیج جدید
        </button>
      </div>

      {isLoading ? <PageLoader /> : packages.length === 0 ? (
        <div className="text-center py-12 text-gray-steel text-sm">
          <Package size={36} className="mx-auto mb-3 opacity-40" />
          پکیجی وجود ندارد — با «+ پکیج جدید» اولین پکیج را بسازید
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {packages.map(p => (
            <button key={p.id} onClick={() => setEditing(p.id)}
              className="card p-4 text-right hover:border-gold/40 transition-colors">
              <div className="flex items-start gap-3 mb-3">
                {p.image ? (
                  <img src={mediaUrl(p.image)} alt={p.name}
                    className="w-16 h-16 object-cover rounded-xl bg-white/5 flex-shrink-0" />
                ) : (
                  <div className="w-16 h-16 rounded-xl bg-white/5 flex items-center justify-center text-gray-steel flex-shrink-0">
                    <Package size={22} className="opacity-40" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-white text-sm leading-6 line-clamp-2">{p.name}</div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-gray-steel">{formatNumber(p.items_count)} قلم</span>
                    {Number(p.discount_percent) > 0 && (
                      <span className="badge-gold badge">{formatNumber(parseFloat(p.discount_percent))}٪ تخفیف</span>
                    )}
                    <span className={p.is_active ? 'badge-green' : 'badge-red'}>
                      {p.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-[11px] space-y-1 border-t border-white/5 pt-2">
                <div className="flex justify-between">
                  <span className="text-gray-steel">قیمت اصلی</span>
                  <span className="text-gray-steel line-through">{formatPrice(p.original_price)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-steel">قیمت پکیج</span>
                  <span className="text-gold font-bold">{formatPrice(p.final_price)}</span>
                </div>
                {p.savings > 0 && (
                  <div className="flex justify-between">
                    <span className="text-green-400">صرفه‌جویی</span>
                    <span className="text-green-400">{formatPrice(p.savings)}</span>
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {creating && <PackageEditor packageId={null} onClose={() => setCreating(false)} />}
      {editing && <PackageEditor packageId={editing} onClose={() => setEditing(null)} />}
    </div>
  )
}
