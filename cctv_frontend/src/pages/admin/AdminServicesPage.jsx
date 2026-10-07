import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, X, Check, AlertTriangle, RefreshCw } from 'lucide-react'
import api from '../../services/api'
import { formatDate, todayTehran } from '../../utils/date'

const CATEGORIES = [
  ['domain', 'دامنه'],
  ['server', 'سرور'],
  ['cdn', 'CDN و امنیت'],
  ['sms', 'پیامک'],
  ['email', 'ایمیل'],
  ['ai', 'هوش مصنوعی / API'],
  ['other', 'سایر'],
]

const EMPTY = {
  name: '', category: 'domain', provider: '', account: '',
  expire_date: '', renew_cost: '', warn_days: 30, auto_renew: false, note: '', is_active: true,
}

function fmtDays(n) { return Number(n).toLocaleString('fa-IR') }

// رنگ وضعیت بر اساس روزهای باقی‌مانده
function statusOf(s) {
  if (s.days_left < 0) return { label: `منقضی شده (${fmtDays(-s.days_left)} روز پیش)`, color: '#FF3B3B' }
  if (s.days_left <= 7) return { label: `${fmtDays(s.days_left)} روز مانده`, color: '#FF3B3B' }
  if (s.days_left <= s.warn_days) return { label: `${fmtDays(s.days_left)} روز مانده`, color: '#FFB020' }
  return { label: `${fmtDays(s.days_left)} روز مانده`, color: '#00C896' }
}

// ─── فرم افزودن/ویرایش ────────────────────────────────────────────
function ServiceEditor({ service, onClose }) {
  const qc = useQueryClient()
  const [f, setF] = useState(service ? { ...EMPTY, ...service } : EMPTY)
  const set = (k, v) => setF(p => ({ ...p, [k]: v }))

  const saveMut = useMutation({
    mutationFn: (d) => service?.id
      ? api.patch(`/core/services/${service.id}/`, d).then(r => r.data)
      : api.post('/core/services/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['services'])
      qc.invalidateQueries(['dashboard'])
      toast.success('سرویس ذخیره شد')
      onClose()
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="card p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">{service ? 'ویرایش سرویس' : 'سرویس جدید'}</h2>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={20} /></button>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="label text-xs mb-1 block">نام سرویس *</label>
            <input value={f.name} onChange={e => set('name', e.target.value)} className="input text-sm"
              placeholder="مثلاً: دامنه doorbinkar.com" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">دسته</label>
            <select value={f.category} onChange={e => set('category', e.target.value)} className="input text-sm">
              {CATEGORIES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">ارائه‌دهنده</label>
            <input value={f.provider} onChange={e => set('provider', e.target.value)} className="input text-sm"
              placeholder="مثلاً: ابرآروان" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">حساب / شناسه</label>
            <input value={f.account} onChange={e => set('account', e.target.value)} className="input text-sm"
              placeholder="یوزرنیم یا شماره حساب" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">تاریخ انقضا *</label>
            <input type="date" value={f.expire_date} onChange={e => set('expire_date', e.target.value)}
              dir="ltr" className="input text-sm text-left" min={todayTehran()} />
          </div>
          <div>
            <label className="label text-xs mb-1 block">هزینه تمدید</label>
            <input value={f.renew_cost} onChange={e => set('renew_cost', e.target.value)} className="input text-sm"
              placeholder="مثلاً: ۱۵ دلار / ۲ میلیون تومان" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">هشدار از چند روز قبل</label>
            <input type="number" min="1" max="365" value={f.warn_days}
              onChange={e => set('warn_days', e.target.value)} dir="ltr" className="input text-sm text-left" />
          </div>
          <div className="flex items-end gap-4 pb-1">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-steel hover:text-white">
              <div onClick={() => set('auto_renew', !f.auto_renew)}
                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${f.auto_renew ? 'bg-brand border-brand' : 'border-white/20'}`}>
                {f.auto_renew && <Check size={12} strokeWidth={3} className="text-white" />}
              </div>
              تمدید خودکار
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-steel hover:text-white">
              <div onClick={() => set('is_active', !f.is_active)}
                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${f.is_active ? 'bg-brand border-brand' : 'border-white/20'}`}>
                {f.is_active && <Check size={12} strokeWidth={3} className="text-white" />}
              </div>
              فعال
            </label>
          </div>
        </div>

        <div className="mb-4">
          <label className="label text-xs mb-1 block">یادداشت</label>
          <textarea value={f.note} onChange={e => set('note', e.target.value)} rows={2}
            className="input text-sm w-full" placeholder="مثلاً: لینک پنل تمدید، نکته‌های خاص..." />
        </div>

        <div className="flex gap-3">
          <button onClick={() => saveMut.mutate(f)} disabled={!f.name || !f.expire_date || saveMut.isPending}
            className="btn-primary flex-1 py-2.5 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره'}
          </button>
          <button onClick={onClose} className="btn-secondary px-6 py-2.5">انصراف</button>
        </div>
      </div>
    </div>
  )
}

// ─── صفحه اصلی ────────────────────────────────────────────────────
export default function AdminServicesPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(null) // null | {} | service
  const [showInactive, setShowInactive] = useState(false)

  const { data: services = [], isLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => api.get('/core/services/').then(r => r.data),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/core/services/${id}/`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['services'])
      qc.invalidateQueries(['dashboard'])
      toast.success('سرویس حذف شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در حذف'),
  })

  const visible = services.filter(s => showInactive || s.is_active)
  const urgent = services.filter(s => s.is_active && !s.auto_renew && s.days_left <= s.warn_days)

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">سرویس‌ها و اشتراک‌ها</h1>
        <button onClick={() => setEditing({})} className="btn-primary text-sm px-4 py-2 flex items-center gap-1.5">
          <Plus size={15} /> سرویس جدید
        </button>
      </div>

      <div className="text-xs text-gray-steel mb-4">
        دامنه، سرور، CDN و بقیه سرویس‌های سایت را با تاریخ انقضا ثبت کن — نزدیک انقضا که شود، روی داشبورد اصلی هشدار می‌گیری.
      </div>

      {urgent.length > 0 && (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 p-4 flex items-start gap-3">
          <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
          <div className="text-xs text-red-300 leading-6">
            {urgent.map(s => `${s.name} (${fmtDays(s.days_left)} روز مانده)`).join('، ')} — نیاز به تمدید دارند.
          </div>
        </div>
      )}

      <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-steel hover:text-white mb-4 w-fit">
        <div onClick={() => setShowInactive(v => !v)}
          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${showInactive ? 'bg-brand border-brand' : 'border-white/20'}`}>
          {showInactive && <Check size={12} strokeWidth={3} className="text-white" />}
        </div>
        نمایش غیرفعال‌ها
      </label>

      {isLoading ? <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div> :
       visible.length === 0 ? (
        <div className="text-center py-12 text-gray-steel text-sm">
          هنوز سرویسی ثبت نشده — با دکمه «سرویس جدید» اولین مورد (مثلاً دامنه) را اضافه کن
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                {['سرویس', 'دسته', 'ارائه‌دهنده', 'انقضا', 'وضعیت', 'هزینه تمدید', ''].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((s, i) => {
                const st = statusOf(s)
                return (
                  <tr key={s.id} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.05)', background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent', opacity: s.is_active ? 1 : 0.45 }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>
                      <button onClick={() => setEditing(s)} className="hover:text-brand transition-colors" title="ویرایش">{s.name}</button>
                      {s.auto_renew && (
                        <span className="mr-2 text-[10px] text-sky-400 inline-flex items-center gap-1">
                          <RefreshCw size={10} /> تمدید خودکار
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{s.category_display}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{s.provider || '—'}</td>
                    <td style={{ padding: '10px 12px', fontSize: 11 }}>{formatDate(s.expire_date)}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: st.color, background: st.color + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap' }}>
                        {st.label}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{s.renew_cost || '—'}</td>
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                      <button onClick={() => setEditing(s)} className="text-xs text-brand hover:text-brand/80 ml-3">ویرایش</button>
                      <button onClick={() => { if (window.confirm(`«${s.name}» حذف شود؟`)) deleteMut.mutate(s.id) }}
                        className="text-xs text-red-400 hover:text-red-300">حذف</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {editing && <ServiceEditor service={editing.id ? editing : null} onClose={() => setEditing(null)} />}
    </div>
  )
}
