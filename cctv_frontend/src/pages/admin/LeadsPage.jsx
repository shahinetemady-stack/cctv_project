import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { leadsService } from '../../services/leads'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

const PAGE_SIZE = 50

// حذف فیلترهای خالی برای ارسال به API
function cleanFilters({ q, city, source, status, keyword, category }) {
  return {
    ...(q && { q }), ...(city && { city }), ...(source && { source }),
    ...(status && { status }), ...(keyword && { keyword }), ...(category && { category }),
  }
}

// رنگ بج وضعیت مخاطب
const STATUS_BADGE = {
  new: 'badge',
  contacted: 'badge',
  replied: 'badge badge-gold',
  customer: 'badge badge-success',
  rejected: 'badge badge-danger',
}

const CAMPAIGN_STATUS_LABEL = { draft: 'پیش‌نویس', sending: 'در حال ارسال', done: 'انجام شد', failed: 'ناموفق' }
const CAMPAIGN_STATUS_BADGE = { draft: 'badge', sending: 'badge badge-gold', done: 'badge badge-success', failed: 'badge badge-danger' }

// ─── تب ۱: مخاطبان ──────────────────────────────────────────
function LeadsTab({ meta, filters, setFilters }) {
  const qc = useQueryClient()
  const { q, city, source, status, keyword, category, page } = filters

  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value, ...(key !== 'page' ? { page: 1 } : {}) }))

  // debounce جستجو — qd متن فوری اینپوت است و q در فیلترها با تأخیر به‌روز می‌شود
  const [qd, setQd] = useState(filters.q)
  useEffect(() => {
    const t = setTimeout(() => setFilter('q', qd), 400)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qd])

  const params = { ...cleanFilters(filters), page }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['leads', q, city, source, status, keyword, category, page],
    queryFn: () => leadsService.list(params),
    placeholderData: (prev) => prev,
  })
  const leads = data?.results || []
  const total = data?.count || 0
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const statusMut = useMutation({
    mutationFn: ({ id, value }) => leadsService.update(id, { status: value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
    onError: () => toast.error('خطا در تغییر وضعیت'),
  })

  const delMut = useMutation({
    mutationFn: (id) => leadsService.remove(id),
    onSuccess: () => {
      toast.success('مخاطب حذف شد')
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['leads-meta'] })
    },
    onError: () => toast.error('خطا در حذف'),
  })

  function handleDelete(lead) {
    if (window.confirm(`مخاطب ${lead.phone} حذف شود؟`)) delMut.mutate(lead.id)
  }

  const byStatus = meta?.by_status || {}
  const byCategory = meta?.by_category || {}
  const statusOptions = meta?.statuses || []
  const sourceOptions = meta?.sources || []
  const categoryOptions = meta?.categories || []

  return (
    <div>
      {/* آمار کلی */}
      {meta && (
        <div className="space-y-2 mb-6">
          <div className="flex flex-wrap gap-2">
            <span className="badge badge-gold">کل: {fmt(meta.total)}</span>
            {statusOptions.map(([value, label]) => (
              <button key={value} type="button"
                onClick={() => setFilter('status', status === value ? '' : value)}
                className={`${STATUS_BADGE[value] || 'badge'} cursor-pointer transition-all hover:opacity-80 ${status === value ? 'ring-1 ring-brand' : ''}`}>
                {label}: {fmt(byStatus[value] || 0)}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {categoryOptions.map(([value, label]) => (
              <button key={value} type="button"
                onClick={() => setFilter('category', category === value ? '' : value)}
                className={`badge cursor-pointer transition-all hover:opacity-80 ${category === value ? 'badge-gold ring-1 ring-brand' : ''}`}>
                {label}: {fmt(byCategory[value] || 0)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* نوار فیلتر */}
      <div className="card p-4 mb-6 grid grid-cols-2 md:grid-cols-6 gap-3">
        <input value={qd} onChange={e => setQd(e.target.value)} placeholder="جستجو (موبایل، نام...)"
          className="input-dark text-sm col-span-2 md:col-span-1" />
        <select value={city} onChange={e => setFilter('city', e.target.value)} className="input-dark text-sm">
          <option value="">همه شهرها</option>
          {(meta?.cities || []).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={source} onChange={e => setFilter('source', e.target.value)} className="input-dark text-sm">
          <option value="">همه منابع</option>
          {sourceOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select value={category} onChange={e => setFilter('category', e.target.value)} className="input-dark text-sm">
          <option value="">همه دسته‌ها</option>
          {categoryOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select value={status} onChange={e => setFilter('status', e.target.value)} className="input-dark text-sm">
          <option value="">همه وضعیت‌ها</option>
          {statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select value={keyword} onChange={e => setFilter('keyword', e.target.value)} className="input-dark text-sm">
          <option value="">همه کلیدواژه‌ها</option>
          {(meta?.keywords || []).map(k => <option key={k} value={k}>{k}</option>)}
        </select>
      </div>

      {/* جدول */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-gray-steel text-xs">
                <th className="text-right p-3">موبایل</th>
                <th className="text-right p-3">نام</th>
                <th className="text-right p-3">شهر</th>
                <th className="text-right p-3">منبع</th>
                <th className="text-right p-3">کلیدواژه</th>
                <th className="text-right p-3">وضعیت</th>
                <th className="text-right p-3">پیامک</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={8} className="p-8 text-center text-gray-steel">در حال بارگذاری...</td></tr>
              ) : isError ? (
                <tr><td colSpan={8} className="p-8 text-center text-red-400">خطا در دریافت مخاطبان</td></tr>
              ) : leads.length === 0 ? (
                <tr><td colSpan={8} className="p-8 text-center text-gray-steel">مخاطبی یافت نشد</td></tr>
              ) : leads.map(lead => (
                <tr key={lead.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="p-3 text-white font-mono" dir="ltr">{lead.phone}</td>
                  <td className="p-3 text-white">{lead.name || '—'}</td>
                  <td className="p-3 text-gray-steel">{lead.city || '—'}</td>
                  <td className="p-3">
                    {lead.source_url ? (
                      <a href={lead.source_url} target="_blank" rel="noopener noreferrer"
                        className="badge hover:border-brand hover:text-brand transition-colors"
                        title={lead.source_title || lead.source_url}>
                        {lead.source_display || lead.source} ↗
                      </a>
                    ) : (
                      <span className="badge">{lead.source_display || lead.source || '—'}</span>
                    )}
                  </td>
                  <td className="p-3">
                    {lead.category && lead.category !== 'other' ? (
                      <span className="badge badge-gold text-[11px] block w-fit mb-1">{lead.category_display}</span>
                    ) : null}
                    <span className="text-gray-steel text-xs">{lead.keyword || '—'}</span>
                  </td>
                  <td className="p-3">
                    <select value={lead.status}
                      onChange={e => statusMut.mutate({ id: lead.id, value: e.target.value })}
                      disabled={statusMut.isPending}
                      className="input-dark text-xs py-1 px-2 w-auto">
                      {statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                  </td>
                  <td className="p-3 text-gray-steel">{fmt(lead.sms_count)}</td>
                  <td className="p-3">
                    <button onClick={() => handleDelete(lead)} disabled={delMut.isPending}
                      className="btn-danger text-xs py-1 px-3 disabled:opacity-50">حذف</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {pageCount > 1 && (
          <div className="flex items-center justify-center gap-4 p-4 text-xs">
            <button disabled={page <= 1} onClick={() => setFilter('page', page - 1)}
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-40 transition-all">→ قبلی</button>
            <span className="text-gray-steel">
              صفحه {fmt(page)} از {fmt(pageCount)} — {fmt(total)} مخاطب
            </span>
            <button disabled={page >= pageCount} onClick={() => setFilter('page', page + 1)}
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-40 transition-all">بعدی ←</button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── تب ۲: افزودن و ایمپورت ──────────────────────────────────
function ImportTab({ filters }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ phone: '', name: '', city: '' })
  const [importText, setImportText] = useState('')
  const [importCity, setImportCity] = useState('')
  const [importResult, setImportResult] = useState(null)
  const [exporting, setExporting] = useState(false)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['leads'] })
    qc.invalidateQueries({ queryKey: ['leads-meta'] })
  }

  const createMut = useMutation({
    mutationFn: (payload) => leadsService.create(payload),
    onSuccess: () => {
      toast.success('مخاطب اضافه شد')
      setForm({ phone: '', name: '', city: '' })
      invalidate()
    },
    onError: (e) => {
      if (e.response?.status === 409) toast.error('این شماره قبلاً ثبت شده است')
      else toast.error(e.response?.data?.error || 'خطا در ثبت مخاطب')
    },
  })

  const importMut = useMutation({
    mutationFn: (payload) => leadsService.importText(payload),
    onSuccess: (res) => {
      setImportResult(res)
      setImportText('')
      invalidate()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ایمپورت'),
  })

  async function handleExport() {
    setExporting(true)
    try {
      await leadsService.exportCsv(filters)
      toast.success('فایل CSV دانلود شد')
    } catch {
      toast.error('خطا در دانلود خروجی')
    } finally {
      setExporting(false)
    }
  }

  function handleCreate(e) {
    e.preventDefault()
    if (!form.phone.trim()) return toast.error('شماره موبایل را وارد کنید')
    createMut.mutate({
      phone: form.phone.trim(),
      ...(form.name.trim() && { name: form.name.trim() }),
      ...(form.city.trim() && { city: form.city.trim() }),
    })
  }

  function handleImport() {
    if (!importText.trim()) return toast.error('متن شماره‌ها را وارد کنید')
    importMut.mutate({
      text: importText,
      ...(importCity.trim() && { city: importCity.trim() }),
    })
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* افزودن دستی */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">افزودن دستی مخاطب</h3>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="label">موبایل *</label>
            <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
              className="input-dark text-sm" dir="ltr" placeholder="09123456789" />
          </div>
          <div>
            <label className="label">نام</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="input-dark text-sm" placeholder="اختیاری" />
          </div>
          <div>
            <label className="label">شهر</label>
            <input value={form.city} onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
              className="input-dark text-sm" placeholder="اختیاری" />
          </div>
          <button type="submit" disabled={createMut.isPending} className="btn-gold text-sm w-full py-2.5 disabled:opacity-50">
            {createMut.isPending ? 'در حال ثبت...' : 'افزودن مخاطب'}
          </button>
        </form>
      </div>

      {/* ایمپورت متنی */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">ایمپورت گروهی</h3>
        <label className="label">شماره‌ها — هر خط یک شماره، اختیاری با کاما نام</label>
        <textarea value={importText} onChange={e => setImportText(e.target.value)} rows={8}
          className="input-dark text-sm resize-y font-mono" dir="ltr"
          placeholder={'09123456789,علی رضایی\n09121112222\n09353334444,مغازه تهران'} />
        <div className="mt-3">
          <label className="label">شهر پیش‌فرض برای همه</label>
          <input value={importCity} onChange={e => setImportCity(e.target.value)}
            className="input-dark text-sm" placeholder="اختیاری" />
        </div>
        <button onClick={handleImport} disabled={importMut.isPending}
          className="btn-gold text-sm w-full py-2.5 mt-4 disabled:opacity-50">
          {importMut.isPending ? 'در حال ایمپورت...' : 'ایمپورت'}
        </button>
        {importResult && (
          <div className="mt-4 rounded-lg px-4 py-3 text-sm bg-white/5 flex flex-wrap gap-4">
            <span className="text-emerald-400">{fmt(importResult.created)} ایجاد</span>
            <span className="text-brand">{fmt(importResult.duplicate)} تکراری</span>
            <span className="text-red-400">{fmt(importResult.invalid)} نامعتبر</span>
          </div>
        )}
      </div>

      {/* خروجی */}
      <div className="card p-5 md:col-span-2 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-white">خروجی اکسل / CSV</h3>
          <p className="text-xs text-gray-steel mt-1">خروجی با فیلترهای فعلی تب «مخاطبان» دانلود می‌شود.</p>
        </div>
        <button onClick={handleExport} disabled={exporting} className="btn-ghost text-sm py-2.5 disabled:opacity-50">
          {exporting ? 'در حال آماده‌سازی...' : 'دانلود خروجی CSV'}
        </button>
      </div>
    </div>
  )
}

// ─── تب ۳: کمپین‌ها ─────────────────────────────────────────
function CampaignsTab({ meta }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    name: '', message: '', filter_city: '', filter_source: '', filter_category: '', filter_status: '', filter_keyword: '',
  })
  const [targetPreview, setTargetPreview] = useState(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['leads-campaigns'],
    queryFn: () => leadsService.campaigns(),
  })
  const campaigns = Array.isArray(data) ? data : (data?.results || [])

  const createMut = useMutation({
    mutationFn: (payload) => leadsService.createCampaign(payload),
    onSuccess: (res) => {
      toast.success('کمپین ساخته شد')
      setTargetPreview(res.target_preview ?? null)
      setForm({ name: '', message: '', filter_city: '', filter_source: '', filter_category: '', filter_status: '', filter_keyword: '' })
      qc.invalidateQueries({ queryKey: ['leads-campaigns'] })
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ساخت کمپین'),
  })

  const sendMut = useMutation({
    mutationFn: (id) => leadsService.sendCampaign(id),
    onSuccess: (res) => {
      if (res.error) toast.error(res.error)
      else toast.success(`ارسال شد: ${fmt(res.sent)} — ناموفق: ${fmt(res.failed)}`)
      qc.invalidateQueries({ queryKey: ['leads-campaigns'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ارسال کمپین'),
  })

  function handleCreate(e) {
    e.preventDefault()
    if (!form.name.trim()) return toast.error('نام کمپین را وارد کنید')
    if (!form.message.trim()) return toast.error('متن پیامک را بنویسید')
    setTargetPreview(null)
    createMut.mutate({
      name: form.name.trim(),
      message: form.message.trim(),
      ...(form.filter_city && { filter_city: form.filter_city }),
      ...(form.filter_source && { filter_source: form.filter_source }),
      ...(form.filter_category && { filter_category: form.filter_category }),
      ...(form.filter_status && { filter_status: form.filter_status }),
      ...(form.filter_keyword && { filter_keyword: form.filter_keyword }),
    })
  }

  function handleSend(c) {
    if (window.confirm(`برای ${fmt(c.total_targets)} نفر ارسال شود؟`)) sendMut.mutate(c.id)
  }

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  return (
    <div>
      {/* هشدار ثابت */}
      <div className="rounded-lg px-4 py-3 text-sm bg-brand/10 text-brand mb-6">
        ارسال پیامک تبلیغاتی فقط با خط تبلیغاتی و با متن شامل عبارت لغو مجاز است.
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* فرم ساخت کمپین */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">ساخت کمپین جدید</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="label">نام کمپین *</label>
              <input value={form.name} onChange={set('name')} className="input-dark text-sm" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="label mb-0">متن پیامک *</label>
                <span className="text-[11px] text-gray-steel" dir="ltr">{fmt(form.message.length)} کاراکتر</span>
              </div>
              <textarea value={form.message} onChange={set('message')} rows={4}
                className="input-dark text-sm resize-y" placeholder="متن پیامک..." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">فیلتر شهر</label>
                <select value={form.filter_city} onChange={set('filter_city')} className="input-dark text-sm">
                  <option value="">همه</option>
                  {(meta?.cities || []).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="label">فیلتر منبع</label>
                <select value={form.filter_source} onChange={set('filter_source')} className="input-dark text-sm">
                  <option value="">همه</option>
                  {(meta?.sources || []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="label">فیلتر دسته‌بندی</label>
                <select value={form.filter_category} onChange={set('filter_category')} className="input-dark text-sm">
                  <option value="">همه</option>
                  {(meta?.categories || []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="label">فیلتر وضعیت</label>
                <select value={form.filter_status} onChange={set('filter_status')} className="input-dark text-sm">
                  <option value="">همه</option>
                  {(meta?.statuses || []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="label">فیلتر کلیدواژه</label>
                <select value={form.filter_keyword} onChange={set('filter_keyword')} className="input-dark text-sm">
                  <option value="">همه</option>
                  {(meta?.keywords || []).map(k => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
            </div>
            <button type="submit" disabled={createMut.isPending} className="btn-gold text-sm w-full py-2.5 disabled:opacity-50">
              {createMut.isPending ? 'در حال ساخت...' : 'ساخت کمپین'}
            </button>
          </form>
          {targetPreview !== null && (
            <div className="mt-4 rounded-lg px-4 py-3 text-sm bg-white/5 text-white">
              مخاطبان هدف این کمپین: <span className="text-brand font-bold">{fmt(targetPreview)}</span> نفر
            </div>
          )}
        </div>

        {/* لیست کمپین‌ها */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">کمپین‌ها</h3>
          {isLoading ? (
            <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
          ) : isError ? (
            <div className="rounded-lg px-4 py-3 text-sm bg-red-500/20 text-red-400">خطا در دریافت کمپین‌ها</div>
          ) : campaigns.length === 0 ? (
            <div className="text-center py-10 text-gray-steel text-sm">کمپینی وجود ندارد</div>
          ) : (
            <div className="space-y-3">
              {campaigns.map(c => (
                <div key={c.id} className="rounded-lg border border-white/10 p-4">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <span className="text-sm font-semibold text-white">{c.name}</span>
                    <span className={CAMPAIGN_STATUS_BADGE[c.status] || 'badge'}>
                      {CAMPAIGN_STATUS_LABEL[c.status] || c.status}
                    </span>
                  </div>
                  <div className="text-xs text-gray-steel flex flex-wrap gap-4">
                    <span>ارسال: {fmt(c.sent_count)} از {fmt(c.total_targets)}</span>
                    {c.failed_count > 0 && <span className="text-red-400">ناموفق: {fmt(c.failed_count)}</span>}
                    <span>{c.created_at ? new Date(c.created_at).toLocaleDateString('fa-IR') : ''}</span>
                  </div>
                  {c.status === 'draft' && (
                    <button onClick={() => handleSend(c)} disabled={sendMut.isPending}
                      className="btn-gold text-xs py-1.5 px-4 mt-3 disabled:opacity-50">
                      {sendMut.isPending ? 'در حال ارسال...' : 'ارسال'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── تب ۴: تنظیمات و راهنما ─────────────────────────────────
const SOURCE_GUIDES = [
  {
    key: 'divar_token', source: 'divar', name: 'دیوار', lifetime: 'عمر کوکی: حدود ۳ ساعت — هر بار که خطای «توکن منقضی» دیدی، همین مراحل را تکرار کن',
    steps: [
      'توی مرورگر برو به divar.ir و لاگین کن',
      'کلید F12 را بزن و برو به تب Console',
      'این را تایپ کن و Enter بزن: copy(document.cookie)',
      'برگرد همین‌جا و در کادر زیر بچسبان (Ctrl+V) و ذخیره کن',
    ],
  },
  {
    key: 'sheypoor_token', source: 'sheypoor', name: 'شیپور', lifetime: 'عمر کوکی: حدود ۳ ماه — هر روز ۷ صبح خودکار اجرا می‌شود',
    steps: [
      'توی مرورگر برو به sheypoor.com و لاگین کن',
      'کلید F12 را بزن و برو به تب Application',
      'از منوی سمت چپ: Storage ← Cookies ← روی https://www.sheypoor.com کلیک کن',
      'روی ردیف refresh_token کلیک کن و مقدار کاملش را کپی کن (دابل‌کلیک روی مقدار ← Ctrl+C)',
      'این‌جا در کادر زیر به این شکل بچسبان: refresh_token=مقدار کپی‌شده',
    ],
  },
  {
    key: 'serpapi_key', source: 'google', name: 'گوگل مپ (SerpAPI)', lifetime: 'سهمیه رایگان: ۱۰۰ جستجو در ماه — هر اجرا از پنل ۴۸ جستجو مصرف می‌کند',
    steps: [
      'برو به serpapi.com و با ایمیل (یا اکانت گوگل) ثبت‌نام کن',
      'ایمیل تأیید را باز کن و لینکش را بزن',
      'از Dashboard بخش API Key، کلید را کپی کن',
      'این‌جا در کادر زیر بچسبان و ذخیره کن',
    ],
  },
]

// خط وضعیت آخرین اجرای اسکرپر
function RunStatus({ run }) {
  if (!run) return <div className="text-xs text-gray-steel mb-3">هنوز اجرایی ثبت نشده</div>
  const at = run.finished_at || run.started_at
  const when = at ? new Date(at).toLocaleString('fa-IR') : ''
  if (run.status === 'running') {
    return (
      <div className="text-xs mb-3 flex items-center gap-2 text-brand">
        <span className="inline-block w-2 h-2 rounded-full bg-brand animate-pulse" />
        در حال اجرا... (شروع: {when}) — همین صفحه خودکار به‌روز می‌شود
      </div>
    )
  }
  if (run.status === 'error') {
    return (
      <div className="text-xs mb-3 text-red-400">
        آخرین اجرا خطا خورد ({when}): {run.message || '—'}
        {run.new_count > 0 && ` — ${fmt(run.new_count)} لید قبل از خطا ذخیره شد`}
      </div>
    )
  }
  return (
    <div className="text-xs mb-3 text-emerald-400">
      آخرین اجرا موفق ({when}): {fmt(run.new_count)} لید جدید
      {run.seen_count > 0 && `، ${fmt(run.seen_count)} تکراری/رد شده`}
    </div>
  )
}

function SettingsTab() {
  const qc = useQueryClient()
  const [values, setValues] = useState({ divar_token: '', sheypoor_token: '', serpapi_key: '' })

  const { data: settings, isLoading } = useQuery({
    queryKey: ['leads-settings'],
    queryFn: () => leadsService.getSettings(),
    // وقتی اسکرپری در حال اجراست هر ۱۵ ثانیه وضعیت را تازه کن
    refetchInterval: (query) =>
      Object.values(query.state.data?.last_runs || {}).some(r => r?.status === 'running') ? 15000 : false,
  })

  const saveMut = useMutation({
    mutationFn: (payload) => leadsService.saveSettings(payload),
    onSuccess: () => {
      toast.success('ذخیره شد')
      qc.invalidateQueries({ queryKey: ['leads-settings'] })
    },
    onError: () => toast.error('خطا در ذخیره'),
  })

  const runMut = useMutation({
    mutationFn: (source) => leadsService.runScraper(source),
    onSuccess: (res) => {
      toast.success(res.message || 'اجرا شروع شد')
      qc.invalidateQueries({ queryKey: ['leads-settings'] })
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در شروع اجرا'),
  })

  function handleSave(key) {
    const value = values[key].trim()
    if (!value) return toast.error('اول مقدار را در کادر بچسبان')
    saveMut.mutate({ [key]: value })
    setValues(v => ({ ...v, [key]: '' }))
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg px-4 py-3 text-sm bg-brand/10 text-brand">
        اسکرپرها روی سرور اجرا می‌شوند؛ تو این صفحه فقط توکن‌ها را می‌گذاری. شیپور هر روز ۷ صبح خودکار اجرا می‌شود؛ دیوار و گوگل را با دکمه «اجرای الان» هر وقت خواستی شروع کن.
      </div>
      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : SOURCE_GUIDES.map(g => {
        const isSet = settings?.[`${g.key}_set`]
        const mask = settings?.[`${g.key}_mask`]
        const lastRun = settings?.last_runs?.[g.source]
        const running = lastRun?.status === 'running'
        return (
          <div key={g.key} className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">{g.name}</h3>
              {isSet ? (
                <span className="badge badge-success" dir="ltr">فعال {mask}</span>
              ) : (
                <span className="badge badge-danger">تنظیم نشده</span>
              )}
            </div>
            <div className="rounded-lg bg-white/5 p-4 mb-4">
              <div className="text-xs text-brand mb-2">{g.lifetime}</div>
              <ol className="text-sm text-gray-steel space-y-1.5 list-decimal pr-5">
                {g.steps.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </div>
            <RunStatus run={lastRun} />
            <div className="flex gap-2">
              <input value={values[g.key]}
                onChange={e => setValues(v => ({ ...v, [g.key]: e.target.value }))}
                className="input-dark text-sm font-mono" dir="ltr"
                placeholder={isSet ? 'مقدار جدید را این‌جا بچسبان تا جایگزین شود' : 'این‌جا بچسبان...'} />
              <button onClick={() => handleSave(g.key)} disabled={saveMut.isPending}
                className="btn-gold text-sm py-2 px-6 whitespace-nowrap disabled:opacity-50">
                ذخیره
              </button>
              <button onClick={() => runMut.mutate(g.source)}
                disabled={runMut.isPending || running || !isSet}
                title={!isSet ? 'اول توکن را تنظیم کن' : ''}
                className="btn-ghost text-sm py-2 px-6 whitespace-nowrap disabled:opacity-50">
                {running ? 'در حال اجرا...' : 'اجرای الان'}
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── صفحه اصلی ───────────────────────────────────────────────
const TABS = [
  { key: 'leads', label: 'مخاطبان' },
  { key: 'import', label: 'افزودن و ایمپورت' },
  { key: 'campaigns', label: 'کمپین‌ها' },
  { key: 'settings', label: 'تنظیمات و راهنما' },
]

export default function LeadsPage() {
  const [tab, setTab] = useState('leads')
  // فیلترها اینجا نگه داشته می‌شوند تا دکمه خروجی CSV در تب ایمپورت هم با همین فیلترها کار کند
  const [filters, setFilters] = useState({ q: '', city: '', source: '', status: '', keyword: '', category: '', page: 1 })

  const { data: meta } = useQuery({
    queryKey: ['leads-meta'],
    queryFn: () => leadsService.meta(),
  })

  return (
    <div className="container-main py-8">
      <h1 className="font-display font-bold text-2xl text-white mb-6">مخاطبان تبلیغاتی</h1>

      {/* تب‌ها */}
      <div className="flex gap-2 mb-6 border-b border-white/10 pb-3">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={tab === t.key ? 'btn-gold text-sm py-2 px-5' : 'btn-ghost text-sm py-2 px-5'}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'leads' && <LeadsTab meta={meta} filters={filters} setFilters={setFilters} />}
      {tab === 'import' && <ImportTab filters={cleanFilters(filters)} />}
      {tab === 'campaigns' && <CampaignsTab meta={meta} />}
      {tab === 'settings' && <SettingsTab />}
    </div>
  )
}
