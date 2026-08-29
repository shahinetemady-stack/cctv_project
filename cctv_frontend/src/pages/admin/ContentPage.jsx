import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { X, ImagePlus } from 'lucide-react'
import api from '../../services/api'
import { mediaUrl } from '../../utils/media'
import { PageLoader } from '../../components/ui'

const VIDEO_TYPES = [
  ['montaj', 'نصب و راه‌اندازی'],
  ['troubleshooting', 'عیب‌یابی'],
  ['part_selection', 'انتخاب قطعه'],
  ['general', 'عمومی'],
]

const th = { padding: '10px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 12 }
const td = { padding: '10px 12px', borderBottom: '0.5px solid var(--color-border)' }

// ─── مودال ویرایش/ساخت مقاله ───────────────────────────────────
function ArticleEditor({ article, categories, onClose }) {
  const qc = useQueryClient()
  const isNew = !article?.id
  const [form, setForm] = useState({
    title: article?.title || '',
    slug: article?.slug || '',
    category: article?.category || '',
    author: article?.author || '',
    tags: (article?.tags || []).join('، '),
    description: article?.description || '',
    content: article?.content || '',
    is_published: article?.is_published ?? true,
    publish_at: article?.publish_at ? article.publish_at.replace(' ', 'T') : '',
  })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const payload = () => ({
    ...form,
    category: form.category || null,
    tags: form.tags.split(/[,،]/).map(t => t.trim()).filter(Boolean),
    publish_at: form.publish_at ? `${form.publish_at}:00+03:30` : null,
  })

  const saveMut = useMutation({
    mutationFn: (d) => isNew
      ? api.post('/education/admin/articles/', d).then(r => r.data)
      : api.patch(`/education/admin/articles/${article.id}/`, d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-articles'])
      toast.success(isNew ? 'مقاله ساخته شد' : 'مقاله ذخیره شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره'),
  })

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/education/admin/articles/${article.id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-articles'])
      toast.success('مقاله حذف شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف'),
  })

  // ─── تصویر کاور و درج تصویر در متن ────────────────────────────
  const thumbInputRef = useRef(null)
  const inlineInputRef = useRef(null)
  const contentRef = useRef(null)
  const [thumbUrl, setThumbUrl] = useState(article?.thumbnail || null)

  const thumbMut = useMutation({
    mutationFn: (file) => {
      if (file.size > 512 * 1024) toast.warning('حجم کاور بیش از ۵۰۰ کیلوبایت است — لود صفحه و پیش‌نمایش پیام‌رسان کند می‌شود؛ بهتر است فشرده‌اش کنید.')
      const fd = new FormData()
      fd.append('thumbnail', file)
      return api.patch(`/education/admin/articles/${article.id}/`, fd).then(r => r.data)
    },
    onSuccess: (data) => {
      setThumbUrl(data.thumbnail || null)
      qc.invalidateQueries(['admin-articles'])
      toast.success('کاور مقاله به‌روز شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در بارگذاری کاور'),
  })

  const removeThumbMut = useMutation({
    mutationFn: () => api.patch(`/education/admin/articles/${article.id}/`, { remove_thumbnail: true }).then(r => r.data),
    onSuccess: () => {
      setThumbUrl(null)
      qc.invalidateQueries(['admin-articles'])
      toast.success('کاور حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف کاور'),
  })

  const inlineMut = useMutation({
    mutationFn: (file) => {
      if (file.size > 512 * 1024) toast.warning('حجم تصویر بیش از ۵۰۰ کیلوبایت است — لود صفحه کند می‌شود؛ بهتر است فشرده‌اش کنید.')
      const fd = new FormData()
      fd.append('image', file)
      return api.post('/education/admin/upload-image/', fd).then(r => r.data)
    },
    onSuccess: ({ url }) => {
      const tag = `<img src="${url}" alt="" style="max-width:100%;height:auto;border-radius:12px;" />`
      const pos = contentRef.current ? contentRef.current.selectionStart : form.content.length
      set('content', form.content.slice(0, pos) + tag + form.content.slice(pos))
      toast.success('تصویر در متن درج شد — برای اعمال نهایی، مقاله را ذخیره کنید')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در بارگذاری تصویر'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white text-lg">{isNew ? 'مقاله جدید' : 'ویرایش مقاله'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="col-span-2 md:col-span-1">
            <label className="label text-xs mb-1 block">عنوان *</label>
            <input value={form.title} onChange={e => set('title', e.target.value)} className="input-dark text-xs w-full" />
          </div>
          <div className="col-span-2 md:col-span-1">
            <label className="label text-xs mb-1 block">اسلاگ {isNew && <span className="text-gray-steel">(خالی = خودکار)</span>}</label>
            <input value={form.slug} onChange={e => set('slug', e.target.value)} dir="ltr" className="input-dark text-xs w-full" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">دسته‌بندی</label>
            <select value={form.category || ''} onChange={e => set('category', e.target.value ? Number(e.target.value) : null)} className="input-dark text-xs w-full">
              <option value="">بدون دسته</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">نویسنده</label>
            <input value={form.author} onChange={e => set('author', e.target.value)} className="input-dark text-xs w-full" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">تگ‌ها (با ویرگول جدا کنید)</label>
            <input value={form.tags} onChange={e => set('tags', e.target.value)} className="input-dark text-xs w-full" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">خلاصه (meta description)</label>
            <textarea value={form.description} onChange={e => set('description', e.target.value)} rows={2} className="input-dark text-xs w-full" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">تصویر کاور</label>
            <div className="flex items-center gap-3">
              {thumbUrl ? (
                <img src={mediaUrl(thumbUrl)} alt="کاور مقاله"
                  className="w-32 h-20 object-cover rounded-lg border border-[var(--color-border)]" />
              ) : (
                <div className="w-32 h-20 rounded-lg border border-dashed border-[var(--color-border)] flex items-center justify-center text-gray-steel text-[10px]">
                  بدون کاور
                </div>
              )}
              {isNew ? (
                <span className="text-[11px] text-gray-steel">برای بارگذاری کاور، ابتدا مقاله را بسازید</span>
              ) : (
                <>
                  <button type="button" onClick={() => thumbInputRef.current?.click()} disabled={thumbMut.isPending}
                    className="btn-secondary text-xs px-3 py-2 flex items-center gap-1.5 disabled:opacity-50">
                    <ImagePlus size={14} /> {thumbMut.isPending ? 'در حال بارگذاری...' : thumbUrl ? 'تعویض کاور' : 'بارگذاری کاور'}
                  </button>
                  {thumbUrl && (
                    <button type="button" onClick={() => removeThumbMut.mutate()} disabled={removeThumbMut.isPending}
                      className="text-xs px-3 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors disabled:opacity-50">
                      حذف کاور
                    </button>
                  )}
                </>
              )}
            </div>
            <input ref={thumbInputRef} type="file" accept="image/*" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) thumbMut.mutate(f); e.target.value = '' }} />
            <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
              ابعاد پیشنهادی کاور: ۱۲۸۰×۷۲۰ پیکسل (نسبت ۱۶:۹) — فرمت JPG یا WebP — حجم تا ۱۵۰ کیلوبایت. این تصویر در پیش‌نمایش لینک مقاله در پیام‌رسان‌ها هم استفاده می‌شود.
            </p>
          </div>
          <div className="col-span-2">
            <div className="flex items-center justify-between mb-1">
              <label className="label text-xs">محتوا (HTML)</label>
              {!isNew && (
                <button type="button" onClick={() => inlineInputRef.current?.click()} disabled={inlineMut.isPending}
                  className="text-[11px] px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-gray-steel hover:text-white hover:border-[#FBC02D] transition-colors flex items-center gap-1.5 disabled:opacity-50">
                  <ImagePlus size={13} /> {inlineMut.isPending ? 'در حال بارگذاری...' : 'درج تصویر در متن'}
                </button>
              )}
            </div>
            <textarea ref={contentRef} value={form.content} onChange={e => set('content', e.target.value)} rows={12} dir="ltr"
              className="input-dark text-xs w-full font-mono" />
            <input ref={inlineInputRef} type="file" accept="image/*" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) inlineMut.mutate(f); e.target.value = '' }} />
            <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
              تصویر در محل نشانگر متن درج می‌شود؛ متن جایگزین (alt) را بعداً داخل تگ img ویرایش کنید.
              برای حذف تصویر، از لیست «تصاویر داخل متن» در پایین همین باکس دکمه حذف را بزنید.
              ابعاد پیشنهادی تصویر میان‌متن: عرض ۱۲۰۰ پیکسل (حداقل ۸۰۰) — فرمت JPG یا WebP — حجم تا ۲۰۰ کیلوبایت.
            </p>
            {(() => {
              const imgs = [...form.content.matchAll(/<img[^>]*?src="([^"]*)"[^>]*>/g)]
              if (!imgs.length) return null
              return (
                <div className="mt-2 space-y-1.5">
                  <div className="text-[11px] text-gray-steel">تصاویر داخل متن ({Number(imgs.length).toLocaleString('fa-IR')}):</div>
                  {imgs.map((m, i) => (
                    <div key={i} className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] px-2 py-1.5">
                      <img src={mediaUrl(m[1])} alt="" className="w-12 h-8 object-cover rounded shrink-0" />
                      <span className="text-[10px] text-gray-steel truncate flex-1" dir="ltr">{m[1]}</span>
                      <button type="button" onClick={() => set('content', form.content.replace(m[0], ''))}
                        className="text-[10px] px-2 py-1 rounded text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors shrink-0">
                        حذف
                      </button>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
          <label className="col-span-2 flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_published} onChange={e => set('is_published', e.target.checked)}
              className="w-4 h-4 accent-[#FBC02D]" />
            <span className="text-xs text-gray-steel">منتشر شده (در سایت نمایش داده شود)</span>
          </label>
          <div className="col-span-2 md:col-span-1">
            <label className="label text-xs mb-1 block">زمان انتشار برنامه‌ریزی‌شده</label>
            <input type="datetime-local" value={form.publish_at} onChange={e => set('publish_at', e.target.value)} dir="ltr"
              className="input-dark text-xs w-full" />
            <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
              برای پیش‌نویسها: با رسیدن این زمان، هشدار انتشار در تب مقالات نمایش داده می‌شود.
            </p>
          </div>
        </div>
        <div className="flex gap-2 pt-2 border-t border-[var(--color-border)]">
          <button onClick={() => saveMut.mutate(payload())} disabled={!form.title || saveMut.isPending}
            className="btn-primary px-6 py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : isNew ? 'ساخت مقاله' : 'ذخیره تغییرات'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
          {!isNew && (
            confirmDelete ? (
              <div className="mr-auto flex items-center gap-2">
                <span className="text-[11px] text-red-400">مقاله حذف شود؟</span>
                <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                  className="text-xs px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 disabled:opacity-50">
                  {deleteMut.isPending ? '...' : 'بله، حذف کن'}
                </button>
                <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-steel hover:text-white">خیر</button>
              </div>
            ) : (
              <button onClick={() => setConfirmDelete(true)}
                className="mr-auto text-xs px-4 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors">
                🗑 حذف مقاله
              </button>
            )
          )}
        </div>
      </div>
    </div>
  )
}

// ─── مودال ویرایش/ساخت ویدیو ───────────────────────────────────
function VideoEditor({ video, onClose }) {
  const qc = useQueryClient()
  const isNew = !video?.id
  const [form, setForm] = useState({
    title: video?.title || '',
    slug: video?.slug || '',
    video_url: video?.video_url || '',
    video_type: video?.video_type || 'general',
    duration: video?.duration || 0,
    order: video?.order || 0,
    description: video?.description || '',
    is_published: video?.is_published ?? true,
  })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const saveMut = useMutation({
    mutationFn: (d) => isNew
      ? api.post('/education/admin/videos/', d).then(r => r.data)
      : api.patch(`/education/admin/videos/${video.id}/`, d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-videos'])
      toast.success(isNew ? 'ویدیو ساخته شد' : 'ویدیو ذخیره شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره'),
  })

  const deleteMut = useMutation({
    mutationFn: () => api.delete(`/education/admin/videos/${video.id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-videos'])
      toast.success('ویدیو حذف شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white text-lg">{isNew ? 'ویدیوی جدید' : 'ویرایش ویدیو'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">عنوان *</label>
            <input value={form.title} onChange={e => set('title', e.target.value)} className="input-dark text-xs w-full" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">لینک ویدیو (آپارات/یوتیوب) *</label>
            <input value={form.video_url} onChange={e => set('video_url', e.target.value)} dir="ltr" className="input-dark text-xs w-full" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">اسلاگ {isNew && <span className="text-gray-steel">(خالی = خودکار)</span>}</label>
            <input value={form.slug} onChange={e => set('slug', e.target.value)} dir="ltr" className="input-dark text-xs w-full" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">نوع ویدیو</label>
            <select value={form.video_type} onChange={e => set('video_type', e.target.value)} className="input-dark text-xs w-full">
              {VIDEO_TYPES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">مدت (دقیقه)</label>
            <input type="number" min="0" value={form.duration} onChange={e => set('duration', Number(e.target.value))} className="input-dark text-xs w-full" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">ترتیب نمایش</label>
            <input type="number" min="0" value={form.order} onChange={e => set('order', Number(e.target.value))} className="input-dark text-xs w-full" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">توضیحات</label>
            <textarea value={form.description} onChange={e => set('description', e.target.value)} rows={3} className="input-dark text-xs w-full" />
          </div>
          <label className="col-span-2 flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_published} onChange={e => set('is_published', e.target.checked)}
              className="w-4 h-4 accent-[#FBC02D]" />
            <span className="text-xs text-gray-steel">منتشر شده (در سایت نمایش داده شود)</span>
          </label>
        </div>
        <div className="flex gap-2 pt-2 border-t border-[var(--color-border)]">
          <button onClick={() => saveMut.mutate(form)} disabled={!form.title || !form.video_url || saveMut.isPending}
            className="btn-primary px-6 py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : isNew ? 'ساخت ویدیو' : 'ذخیره تغییرات'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
          {!isNew && (
            confirmDelete ? (
              <div className="mr-auto flex items-center gap-2">
                <span className="text-[11px] text-red-400">ویدیو حذف شود؟</span>
                <button onClick={() => deleteMut.mutate()} disabled={deleteMut.isPending}
                  className="text-xs px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 disabled:opacity-50">
                  {deleteMut.isPending ? '...' : 'بله، حذف کن'}
                </button>
                <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-steel hover:text-white">خیر</button>
              </div>
            ) : (
              <button onClick={() => setConfirmDelete(true)}
                className="mr-auto text-xs px-4 py-2 rounded-lg text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors">
                🗑 حذف ویدیو
              </button>
            )
          )}
        </div>
      </div>
    </div>
  )
}

// ─── مودال مدیریت دسته‌بندی مقالات ─────────────────────────────
function ArticleCategoriesModal({ onClose }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const { data: cats = [] } = useQuery({
    queryKey: ['admin-article-categories'],
    queryFn: () => api.get('/education/admin/article-categories/').then(r => r.data),
  })
  const createMut = useMutation({
    mutationFn: () => api.post('/education/admin/article-categories/', { name }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-article-categories'])
      toast.success('دسته اضافه شد')
      setName('')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا'),
  })
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/education/admin/article-categories/${id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['admin-article-categories'])
      toast.success('دسته حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-white text-lg">دسته‌بندی مقالات</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>
        <div className="flex gap-2 mb-4">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="نام دسته جدید..."
            className="input-dark text-xs flex-1"
            onKeyDown={e => e.key === 'Enter' && name.trim() && createMut.mutate()} />
          <button onClick={() => createMut.mutate()} disabled={!name.trim() || createMut.isPending}
            className="btn-primary text-xs px-4 disabled:opacity-50">
            {createMut.isPending ? '...' : '+ افزودن'}
          </button>
        </div>
        <div className="space-y-2">
          {cats.map(c => (
            <div key={c.id} className="flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2">
              <div>
                <span className="text-sm text-white">{c.name}</span>
                <span className="text-[10px] text-gray-steel mr-2" dir="ltr">{c.slug}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-gray-steel">{Number(c.article_count).toLocaleString('fa-IR')} مقاله</span>
                <button onClick={() => deleteMut.mutate(c.id)} disabled={deleteMut.isPending}
                  className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50">حذف</button>
              </div>
            </div>
          ))}
          {cats.length === 0 && <div className="text-center py-6 text-gray-steel text-xs">هنوز دسته‌ای نیست</div>}
        </div>
        <div className="text-[10px] text-[var(--color-text-muted)] mt-3">دسته دارای مقاله قابل حذف نیست — اسلاگ خودکار از نام ساخته می‌شود.</div>
      </div>
    </div>
  )
}

// ─── تب مقالات ──────────────────────────────────────────────────
function ArticlesTab() {
  const [editing, setEditing] = useState(null) // مقاله در حال ویرایش یا 'new'
  const [showCats, setShowCats] = useState(false)
  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['admin-articles'],
    queryFn: () => api.get('/education/admin/articles/').then(r => r.data),
  })
  const { data: categories = [] } = useQuery({
    queryKey: ['admin-article-categories'],
    queryFn: () => api.get('/education/admin/article-categories/').then(r => r.data),
  })

  if (isLoading) return <PageLoader />
  const now = new Date()
  const pubDate = (a) => a.publish_at ? new Date(a.publish_at.replace(' ', 'T') + ':00+03:30') : null
  const isDue = (a) => !a.is_published && pubDate(a) && pubDate(a) <= now
  const due = articles.filter(isDue)
  return (
    <div>
      {due.length > 0 && (
        <div className="card mb-4 p-4 border border-yellow-500/50 bg-yellow-500/10">
          <div className="text-sm font-bold text-yellow-400 mb-2">
            🔔 {due.length.toLocaleString('fa-IR')} مقاله به موعد انتشار رسیده‌اند — بازشان کنید و تیک «منتشر شده» را بزنید:
          </div>
          <ul className="space-y-1">
            {due.map(a => (
              <li key={a.id} className="text-xs">
                <button onClick={() => setEditing(a)} className="text-yellow-300 hover:text-white underline underline-offset-4">{a.title}</button>
                <span className="text-gray-steel mr-2" dir="ltr">({a.publish_at})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex justify-end gap-2 mb-4">
        <button onClick={() => setShowCats(true)} className="btn-secondary text-sm px-4 py-2">دسته‌بندی‌ها</button>
        <button onClick={() => setEditing('new')} className="btn-primary text-sm px-4 py-2">+ مقاله جدید</button>
      </div>
      <div className="card overflow-x-auto">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid var(--color-border-strong)' }}>
              {['#', 'عنوان', 'دسته', 'نویسنده', 'بازدید', 'وضعیت', 'موعد انتشار', 'تاریخ'].map(h => <th key={h} style={th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {articles.map((a, i) => (
              <tr key={a.id} style={{ background: i % 2 ? 'var(--color-brand-softer)' : 'transparent' }}>
                <td style={{ ...td, color: 'var(--color-text-muted)', fontSize: 11, width: 34 }}>{(i + 1).toLocaleString('fa-IR')}</td>
                <td style={{ ...td, fontWeight: 600 }}>
                  <button onClick={() => setEditing(a)} className="hover:text-gold transition-colors text-right">{a.title}</button>
                </td>
                <td style={{ ...td, color: 'var(--color-text-secondary)', fontSize: 11 }}>{a.category_name || '—'}</td>
                <td style={{ ...td, color: 'var(--color-text-secondary)', fontSize: 11 }}>{a.author || '—'}</td>
                <td style={{ ...td, fontSize: 11 }}>{Number(a.views_count || 0).toLocaleString('fa-IR')}</td>
                <td style={td}>
                  <span className={a.is_published ? 'badge-green' : 'badge-red'}>{a.is_published ? 'منتشر شده' : 'پیش‌نویس'}</span>
                </td>
                <td style={{ ...td, fontSize: 11 }} dir="ltr">
                  {a.publish_at
                    ? <span style={isDue(a) ? { color: '#fbbf24', fontWeight: 700 } : { color: 'var(--color-text-secondary)' }}>{a.publish_at}{isDue(a) ? ' ⚠️' : ''}</span>
                    : '—'}
                </td>
                <td style={{ ...td, color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{a.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {articles.length === 0 && <div className="text-center py-12 text-gray-steel text-sm">مقاله‌ای نیست</div>}
      </div>
      {editing && (
        <ArticleEditor
          article={editing === 'new' ? null : editing}
          categories={categories}
          onClose={() => setEditing(null)}
        />
      )}
      {showCats && <ArticleCategoriesModal onClose={() => setShowCats(false)} />}
    </div>
  )
}

// ─── تب ویدیوها ─────────────────────────────────────────────────
function VideosTab() {
  const [editing, setEditing] = useState(null)
  const { data: videos = [], isLoading } = useQuery({
    queryKey: ['admin-videos'],
    queryFn: () => api.get('/education/admin/videos/').then(r => r.data),
  })

  if (isLoading) return <PageLoader />
  return (
    <div>
      <div className="flex justify-end mb-4">
        <button onClick={() => setEditing('new')} className="btn-primary text-sm px-4 py-2">+ ویدیوی جدید</button>
      </div>
      <div className="card overflow-x-auto">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid var(--color-border-strong)' }}>
              {['#', 'عنوان', 'نوع', 'مدت', 'بازدید', 'وضعیت', 'تاریخ'].map(h => <th key={h} style={th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {videos.map((v, i) => (
              <tr key={v.id} style={{ background: i % 2 ? 'var(--color-brand-softer)' : 'transparent' }}>
                <td style={{ ...td, color: 'var(--color-text-muted)', fontSize: 11, width: 34 }}>{(i + 1).toLocaleString('fa-IR')}</td>
                <td style={{ ...td, fontWeight: 600 }}>
                  <button onClick={() => setEditing(v)} className="hover:text-gold transition-colors text-right">{v.title}</button>
                </td>
                <td style={{ ...td, color: 'var(--color-text-secondary)', fontSize: 11 }}>{v.video_type_display}</td>
                <td style={{ ...td, fontSize: 11 }}>{v.duration ? `${Number(v.duration).toLocaleString('fa-IR')} دقیقه` : '—'}</td>
                <td style={{ ...td, fontSize: 11 }}>{Number(v.views_count || 0).toLocaleString('fa-IR')}</td>
                <td style={td}>
                  <span className={v.is_published ? 'badge-green' : 'badge-red'}>{v.is_published ? 'منتشر شده' : 'پیش‌نویس'}</span>
                </td>
                <td style={{ ...td, color: 'var(--color-text-secondary)', fontSize: 11 }} dir="ltr">{v.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {videos.length === 0 && <div className="text-center py-12 text-gray-steel text-sm">ویدیویی نیست</div>}
      </div>
      {editing && (
        <VideoEditor video={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />
      )}
    </div>
  )
}

// ─── صفحه محتوی ─────────────────────────────────────────────────
export default function ContentPage() {
  const [tab, setTab] = useState('articles')
  const tabs = [
    { key: 'articles', label: '📰 مقالات' },
    { key: 'videos',   label: '🎬 ویدیوها' },
  ]
  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">مدیریت محتوی</h1>
      <div className="flex gap-2 mb-6 border-b border-white/10">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${tab === t.key ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'articles' && <ArticlesTab />}
      {tab === 'videos' && <VideosTab />}
    </div>
  )
}
