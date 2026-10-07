import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Send, Image, Video, History, Settings, RefreshCw, ChevronDown, Check, X, HelpCircle } from 'lucide-react'
import { publisherService } from '../../services/publisher'
import usePermissions from '../../hooks/usePermissions'
import { formatDate } from '../../utils/date'

// ─── وضعیت‌ها ─────────────────────────────────────────────────
const STATUS = {
  done:       { label: 'موفق',        color: '#00C896' },
  success:    { label: 'موفق',        color: '#00C896' },
  partial:    { label: 'ناقص',        color: '#FFB020' },
  failed:     { label: 'ناموفق',      color: '#FF3B3B' },
  pending:    { label: 'در حال انجام', color: '#0066FF' },
  processing: { label: 'در حال انجام', color: '#0066FF' },
  sending:    { label: 'در حال انجام', color: '#0066FF' },
}

function badgeOf(status) { return STATUS[status] || { label: status || '—', color: '#8892A0' } }

function StatusBadge({ status }) {
  const st = badgeOf(status)
  return (
    <span style={{ color: st.color, background: st.color + '20', padding: '2px 8px', borderRadius: 20, fontSize: 11, whiteSpace: 'nowrap' }}>
      {st.label}
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

// ─── تب ۱: محتوای جدید ───────────────────────────────────────
function ComposeTab({ onPublished }) {
  const qc = useQueryClient()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [link, setLink] = useState('')
  const [image, setImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [video, setVideo] = useState(null)
  const [selected, setSelected] = useState(new Set())

  const { data: platforms = [], isLoading } = useQuery({
    queryKey: ['publisher-platforms'],
    queryFn: publisherService.platforms,
  })
  const activePlatforms = platforms.filter(p => p.is_active)

  const togglePlatform = (id) => {
    setSelected(s => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id); else n.add(id)
      return n
    })
  }

  const pickImage = (e) => {
    const f = e.target.files?.[0] || null
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImage(f)
    setImagePreview(f ? URL.createObjectURL(f) : null)
  }

  const clearImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImage(null)
    setImagePreview(null)
  }

  const resetForm = () => {
    setTitle(''); setBody(''); setLink('')
    clearImage()
    setVideo(null)
    setSelected(new Set())
  }

  const publishMut = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('title', title)
      fd.append('body', body)
      if (link) fd.append('link', link)
      if (image) fd.append('image', image)
      if (video) fd.append('video', video)
      const post = await publisherService.createPost(fd)
      return publisherService.publish({ post_id: post.id, platform_ids: [...selected] })
    },
    onSuccess: (d) => {
      toast.success(`درخواست انتشار ثبت شد (کار شماره ${Number(d.job_id).toLocaleString('fa-IR')})`)
      qc.invalidateQueries(['publisher-jobs'])
      qc.invalidateQueries(['publisher-posts'])
      resetForm()
      onPublished(d.job_id)
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در انتشار'),
  })

  const submit = () => {
    if (!title.trim()) return toast.error('عنوان الزامی است')
    if (!body.trim()) return toast.error('متن محتوا الزامی است')
    if (selected.size === 0) return toast.error('حداقل یک پیام‌رسان را انتخاب کنید')
    publishMut.mutate()
  }

  return (
    <div className="card p-6">
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="col-span-2">
          <label className="label text-xs mb-1 block">عنوان *</label>
          <input value={title} onChange={e => setTitle(e.target.value)} className="input text-sm"
            placeholder="مثلاً: نصب دوربین مداربسته در پروژه سعادت‌آباد" />
        </div>
        <div className="col-span-2">
          <label className="label text-xs mb-1 block">متن محتوا *</label>
          <textarea value={body} onChange={e => setBody(e.target.value)} rows={5}
            className="input text-sm w-full" placeholder="متن پست که در پیام‌رسان‌ها منتشر می‌شود..." />
        </div>
        <div className="col-span-2">
          <label className="label text-xs mb-1 block">لینک (اختیاری)</label>
          <input value={link} onChange={e => setLink(e.target.value)} dir="ltr"
            className="input text-sm text-left" placeholder="https://..." />
        </div>
        <div>
          <label className="label text-xs mb-1 block">تصویر (اختیاری)</label>
          <label className="input text-sm flex items-center gap-2 cursor-pointer text-gray-steel hover:text-white">
            <Image size={15} />
            <span className="truncate">{image ? image.name : 'انتخاب تصویر...'}</span>
            <input type="file" accept="image/*" className="hidden" onChange={pickImage} />
          </label>
          {imagePreview && (
            <div className="relative mt-2 w-fit">
              <img src={imagePreview} alt="پیش‌نمایش" className="max-h-40 rounded-xl border border-white/10" />
              <button onClick={clearImage}
                className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center">
                <X size={13} />
              </button>
            </div>
          )}
        </div>
        <div>
          <label className="label text-xs mb-1 block">ویدیو (اختیاری)</label>
          <label className="input text-sm flex items-center gap-2 cursor-pointer text-gray-steel hover:text-white">
            <Video size={15} />
            <span className="truncate">{video ? video.name : 'انتخاب ویدیو...'}</span>
            <input type="file" accept="video/*" className="hidden"
              onChange={e => setVideo(e.target.files?.[0] || null)} />
          </label>
          {video && (
            <button onClick={() => setVideo(null)} className="text-xs text-red-400 hover:text-red-300 mt-2 flex items-center gap-1">
              <X size={12} /> حذف ویدیو
            </button>
          )}
        </div>
      </div>

      <div className="mb-5">
        <label className="label text-xs mb-2 block">انتشار در پیام‌رسان‌ها *</label>
        {isLoading ? <div className="text-xs text-gray-steel">در حال بارگذاری...</div> :
         activePlatforms.length === 0 ? (
          <div className="text-xs text-gray-steel">هیچ پیام‌رسان فعالی تعریف نشده است</div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {activePlatforms.map(p => (
              <label key={p.id} className="flex items-center gap-2 cursor-pointer text-xs text-gray-steel hover:text-white">
                <CheckBox checked={selected.has(p.id)} onToggle={() => togglePlatform(p.id)} />
                {p.name}
                {!p.configured && <span className="text-[10px] text-gray-steel/70">(پیکربندی نشده)</span>}
              </label>
            ))}
          </div>
        )}
      </div>

      <button onClick={submit} disabled={publishMut.isPending}
        className="btn-primary px-6 py-2.5 flex items-center gap-2 disabled:opacity-50">
        <Send size={15} />
        {publishMut.isPending ? 'در حال انتشار...' : 'انتشار'}
      </button>
    </div>
  )
}

// ─── جزئیات یک کار انتشار (با polling تا پایان) ───────────────
function JobDetail({ jobId }) {
  const qc = useQueryClient()

  const { data: job, isLoading } = useQuery({
    queryKey: ['publisher-job', jobId],
    queryFn: () => publisherService.job(jobId),
    enabled: !!jobId,
    // فقط تا وقتی کار در حال انجام است، هر ۲ ثانیه تازه‌سازی شود
    refetchInterval: (query) =>
      ['pending', 'processing'].includes(query.state.data?.status) ? 2000 : false,
  })

  const retryMut = useMutation({
    mutationFn: (logId) => publisherService.retryLog(logId),
    onSuccess: () => {
      toast.success('برای تلاش مجدد بازنشانی شد')
      qc.invalidateQueries(['publisher-job', jobId])
      qc.invalidateQueries(['publisher-jobs'])
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در تلاش مجدد'),
  })

  if (isLoading) return <div className="text-xs text-gray-steel py-3">در حال بارگذاری...</div>
  if (!job) return null

  return (
    <div className="bg-white/5 rounded-xl p-4 mt-2">
      {job.post?.body && (
        <div className="text-xs text-gray-steel leading-6 mb-3 whitespace-pre-wrap line-clamp-4">{job.post.body}</div>
      )}
      <div className="space-y-2">
        {(job.logs || []).map(log => {
          const st = badgeOf(log.status)
          return (
            <div key={log.id} className="flex items-center justify-between gap-3 border-b border-white/5 last:border-0 pb-2 last:pb-0">
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs text-white font-medium shrink-0">{log.platform_name || log.platform_slug}</span>
                <StatusBadge status={log.status} />
                {log.attempt_count > 1 && (
                  <span className="text-[10px] text-gray-steel">
                    {Number(log.attempt_count).toLocaleString('fa-IR')} تلاش
                  </span>
                )}
                {log.status === 'failed' && log.error_message && (
                  <span className="text-[10px] text-red-400 truncate" title={log.error_message}>{log.error_message}</span>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-[10px] text-gray-steel">{formatDate(log.updated_at, { withTime: true })}</span>
                {log.status === 'failed' && (
                  <button onClick={() => retryMut.mutate(log.id)} disabled={retryMut.isPending}
                    className="text-xs text-brand hover:text-brand/80 flex items-center gap-1 disabled:opacity-50">
                    <RefreshCw size={11} /> تلاش مجدد
                  </button>
                )}
              </div>
            </div>
          )
        })}
        {(job.logs || []).length === 0 && <div className="text-xs text-gray-steel">هنوز لاگی ثبت نشده</div>}
      </div>
    </div>
  )
}

// ─── تب ۲: تاریخچه انتشار ────────────────────────────────────
function HistoryTab({ selectedJobId, onSelectJob }) {
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['publisher-jobs'],
    queryFn: publisherService.jobs,
  })

  if (isLoading) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>
  if (jobs.length === 0) return (
    <div className="text-center py-12 text-gray-steel text-sm">هنوز انتشاری ثبت نشده — از تب «محتوای جدید» اولین پست را منتشر کن</div>
  )

  return (
    <div className="space-y-2">
      {jobs.map(job => {
        const open = selectedJobId === job.id
        return (
          <div key={job.id} className="card p-4">
            <button onClick={() => onSelectJob(open ? null : job.id)} className="w-full flex items-center justify-between gap-3 text-right">
              <div className="flex items-center gap-3 min-w-0">
                <ChevronDown size={15} className={`text-gray-steel shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
                <span className="text-sm text-white font-medium truncate">{job.post?.title || job.post_title || `کار ${Number(job.id).toLocaleString('fa-IR')}`}</span>
                <StatusBadge status={job.status} />
              </div>
              <span className="text-[11px] text-gray-steel shrink-0">{formatDate(job.created_at, { withTime: true })}</span>
            </button>
            {open && <JobDetail jobId={job.id} />}
          </div>
        )
      })}
    </div>
  )
}

// ─── تب ۳: تنظیمات پلتفرم‌ها ─────────────────────────────────
const CRED_FIELDS = {
  telegram: ['bot_token'],
  bale: ['bot_token'],
  rubika: ['bot_token'],
  eitaa: ['base_url', 'token'],
  whatsapp: ['session'],
}

const FIELD_LABELS = {
  bot_token: 'توکن ربات',
  base_url: 'آدرس پایه (base_url)',
  token: 'توکن',
  session: 'نشست (session)',
}

function PlatformCard({ platform, credential }) {
  const qc = useQueryClient()
  const fields = CRED_FIELDS[platform.slug] || ['bot_token']
  const [creds, setCreds] = useState(() =>
    Object.fromEntries(fields.map(f => [f, f === 'session' ? 'default' : ''])))
  const [chatId, setChatId] = useState(credential?.chat_id || '')
  const [isActive, setIsActive] = useState(credential?.is_active ?? true)

  const saveMut = useMutation({
    mutationFn: (d) => publisherService.saveCredentials(d),
    onSuccess: () => {
      qc.invalidateQueries(['publisher-credentials'])
      qc.invalidateQueries(['publisher-platforms'])
      toast.success(`تنظیمات ${platform.name} ذخیره شد`)
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره'),
  })

  const submit = () => {
    for (const f of fields) {
      if (f !== 'session' && !creds[f]?.trim()) return toast.error(`${FIELD_LABELS[f] || f} الزامی است`)
    }
    if (!chatId.trim()) return toast.error('شناسه کانال مقصد الزامی است')
    saveMut.mutate({
      platform: platform.id,
      credentials: creds,
      chat_id: chatId,
      is_active: isActive,
    })
  }

  const masked = Array.isArray(credential?.credential_keys) ? credential.credential_keys : []

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-bold text-white">{platform.name}</h3>
        <StatusBadge status={platform.configured ? 'done' : 'failed'} />
      </div>
      <div className="text-[11px] text-gray-steel mb-4">
        {platform.configured ? 'پیکربندی شده' : 'پیکربندی نشده'}
        {credential?.chat_id && <> — کانال: <span dir="ltr">{credential.chat_id}</span></>}
        {masked.length > 0 && (
          <> — کلیدها: {masked.map(k => `${k} (••••)`).join('، ')}</>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {fields.map(f => (
          <div key={f}>
            <label className="label text-xs mb-1 block">{FIELD_LABELS[f] || f}{f !== 'session' ? ' *' : ''}</label>
            <input value={creds[f]} dir="ltr"
              onChange={e => setCreds(c => ({ ...c, [f]: e.target.value }))}
              className="input text-sm font-mono text-left"
              placeholder={credential ? 'برای تغییر، مقدار جدید وارد کنید' : ''} />
          </div>
        ))}
        <div>
          <label className="label text-xs mb-1 block">شناسه کانال مقصد *</label>
          <input value={chatId} dir="ltr" onChange={e => setChatId(e.target.value)}
            className="input text-sm font-mono text-left" placeholder="@channel یا -100..." />
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-steel hover:text-white">
            <CheckBox checked={isActive} onToggle={() => setIsActive(v => !v)} />
            فعال
          </label>
        </div>
      </div>

      <button onClick={submit} disabled={saveMut.isPending}
        className="btn-primary text-sm px-5 py-2 disabled:opacity-50">
        {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره'}
      </button>
    </div>
  )
}

// ─── راهنمای دریافت توکن هر پلتفرم ─────────────────────────────
const GUIDE = [
  {
    name: 'تلگرام',
    steps: [
      'در تلگرام به @BotFather پیام بده و دستور /newbot را بفرست؛ بعد از انتخاب نام، یک توکن مثل 123456:ABC-DEF... به تو می‌دهد → همان را در فیلد bot_token بگذار.',
      'ربات را در کانال خودت **ادمین** کن (با دسترسی ارسال پست).',
      'chat_id: یوزرنیم کانال با @ (مثل @doorbinkar). برای کانال خصوصی، یک پست در کانال بگذار و به @userinfobot فوروارد کن تا آی‌دی عددی (مثل -100...) را بدهد.',
    ],
  },
  {
    name: 'بله',
    steps: [
      'در پیام‌رسان بله به «بله‌بات» (@BotFather در بله) پیام بده و ربات بساز؛ توکن را در فیلد bot_token بگذار.',
      'ربات را در کانال بله ادمین کن.',
      'chat_id: یوزرنیم کانال با @ — دقیقاً مثل تلگرام.',
    ],
  },
  {
    name: 'روبیکا',
    steps: [
      'در روبیکا وارد «روبیکا پنل» (bot.rubika.ir) شو و یک ربات بساز؛ توکن را در bot_token بگذار.',
      'ربات را در کانال روبیکا ادمین کن.',
      'chat_id: شناسه کانال (یوزرنیم با @ یا guid که روبیکا می‌دهد).',
    ],
  },
  {
    name: 'ایتا',
    steps: [
      'ایتا API رسمی عمومی ندارد؛ باید از یک سرویس دروازه (gateway) مثل eitaayar.ir حساب بگیری.',
      'از پنل gateway آدرس API را در base_url (مثل https://eitaayar.ir/api) و توکن را در token بگذار.',
      'chat_id: آی‌دی عددی کانال که پنل gateway نشان می‌دهد.',
    ],
  },
  {
    name: 'واتساپ',
    steps: [
      'فعلاً غیرفعال است — نیاز به راه‌اندازی WAHA روی سرور آمریکا دارد. با مدیر سیستم هماهنگ کن.',
    ],
  },
]

function PlatformGuide() {
  const [open, setOpen] = useState(false)
  return (
    <div className="card p-5 col-span-2">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between text-right">
        <span className="flex items-center gap-2 font-bold text-white text-sm">
          <HelpCircle size={16} className="text-brand" />
          راهنمای دریافت توکن و شناسه کانال
        </span>
        <span className="flex items-center gap-1 text-xs text-brand">
          {open ? 'بستن' : 'مشاهده بیشتر'}
          <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>
      {open && (
        <div className="mt-4 space-y-4 text-xs leading-6 text-gray-steel">
          {GUIDE.map(g => (
            <div key={g.name}>
              <div className="font-bold text-white mb-1">{g.name}</div>
              <ol className="list-decimal pr-4 space-y-1">
                {g.steps.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </div>
          ))}
          <p className="border-t border-white/10 pt-3">
            نکته: توکن‌ها به‌صورت رمزنگاری‌شده ذخیره می‌شوند و بعد از ذخیره، مقدارشان دیگر نمایش داده نمی‌شود — فقط نام کلیدها را می‌بینی. برای تغییر، مقدار جدید را وارد و ذخیره کن.
          </p>
        </div>
      )}
    </div>
  )
}

function SettingsTab() {
  const { data: platforms = [], isLoading: loadingPlatforms } = useQuery({
    queryKey: ['publisher-platforms'],
    queryFn: publisherService.platforms,
  })
  const { data: credentials = [], isLoading: loadingCreds } = useQuery({
    queryKey: ['publisher-credentials'],
    queryFn: publisherService.credentials,
  })

  if (loadingPlatforms || loadingCreds) return <div className="text-center py-8 text-gray-steel">در حال بارگذاری...</div>

  const credByPlatform = Object.fromEntries(credentials.map(c => [c.platform_id, c]))

  return (
    <div className="grid grid-cols-2 gap-4">
      <PlatformGuide />
      {platforms.map(p => (
        <PlatformCard key={p.id} platform={p} credential={credByPlatform[p.id]} />
      ))}
      {platforms.length === 0 && (
        <div className="col-span-2 text-center py-12 text-gray-steel text-sm">هیچ پلتفرمی تعریف نشده است</div>
      )}
    </div>
  )
}

// ─── صفحه اصلی ────────────────────────────────────────────────
export default function AdminPublisherPage() {
  const { can } = usePermissions()
  const [tab, setTab] = useState('compose')
  const [selectedJobId, setSelectedJobId] = useState(null)
  const canManageCreds = can('publisher_credentials')

  const tabs = [
    ['compose', 'محتوای جدید', Send],
    ['history', 'تاریخچه انتشار', History],
    ...(canManageCreds ? [['settings', 'تنظیمات پلتفرم‌ها', Settings]] : []),
  ]

  return (
    <div className="container-main py-8 max-w-5xl">
      <h1 className="font-display font-bold text-2xl text-white mb-2">انتشار در پیام‌رسان‌ها</h1>
      <div className="text-xs text-gray-steel mb-6">
        محتوا را یک جا بنویس و همزمان در تلگرام، بله، روبیکا، ایتا و واتساپ منتشر کن.
      </div>

      <div className="flex gap-2 mb-6 border-b border-white/10">
        {tabs.map(([k, v, Icon]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all flex items-center gap-2 ${tab === k ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            <Icon size={15} /> {v}
          </button>
        ))}
      </div>

      {tab === 'compose' && (
        <ComposeTab onPublished={(jobId) => { setSelectedJobId(jobId); setTab('history') }} />
      )}
      {tab === 'history' && <HistoryTab selectedJobId={selectedJobId} onSelectJob={setSelectedJobId} />}
      {tab === 'settings' && canManageCreds && <SettingsTab />}
    </div>
  )
}
