import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Calendar, Eye, Lightbulb, Music, Video, Check, X, RefreshCw,
  Loader2, Send, Clock, Upload, Sparkles, TrendingUp, KeyRound, Trash2,
} from 'lucide-react'
import { contentStudioService } from '../../services/contentStudio'
import usePermissions from '../../hooks/usePermissions'
import { formatDate } from '../../utils/date'

// ─── برچسب‌ها و رنگ‌ها ───────────────────────────────────────
const APPROVAL = {
  draft:    { label: 'پیش‌نویس',  color: '#FFB020' },
  approved: { label: 'تأیید شده', color: '#00C896' },
  rejected: { label: 'رد شده',    color: '#FF3B3B' },
}

const CTYPE = {
  post:  { label: 'پست',    color: '#0066FF' },
  story: { label: 'استوری', color: '#B24BF3' },
  reel:  { label: 'ریل',    color: '#00C896' },
}

const CATEGORIES = [
  ['product_showcase', 'معرفی محصول'],
  ['educational', 'آموزشی'],
  ['offer', 'پیشنهاد و تخفیف'],
  ['trend', 'ترند'],
  ['behind_scenes', 'پشت صحنه'],
]

const errMsg = (e, fallback) =>
  e.response?.data?.error || e.response?.data?.detail || fallback

function Badge({ label, color }) {
  return (
    <span style={{ color, background: color + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap' }}>
      {label}
    </span>
  )
}

function CheckBox({ checked, onToggle }) {
  return (
    <div onClick={onToggle}
      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${checked ? 'bg-brand border-brand' : 'border-white/20'}`}>
      {checked && <Check size={12} strokeWidth={3} className="text-white" />}
    </div>
  )
}

function PendingHint({ text }) {
  return (
    <div className="flex items-center gap-2 text-xs text-brand mt-3">
      <Loader2 size={14} className="animate-spin" />
      {text}
    </div>
  )
}

// ─── اسلات اوج بعدی به وقت تهران: ۱۲:۳۰ یا ۱۹:۳۰ ────────────
// مقدار برگشتی برای input[type=datetime-local] فرمت YYYY-MM-DDTHH:MM است
function nextPeakSlotLocal() {
  const TEHRAN_OFFSET_MIN = 210 // +03:30 — ایران از ۱۴۰۱ ساعت تابستانی ندارد
  const now = new Date()
  const tehran = new Date(now.getTime() + (now.getTimezoneOffset() + TEHRAN_OFFSET_MIN) * 60000)
  const mk = (h, m, addDays = 0) => {
    const d = new Date(tehran)
    d.setDate(d.getDate() + addDays)
    d.setHours(h, m, 0, 0)
    return d
  }
  const slot = tehran < mk(12, 30) ? mk(12, 30) : tehran < mk(19, 30) ? mk(19, 30) : mk(12, 30, 1)
  const pad = (n) => String(n).padStart(2, '0')
  return `${slot.getFullYear()}-${pad(slot.getMonth() + 1)}-${pad(slot.getDate())}T${pad(slot.getHours())}:${pad(slot.getMinutes())}`
}

// مقدار datetime-local را به وقت تهران (+03:30) به ISO تبدیل می‌کند
function localToTehranISO(value) {
  if (!value) return null
  return new Date(`${value}:00+03:30`).toISOString()
}

// ─── مودال تأیید و انتشار ────────────────────────────────────
function ApproveModal({ post, onClose }) {
  const qc = useQueryClient()
  const [selected, setSelected] = useState(new Set())
  const [scheduledAt, setScheduledAt] = useState(nextPeakSlotLocal)

  const { data: platforms = [], isLoading } = useQuery({
    queryKey: ['publisher-platforms'],
    queryFn: contentStudioService.platforms,
  })
  const activePlatforms = platforms.filter(p => p.is_active)

  const toggle = (id) => {
    setSelected(s => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id); else n.add(id)
      return n
    })
  }

  const approveMut = useMutation({
    mutationFn: () => {
      const payload = { platform_ids: [...selected] }
      const iso = localToTehranISO(scheduledAt)
      if (iso) payload.scheduled_at = iso
      return contentStudioService.approvePost(post.id, payload)
    },
    onSuccess: (d) => {
      const skipped = d.skipped_platforms?.length
        ? ` — بدون ${d.skipped_platforms.join('، ')} (غیرفعال)`
        : ''
      toast.success(`پست تأیید و برای انتشار زمان‌بندی شد${skipped}`)
      qc.invalidateQueries({ queryKey: ['studio-posts'] })
      onClose()
    },
    onError: (e) => toast.error(errMsg(e, 'خطا در تأیید پست')),
  })

  const submit = () => {
    if (selected.size === 0) return toast.error('حداقل یک پلتفرم را انتخاب کنید')
    approveMut.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="card p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-sm">تأیید و انتشار</h3>
          <button onClick={onClose} className="text-gray-steel hover:text-white"><X size={16} /></button>
        </div>
        <div className="text-xs text-gray-steel mb-4 line-clamp-2">{post.title}</div>

        <label className="label text-xs mb-2 block">انتشار در پلتفرم‌ها *</label>
        {isLoading ? <div className="text-xs text-gray-steel mb-4">در حال بارگذاری...</div> : (
          <div className="flex flex-wrap gap-3 mb-4">
            {activePlatforms.map(p => (
              <label key={p.id} className="flex items-center gap-2 cursor-pointer text-xs text-gray-steel hover:text-white">
                <CheckBox checked={selected.has(p.id)} onToggle={() => toggle(p.id)} />
                {p.name}
                {!p.configured && <span className="text-[10px] text-gray-steel/70">(پیکربندی نشده)</span>}
              </label>
            ))}
            {activePlatforms.length === 0 && (
              <div className="text-xs text-gray-steel">هیچ پلتفرم فعالی تعریف نشده است</div>
            )}
          </div>
        )}

        <label className="label text-xs mb-1 flex items-center gap-1">
          <Clock size={12} /> زمان انتشار (به وقت تهران — پیش‌فرض: نزدیک‌ترین اسلات اوج)
        </label>
        <input type="datetime-local" value={scheduledAt} onChange={e => setScheduledAt(e.target.value)}
          dir="ltr" className="input text-sm text-left w-full mb-5" />

        <div className="flex gap-2">
          <button onClick={submit} disabled={approveMut.isPending}
            className="btn-primary flex-1 py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 text-sm">
            {approveMut.isPending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            {approveMut.isPending ? 'در حال تأیید...' : 'تأیید و انتشار'}
          </button>
          <button onClick={onClose} disabled={approveMut.isPending}
            className="px-4 py-2.5 rounded-xl border border-white/10 text-sm text-gray-steel hover:text-white disabled:opacity-50">
            انصراف
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── تب ۱: تقویم محتوا ───────────────────────────────────────
function HookSection({ post, canBuild }) {
  const qc = useQueryClient()

  const hookMut = useMutation({
    mutationFn: () => contentStudioService.generateHook(post.id),
    onSuccess: () => {
      toast.success('ساخت هوک AI شروع شد — ۱ تا ۳ دقیقه طول می‌کشد')
      qc.invalidateQueries({ queryKey: ['studio-posts'] })
    },
    onError: (e) => toast.error(errMsg(e, 'شروع ساخت هوک ناموفق بود')),
  })

  const readyBadge = (
    <Badge
      label={post.hook_provider === 'veo' ? 'هوک AI آماده · Veo'
        : post.hook_provider === 'hf' ? 'هوک AI آماده · HF رایگان'
        : 'هوک AI آماده'}
      color="#00C896" />
  )

  if (!canBuild || post.content_type !== 'reel' || post.approval_status !== 'draft') {
    if (post.hook_status === 'ready') {
      return readyBadge
    }
    return null
  }

  if (post.hook_status === 'building') {
    return <PendingHint text="در حال ساخت هوک سینمایی… معمولاً ۱ تا ۳ دقیقه" />
  }

  return (
    <div className="flex flex-col gap-1">
      {post.hook_status === 'ready' && (
        <>
          {readyBadge}
          <span className="text-[10px] text-gray-steel">
            برای ترکیب در ویدیوی نهایی، دوباره «ساخت ویدیو» را بزنید
          </span>
        </>
      )}
      {post.hook_status !== 'ready' && (
        <button onClick={() => hookMut.mutate()} disabled={hookMut.isPending}
          className="text-xs px-3 py-1.5 rounded-lg border border-brand/40 text-brand hover:bg-brand/10 flex items-center gap-1 disabled:opacity-50 w-fit">
          {hookMut.isPending ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
          {post.hook_status === 'failed' ? 'تلاش مجدد هوک AI' : 'ساخت هوک سینمایی AI'}
        </button>
      )}
      {post.hook_status !== 'ready' && (
        <span className="text-[10px] text-gray-steel">~۱ دلار هزینه — ۱ تا ۳ دقیقه صبر</span>
      )}
      {post.hook_status === 'failed' && post.hook_error && (
        <span className="text-[10px] text-red-400 line-clamp-2">{post.hook_error}</span>
      )}
    </div>
  )
}

function PostCard({ post, canBuild, canApprove, onPreview, onApprove }) {
  const qc = useQueryClient()
  const ct = CTYPE[post.content_type] || { label: post.content_type || '—', color: '#8892A0' }
  const st = APPROVAL[post.approval_status] || { label: post.approval_status || '—', color: '#8892A0' }

  const buildMut = useMutation({
    mutationFn: () => contentStudioService.buildMedia(post.id),
    onSuccess: () => {
      toast.success('ویدیو ساخته و به پست ضمیمه شد')
      qc.invalidateQueries({ queryKey: ['studio-posts'] })
    },
    onError: (e) => {
      if (e.response?.status === 409) {
        toast.error('این پست از قبل ویدیو دارد — از تب پیش‌نمایش «بازسازی ویدیو» را بزنید')
      } else {
        toast.error(errMsg(e, 'ساخت ویدیو ناموفق بود'))
      }
    },
  })

  const rejectMut = useMutation({
    mutationFn: () => contentStudioService.rejectPost(post.id),
    onSuccess: () => {
      toast.success('پست رد شد')
      qc.invalidateQueries({ queryKey: ['studio-posts'] })
    },
    onError: (e) => toast.error(errMsg(e, 'خطا در رد پست')),
  })

  const styleMut = useMutation({
    mutationFn: (style) => contentStudioService.setStyle(post.id, style),
    onSuccess: () => {
      toast.success('سبک ویدیو تغییر کرد')
      qc.invalidateQueries({ queryKey: ['studio-posts'] })
    },
    onError: (e) => toast.error(errMsg(e, 'تغییر سبک ناموفق بود')),
  })

  const building = buildMut.isPending

  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Badge label={ct.label} color={ct.color} />
          <Badge label={st.label} color={st.color} />
        </div>
        <button onClick={() => onPreview(post)} title="پیش‌نمایش"
          className="text-gray-steel hover:text-white shrink-0">
          <Eye size={15} />
        </button>
      </div>

      <button onClick={() => onPreview(post)} className="text-right">
        <div className="text-sm text-white font-medium mb-1 line-clamp-1">{post.title}</div>
        <div className="text-xs text-gray-steel leading-5 line-clamp-3 whitespace-pre-wrap mb-2">{post.body}</div>
      </button>

      {post.hashtags && (
        <div className="text-[11px] text-brand/80 line-clamp-1 mb-2" dir="ltr" style={{ textAlign: 'right' }}>{post.hashtags}</div>
      )}

      {post.idea_signal && (
        <div className="text-[10px] text-gray-steel/80 line-clamp-1 mb-2 flex items-center gap-1">
          <Lightbulb size={10} className="shrink-0" /> منبع ایده: {post.idea_signal}
        </div>
      )}

      <div className="text-[11px] text-gray-steel mb-3 flex items-center gap-1">
        <Clock size={11} />
        {post.scheduled_at
          ? `زمان‌بندی: ${formatDate(post.scheduled_at, { withTime: true })}`
          : `ساخته شده: ${formatDate(post.created_at, { withTime: true })}`}
      </div>

      <div className="mb-3">
        <HookSection post={post} canBuild={canBuild} />
      </div>

      {building && (
        <PendingHint text="در حال ساخت ویدیو با FFmpeg… ممکن است تا دو دقیقه طول بکشد" />
      )}

      <div className="mt-auto flex flex-wrap gap-2">
        {post.approval_status === 'draft' && canBuild && !post.video_url && (
          <button onClick={() => buildMut.mutate()} disabled={building}
            className="text-xs px-3 py-1.5 rounded-lg border border-white/10 text-gray-steel hover:text-white flex items-center gap-1 disabled:opacity-50">
            {building ? <Loader2 size={12} className="animate-spin" /> : <Video size={12} />}
            ساخت ویدیو
          </button>
        )}
        {post.approval_status === 'draft' && post.content_type === 'reel' && canBuild && (
          <select value={post.video_style || 'auto'}
            onChange={e => styleMut.mutate(e.target.value)} disabled={styleMut.isPending}
            title="سبک ویدیو"
            className="text-xs px-2 py-1.5 rounded-lg border border-white/10 bg-transparent text-gray-steel hover:text-white disabled:opacity-50">
            <option value="auto" className="bg-gray-900">خودکار (اسلایدشو + هوک AI)</option>
            <option value="motion" className="bg-gray-900">موشن‌گرافیک</option>
          </select>
        )}
        {(post.approval_status === 'draft' || post.approval_status === 'rejected') && canApprove && (
          <button onClick={() => onApprove(post)}
            className="text-xs px-3 py-1.5 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 flex items-center gap-1">
            <Check size={12} />
            {post.approval_status === 'rejected' ? 'تأیید مجدد' : 'تأیید و انتشار'}
          </button>
        )}
        {post.approval_status === 'draft' && canApprove && (
          <button onClick={() => rejectMut.mutate()} disabled={rejectMut.isPending}
            className="text-xs px-3 py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 flex items-center gap-1 disabled:opacity-50">
            <X size={12} /> رد
          </button>
        )}
        {post.approval_status === 'approved' && (
          <span className="text-[11px] text-emerald-400 flex items-center gap-1">
            <Check size={12} />
            {post.scheduled_at ? 'در صف انتشار زمان‌بندی‌شده' : 'تأیید شده — آماده انتشار'}
          </span>
        )}
      </div>
    </div>
  )
}

function CalendarTab({ status, setStatus, ctype, setCtype, onPreview, onApprove, canBuild, canApprove }) {
  const params = {}
  if (status) params.status = status
  if (ctype) params.content_type = ctype

  const { data: posts = [], isLoading } = useQuery({
    queryKey: ['studio-posts', status, ctype],
    queryFn: () => contentStudioService.posts(params),
    // تا وقتی هوکی در حال ساخت است هر ۱۰ ثانیه تازه‌سازی شود
    refetchInterval: (query) =>
      query.state.data?.some(p => p.hook_status === 'building') ? 10000 : false,
  })

  const chips = (items, value, setter) => (
    <div className="flex flex-wrap gap-1.5">
      {items.map(([v, l]) => (
        <button key={v} onClick={() => setter(v)}
          className={`text-[11px] px-3 py-1.5 rounded-full border transition-all ${value === v ? 'border-brand text-brand bg-brand/10' : 'border-white/10 text-gray-steel hover:text-white'}`}>
          {l}
        </button>
      ))}
    </div>
  )

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4 mb-5">
        {chips([['', 'همه'], ['draft', 'پیش‌نویس'], ['approved', 'تأیید شده'], ['rejected', 'رد شده']], status, setStatus)}
        <span className="w-px h-5 bg-white/10" />
        {chips([['', 'همه انواع'], ['post', 'پست'], ['story', 'استوری'], ['reel', 'ریل']], ctype, setCtype)}
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 text-gray-steel text-sm">
          محتوایی با این فیلتر پیدا نشد — از تب «ایده دستی» محتوای جدید بساز
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-2 max-sm:grid-cols-1">
          {posts.map(p => (
            <PostCard key={p.id} post={p} canBuild={canBuild} canApprove={canApprove}
              onPreview={onPreview} onApprove={onApprove} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── تب ۲: پیش‌نمایش ─────────────────────────────────────────
function PreviewTab({ posts, selectedId, onSelect, canBuild }) {
  const qc = useQueryClient()
  const post = posts.find(p => p.id === selectedId) || null

  const rebuildMut = useMutation({
    mutationFn: () => contentStudioService.buildMedia(post.id, true),
    onSuccess: () => {
      toast.success('ویدیو بازسازی شد')
      qc.invalidateQueries({ queryKey: ['studio-posts'] })
    },
    onError: (e) => toast.error(errMsg(e, 'بازسازی ویدیو ناموفق بود')),
  })

  if (posts.length === 0) {
    return <div className="text-center py-12 text-gray-steel text-sm">هنوز محتوایی برای پیش‌نمایش نیست</div>
  }

  return (
    <div className="grid grid-cols-3 gap-6 max-lg:grid-cols-1">
      <div className="card p-4">
        <label className="label text-xs mb-2 block">انتخاب محتوا</label>
        <select value={selectedId || ''} onChange={e => onSelect(Number(e.target.value) || null)}
          className="input text-sm w-full mb-4">
          <option value="">— انتخاب کن —</option>
          {posts.map(p => (
            <option key={p.id} value={p.id}>
              {(CTYPE[p.content_type]?.label || '')} | {p.title}
            </option>
          ))}
        </select>
        <div className="space-y-1.5 max-h-96 overflow-y-auto">
          {posts.slice(0, 20).map(p => (
            <button key={p.id} onClick={() => onSelect(p.id)}
              className={`w-full text-right text-xs px-3 py-2 rounded-lg transition-all flex items-center justify-between gap-2 ${p.id === selectedId ? 'bg-brand/15 text-white' : 'text-gray-steel hover:bg-white/5'}`}>
              <span className="truncate">{p.title}</span>
              <Badge label={CTYPE[p.content_type]?.label || '—'} color={CTYPE[p.content_type]?.color || '#8892A0'} />
            </button>
          ))}
        </div>
      </div>

      <div className="col-span-2 max-lg:col-span-1">
        {!post ? (
          <div className="card p-12 text-center text-gray-steel text-sm">
            یک محتوا را از لیست انتخاب کن یا از تب «تقویم محتوا» روی کارت آن بزن
          </div>
        ) : (
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Badge label={CTYPE[post.content_type]?.label || '—'} color={CTYPE[post.content_type]?.color || '#8892A0'} />
                <Badge label={APPROVAL[post.approval_status]?.label || '—'} color={APPROVAL[post.approval_status]?.color || '#8892A0'} />
                {post.hook_status === 'ready' && (
                  <Badge
                    label={post.hook_provider === 'veo' ? 'هوک AI آماده · Veo'
                      : post.hook_provider === 'hf' ? 'هوک AI آماده · HF رایگان'
                      : 'هوک AI آماده'}
                    color="#00C896" />
                )}
                <span className="text-sm text-white font-medium">{post.title}</span>
              </div>
              {canBuild && (
                <button onClick={() => rebuildMut.mutate()} disabled={rebuildMut.isPending}
                  className="text-xs px-3 py-1.5 rounded-lg border border-white/10 text-gray-steel hover:text-white flex items-center gap-1 disabled:opacity-50">
                  {rebuildMut.isPending ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                  بازسازی ویدیو
                </button>
              )}
            </div>

            {rebuildMut.isPending && (
              <PendingHint text="در حال بازسازی ویدیو… ممکن است تا دو دقیقه طول بکشد" />
            )}

            {post.hook_status === 'ready' && (
              <div className="text-[11px] text-emerald-400 mb-3 flex items-center gap-1">
                <Sparkles size={11} />
                هوک AI در ساخت بعدی ویدیو به ابتدای آن اضافه می‌شود — برای ترکیب، «بازسازی ویدیو» را بزنید
              </div>
            )}
            {post.hook_status === 'building' && (
              <PendingHint text="در حال ساخت هوک سینمایی… معمولاً ۱ تا ۳ دقیقه" />
            )}

            <div className="rounded-xl overflow-hidden border border-white/10 bg-black/30 mb-4 flex items-center justify-center min-h-40">
              {post.video_url ? (
                <video controls src={post.video_url} className="max-h-[28rem] w-full" />
              ) : post.image_url ? (
                <img src={post.image_url} alt={post.title} className="max-h-[28rem] object-contain" />
              ) : (
                <div className="text-xs text-gray-steel py-16">این محتوا هنوز تصویر یا ویدیو ندارد</div>
              )}
            </div>

            <div className="text-sm text-gray-steel leading-7 whitespace-pre-wrap mb-3">{post.body}</div>
            {post.hashtags && (
              <div className="text-xs text-brand/80" dir="ltr" style={{ textAlign: 'right' }}>{post.hashtags}</div>
            )}
            {post.scheduled_at && (
              <div className="text-[11px] text-gray-steel mt-3 flex items-center gap-1">
                <Clock size={11} /> زمان‌بندی: {formatDate(post.scheduled_at, { withTime: true })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── تب ۳: ایده دستی ─────────────────────────────────────────
function IdeaTab({ onGenerated }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('product_showcase')
  const [contentType, setContentType] = useState('reel')
  const [result, setResult] = useState(null)

  const ideaMut = useMutation({
    mutationFn: () => contentStudioService.createIdea({
      title: title.trim(),
      description: description.trim(),
      category,
      content_type: contentType,
    }),
    onSuccess: (d) => {
      toast.success('محتوا تولید و پیش‌نویس ساخته شد')
      setResult(d)
      setTitle(''); setDescription('')
    },
    onError: (e) => toast.error(errMsg(e, 'تولید محتوا با هوش مصنوعی ناموفق بود')),
  })

  const submit = () => {
    if (!title.trim()) return toast.error('ایده را بنویس')
    setResult(null)
    ideaMut.mutate()
  }

  return (
    <div className="max-w-2xl">
      <div className="card p-6">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">ایده محتوا *</label>
            <textarea value={title} onChange={e => setTitle(e.target.value)} rows={2}
              className="input text-sm w-full"
              placeholder="مثلاً: مزایای دوربین تحت شبکه برای مغازه‌ها در یک جمله" />
          </div>
          <div className="col-span-2">
            <label className="label text-xs mb-1 block">توضیح تکمیلی (اختیاری)</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
              className="input text-sm w-full" placeholder="جزئیاتی که به تولید کپشن بهتر کمک می‌کند..." />
          </div>
          <div>
            <label className="label text-xs mb-1 block">دسته‌بندی</label>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input text-sm w-full">
              {CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="label text-xs mb-1 block">نوع محتوا</label>
            <select value={contentType} onChange={e => setContentType(e.target.value)} className="input text-sm w-full">
              {Object.entries(CTYPE).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
            </select>
          </div>
        </div>

        <button onClick={submit} disabled={ideaMut.isPending}
          className="btn-primary px-6 py-2.5 flex items-center gap-2 disabled:opacity-50 text-sm">
          {ideaMut.isPending ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
          {ideaMut.isPending ? 'در حال تولید...' : 'تولید محتوا'}
        </button>
        {ideaMut.isPending && (
          <PendingHint text="در حال تولید با هوش مصنوعی… ممکن است تا یک دقیقه طول بکشد" />
        )}
      </div>

      {result && (
        <div className="card p-6 mt-4 border border-brand/30">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <Sparkles size={15} className="text-brand" /> خروجی تولیدشده
            </h3>
            <button onClick={() => onGenerated(result.post_id)}
              className="text-xs px-3 py-1.5 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 flex items-center gap-1">
              <Eye size={12} /> مشاهده پیش‌نویس
            </button>
          </div>
          <div className="text-sm text-gray-steel leading-7 whitespace-pre-wrap mb-3">{result.caption}</div>
          {result.hashtags?.length > 0 && (
            <div className="text-xs text-brand/80" dir="ltr" style={{ textAlign: 'right' }}>
              {result.hashtags.map(h => `#${h}`).join(' ')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── کارت تنظیمات موتور ویدیو (Veo + Hugging Face) ───────────
function KeyField({ label, hint, helpText, field, isSet, maskedHint, onSave, saving }) {
  const [value, setValue] = useState('')
  return (
    <div className="border-b border-white/5 last:border-0 pb-4 last:pb-0 mb-4 last:mb-0">
      <div className={`text-xs mb-2 ${isSet ? 'text-emerald-400' : 'text-gray-steel'}`}>
        {label}: {isSet ? `تنظیم شده (${maskedHint})` : hint}
      </div>
      {helpText && <div className="text-[10px] text-gray-steel/70 mb-2">{helpText}</div>}
      <input type="password" value={value} onChange={e => setValue(e.target.value)} dir="ltr"
        className="input text-sm w-full text-left mb-2" placeholder="کلید جدید..." />
      <div className="flex gap-2">
        <button onClick={() => { if (!value.trim()) return toast.error('کلید جدید را بنویس'); onSave({ [field]: value.trim() }, () => setValue('')) }}
          disabled={saving}
          className="btn-primary flex-1 py-1.5 flex items-center justify-center gap-1 disabled:opacity-50 text-xs">
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
          ذخیره
        </button>
        {isSet && (
          <button onClick={() => onSave({ [field]: '__clear__' }, () => setValue(''))} disabled={saving}
            className="px-3 py-1.5 rounded-xl border border-red-500/30 text-red-400 hover:bg-red-500/10 flex items-center gap-1 disabled:opacity-50 text-xs">
            <Trash2 size={12} /> حذف کلید
          </button>
        )}
      </div>
    </div>
  )
}

function VideoEngineCard() {
  const qc = useQueryClient()
  const [space, setSpace] = useState(null)

  const { data: st, isLoading } = useQuery({
    queryKey: ['studio-settings'],
    queryFn: contentStudioService.settings,
  })

  const saveMut = useMutation({
    mutationFn: (payload) => contentStudioService.saveSettings(payload),
    onSuccess: (d, _payload, _ctx) => {
      toast.success('تنظیمات ذخیره شد')
      qc.invalidateQueries({ queryKey: ['studio-settings'] })
    },
    onError: (e) => toast.error(errMsg(e, 'ذخیره تنظیمات ناموفق بود')),
  })

  const save = (payload, after) => saveMut.mutate(payload, { onSuccess: () => after?.() })
  const spaceValue = space === null ? (st?.hf_space || '') : space

  return (
    <div className="card p-6 h-fit">
      <h3 className="font-bold text-white text-sm mb-1 flex items-center gap-2">
        <KeyRound size={15} className="text-brand" /> تنظیمات موتور ویدیو
      </h3>
      <div className="text-[10px] text-gray-steel/70 mb-4">
        زنجیرهٔ ساخت هوک: اول Veo (پولی، باکیفیت) — در صورت اتمام سهمیه، HF رایگان
      </div>
      {isLoading ? (
        <div className="text-xs text-gray-steel">در حال بارگذاری...</div>
      ) : (
        <>
          <KeyField label="کلید Veo" field="veo_api_key" saving={saveMut.isPending}
            isSet={st?.veo_api_key_set} maskedHint={st?.veo_api_key_hint}
            hint="تنظیم نشده — از کلید Gemini دستیار استفاده می‌شود" onSave={save} />
          <KeyField label="توکن Hugging Face" field="hf_token" saving={saveMut.isPending}
            isSet={st?.hf_token_set} maskedHint={st?.hf_token_hint}
            hint="تنظیم نشده — موتور رایگان HF کار نمی‌کند"
            helpText="حساب رایگان huggingface.co ← Settings ← Access Tokens"
            onSave={save} />
          <div>
            <label className="label text-xs mb-1 block">اسپیس HF (اختیاری — خالی یعنی پیش‌فرض رله)</label>
            <div className="flex gap-2">
              <input value={spaceValue} onChange={e => setSpace(e.target.value)} dir="ltr"
                className="input text-sm w-full text-left" placeholder="Lightricks/ltx-video-distilled" />
              <button onClick={() => save({ hf_space: spaceValue.trim() })} disabled={saveMut.isPending}
                className="px-4 py-1.5 rounded-xl border border-white/10 text-gray-steel hover:text-white flex items-center gap-1 disabled:opacity-50 text-xs shrink-0">
                ذخیره
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ─── تب ۴: کتابخانه موزیک ────────────────────────────────────
function MusicTab({ canPublish, canCredentials }) {
  const qc = useQueryClient()
  const [title, setTitle] = useState('')
  const [mood, setMood] = useState('')
  const [file, setFile] = useState(null)

  const { data: tracks = [], isLoading } = useQuery({
    queryKey: ['studio-music'],
    queryFn: contentStudioService.music,
    enabled: canPublish,
  })

  const uploadMut = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('title', title.trim())
      if (mood.trim()) fd.append('mood', mood.trim())
      fd.append('file', file)
      return contentStudioService.uploadMusic(fd)
    },
    onSuccess: () => {
      toast.success('موزیک به کتابخانه اضافه شد')
      qc.invalidateQueries({ queryKey: ['studio-music'] })
      setTitle(''); setMood(''); setFile(null)
    },
    onError: (e) => toast.error(errMsg(e, 'آپلود موزیک ناموفق بود')),
  })

  if (!canPublish && !canCredentials) {
    return (
      <div className="text-center py-12 text-gray-steel text-sm">
        برای مدیریت کتابخانه موزیک و تنظیمات به دسترسی «تولید و انتشار محتوا» یا «اعتبارنامه‌های انتشار» نیاز داری
      </div>
    )
  }

  const submit = () => {
    if (!title.trim()) return toast.error('عنوان موزیک الزامی است')
    if (!file) return toast.error('فایل موزیک را انتخاب کن')
    uploadMut.mutate()
  }

  return (
    <div className="grid grid-cols-2 gap-6 max-lg:grid-cols-1">
      <div className="space-y-6">
      {canPublish && (
      <div className="card p-6 h-fit">
        <h3 className="font-bold text-white text-sm mb-4 flex items-center gap-2">
          <Upload size={15} className="text-brand" /> آپلود موزیک جدید
        </h3>
        <div className="space-y-3 mb-4">
          <div>
            <label className="label text-xs mb-1 block">عنوان *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} className="input text-sm w-full"
              placeholder="مثلاً: موزیک پرانرژی ریل تابستانه" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">حال‌وهوا (اختیاری)</label>
            <input value={mood} onChange={e => setMood(e.target.value)} dir="ltr"
              className="input text-sm w-full text-left" placeholder="energetic / calm / corporate" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">فایل (mp3 / wav / m4a — حداکثر ۲۰ مگابایت) *</label>
            <label className="input text-sm flex items-center gap-2 cursor-pointer text-gray-steel hover:text-white">
              <Music size={15} />
              <span className="truncate">{file ? file.name : 'انتخاب فایل...'}</span>
              <input type="file" accept=".mp3,.wav,.m4a,audio/*" className="hidden"
                onChange={e => setFile(e.target.files?.[0] || null)} />
            </label>
            {file && (
              <button onClick={() => setFile(null)} className="text-xs text-red-400 hover:text-red-300 mt-2 flex items-center gap-1">
                <X size={12} /> حذف فایل
              </button>
            )}
          </div>
        </div>
        <button onClick={submit} disabled={uploadMut.isPending}
          className="btn-primary px-6 py-2.5 flex items-center gap-2 disabled:opacity-50 text-sm">
          {uploadMut.isPending ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
          {uploadMut.isPending ? 'در حال آپلود...' : 'آپلود'}
        </button>
      </div>
      )}
      {canCredentials && <VideoEngineCard />}
      </div>

      {canPublish && (
      <div>
        {isLoading ? (
          <div className="text-center py-8 text-gray-steel text-sm">در حال بارگذاری...</div>
        ) : tracks.length === 0 ? (
          <div className="card p-12 text-center text-gray-steel text-sm">
            کتابخانه خالی است — اولین موزیک را آپلود کن
          </div>
        ) : (
          <div className="space-y-2">
            {tracks.map(t => (
              <div key={t.id} className="card p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Music size={14} className="text-brand shrink-0" />
                    <span className="text-sm text-white font-medium truncate">{t.title}</span>
                    {t.mood && <Badge label={t.mood} color="#B24BF3" />}
                  </div>
                  {!t.is_active && <Badge label="غیرفعال" color="#8892A0" />}
                </div>
                {t.file_url && (
                  <audio controls src={t.file_url} className="w-full h-9" preload="none" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      )}
    </div>
  )
}

// ─── تب ۵: گزارش عملکرد ─────────────────────────────────────
const fmtNum = (n) => new Intl.NumberFormat('fa-IR').format(n || 0)

const METRIC_COLS = [
  ['reach', 'ریچ'],
  ['views', 'بازدید'],
  ['likes', 'لایک'],
  ['comments', 'کامنت'],
  ['shares', 'اشتراک'],
  ['saved', 'ذخیره'],
]

function ReportTab() {
  const { data: insights = [], isLoading } = useQuery({
    queryKey: ['studio-insights'],
    queryFn: contentStudioService.insights,
  })

  if (isLoading) {
    return <div className="text-center py-8 text-gray-steel text-sm">در حال بارگذاری...</div>
  }

  if (insights.length === 0) {
    return (
      <div className="card p-12 text-center text-gray-steel text-sm">
        هنوز داده‌ای ثبت نشده — بعد از انتشار و اجرای fetch_ig_insights پر می‌شود
      </div>
    )
  }

  return (
    <div className="card p-4 overflow-x-auto">
      <div className="text-xs text-gray-steel mb-4 flex items-center gap-1">
        <TrendingUp size={13} className="text-brand" />
        عملکرد پست‌های منتشرشده در اینستاگرام — مرتب‌شده بر اساس ریچ
      </div>
      <table className="w-full text-sm min-w-[640px]">
        <thead>
          <tr className="text-[11px] text-gray-steel border-b border-white/10">
            <th className="text-right py-2 px-2 font-normal">پست</th>
            {METRIC_COLS.map(([k, l]) => (
              <th key={k} className="text-center py-2 px-2 font-normal">{l}</th>
            ))}
            <th className="text-center py-2 px-2 font-normal">انتشار</th>
          </tr>
        </thead>
        <tbody>
          {insights.map(row => {
            const ct = CTYPE[row.content_type] || { label: row.content_type || '—', color: '#8892A0' }
            return (
              <tr key={row.post_id} className="border-b border-white/5 last:border-0 hover:bg-white/5">
                <td className="py-2.5 px-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    {row.thumbnail && (
                      <img src={row.thumbnail} alt="" className="w-9 h-9 rounded-lg object-cover shrink-0 border border-white/10" />
                    )}
                    <div className="min-w-0">
                      <div className="text-xs text-white truncate max-w-52">{row.title}</div>
                      <Badge label={ct.label} color={ct.color} />
                    </div>
                  </div>
                </td>
                {METRIC_COLS.map(([k]) => (
                  <td key={k} className={`text-center py-2.5 px-2 text-xs ${k === 'reach' ? 'text-brand font-medium' : 'text-gray-steel'}`}>
                    {fmtNum(row[k])}
                  </td>
                ))}
                <td className="text-center py-2.5 px-2 text-[11px] text-gray-steel whitespace-nowrap">
                  {row.published_at ? formatDate(row.published_at) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── صفحه اصلی ────────────────────────────────────────────────
export default function ContentStudioPage() {
  const { can } = usePermissions()
  const [tab, setTab] = useState('calendar')
  const [status, setStatus] = useState('')
  const [ctype, setCtype] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [approvingPost, setApprovingPost] = useState(null)

  const canBuild = can('publisher_publish')
  const canApprove = can('publisher_approve')
  const canCredentials = can('publisher_credentials')

  // لیست بدون فیلتر برای تب پیش‌نمایش
  const { data: allPosts = [] } = useQuery({
    queryKey: ['studio-posts', '', ''],
    queryFn: () => contentStudioService.posts(),
    refetchInterval: (query) =>
      query.state.data?.some(p => p.hook_status === 'building') ? 10000 : false,
  })

  const openPreview = (post) => {
    setSelectedId(post.id)
    setTab('preview')
  }

  const jumpToDraft = (postId) => {
    setSelectedId(postId)
    setStatus('draft')
    setCtype('')
    setTab('calendar')
  }

  const tabs = [
    ['calendar', 'تقویم محتوا', Calendar],
    ['preview', 'پیش‌نمایش', Eye],
    ['idea', 'ایده دستی', Lightbulb],
    ['music', 'موزیک و تنظیمات', Music],
    ['report', 'گزارش', TrendingUp],
  ]

  return (
    <div className="container-main py-8 max-w-6xl">
      <h1 className="font-display font-bold text-2xl text-white mb-2">استودیو محتوا</h1>
      <div className="text-xs text-gray-steel mb-6">
        خط لولهٔ محتوای خودکار اینستاگرام — از ایده تا کپشن، ویدیو، تأیید و زمان‌بندی انتشار.
      </div>

      <div className="flex gap-2 mb-6 border-b border-white/10 overflow-x-auto">
        {tabs.map(([k, v, Icon]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all flex items-center gap-2 whitespace-nowrap ${tab === k ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            <Icon size={15} /> {v}
          </button>
        ))}
      </div>

      {tab === 'calendar' && (
        <CalendarTab status={status} setStatus={setStatus} ctype={ctype} setCtype={setCtype}
          onPreview={openPreview} onApprove={setApprovingPost}
          canBuild={canBuild} canApprove={canApprove} />
      )}
      {tab === 'preview' && (
        <PreviewTab posts={allPosts} selectedId={selectedId} onSelect={setSelectedId} canBuild={canBuild} />
      )}
      {tab === 'idea' && <IdeaTab onGenerated={jumpToDraft} />}
      {tab === 'music' && <MusicTab canPublish={canBuild} canCredentials={canCredentials} />}
      {tab === 'report' && <ReportTab />}

      {approvingPost && (
        <ApproveModal post={approvingPost} onClose={() => setApprovingPost(null)} />
      )}
    </div>
  )
}
