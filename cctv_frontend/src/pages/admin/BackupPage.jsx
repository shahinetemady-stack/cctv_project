import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }
function fmtDate(s) { return s ? new Date(s).toLocaleString('fa-IR') : 'هرگز' }

const STATUS_COLORS = {
  success: '#00C896',
  partial: '#FF9500',
  failed:  '#FF3B3B',
}

// ═══════════════════════════════════════════════════════════════
// Restore Section
// ═══════════════════════════════════════════════════════════════
function RestoreSection() {
  const [file, setFile] = useState(null)
  const [staged, setStaged] = useState(null)
  const [confirmText, setConfirmText] = useState('')
  const [restoreDb, setRestoreDb] = useState(true)
  const [restoreMedia, setRestoreMedia] = useState(true)
  const [msg, setMsg] = useState(null)

  const uploadMut = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('backup_file', file)
      return api.post('/accounting/backup/restore/upload/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(r => r.data)
    },
    onSuccess: (d) => {
      setStaged(d.staged)
      setMsg({ type: 'success', text: 'فایل آماده شد. حالا گزینه‌ها را انتخاب کنید.' })
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در آپلود' }),
  })

  const restoreMut = useMutation({
    mutationFn: () => api.post('/accounting/backup/restore/execute/', {
      confirm: confirmText, staged_path: staged.path,
      restore_db: restoreDb, restore_media: restoreMedia,
    }).then(r => r.data),
    onSuccess: (d) => {
      setMsg({
        type: 'success',
        text: `✅ بازیابی موفق! ${d.note}\n${d.safety_log_id ? `safety backup #${d.safety_log_id}` : ''}`
      })
      setStaged(null)
      setConfirmText('')
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  return (
    <div className="card p-5 mb-6" style={{ borderRight: '4px solid #FF6B6B' }}>
      <h2 className="text-base font-bold text-white mb-3">🔄 بازیابی اطلاعات</h2>
      <div className="text-xs text-gray-steel mb-4 leading-6 bg-red-500/10 p-3 rounded">
        ⚠️ <strong>قبل از این کار سرور Django را stop کنید</strong> تا فایل دیتابیس قفل نباشد.<br/>
        خودکار یک safety backup قبل از بازیابی گرفته می‌شود.
      </div>

      {msg && (
        <div className={`rounded-lg px-3 py-2 text-xs mb-3 whitespace-pre-line ${
          msg.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>{msg.text}</div>
      )}

      {!staged ? (
        <div>
          <label className="label text-xs mb-1 block">انتخاب فایل ZIP بک‌اپ</label>
          <input type="file" accept=".zip"
            onChange={e => setFile(e.target.files[0])}
            className="input text-xs w-full" />
          <button
            onClick={() => file && uploadMut.mutate()}
            disabled={!file || uploadMut.isPending}
            className="btn-primary text-xs mt-3 px-4 py-2 disabled:opacity-50">
            {uploadMut.isPending ? 'در حال آپلود...' : '📤 آپلود و بررسی'}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-white/5 p-3 rounded text-xs">
            <div className="text-white"><b>📦 فایل:</b> {staged.name} ({staged.size_mb} MB)</div>
            <div className="text-gray-steel mt-1">📅 ساخته شده: {staged.manifest?.created_at || '—'}</div>
            <div className="text-gray-steel">🗜 فشرده‌سازی: {staged.manifest?.compression || '—'}</div>
            <div className="text-gray-steel">📁 تعداد فایل‌ها: {staged.manifest?.files_added || '—'}</div>
          </div>
          <div className="flex gap-4">
            <label className="text-xs text-gray-steel flex items-center gap-2">
              <input type="checkbox" checked={restoreDb} onChange={e => setRestoreDb(e.target.checked)} />
              بازیابی دیتابیس
            </label>
            <label className="text-xs text-gray-steel flex items-center gap-2">
              <input type="checkbox" checked={restoreMedia} onChange={e => setRestoreMedia(e.target.checked)} />
              بازیابی media
            </label>
          </div>
          <div className="flex gap-2 items-center">
            <input value={confirmText} onChange={e => setConfirmText(e.target.value)}
              placeholder="تایپ کنید: RESTORE"
              className="input text-xs flex-1" />
            <button
              onClick={() => {
                if (confirm('⚠️ غیر قابل بازگشت! مطمئنید؟')) restoreMut.mutate()
              }}
              disabled={confirmText !== 'RESTORE' || restoreMut.isPending}
              className="bg-red-500 text-white text-xs px-4 py-2 rounded disabled:opacity-30">
              🔄 شروع بازیابی
            </button>
            <button onClick={() => { setStaged(null); setConfirmText('') }}
              className="btn-secondary text-xs px-3 py-2">انصراف</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// System Reset Section — فقط superuser، سه تایید مرحله‌ای
// ═══════════════════════════════════════════════════════════════
function ResetSection() {
  const [mode, setMode] = useState(null)      // 'soft' | 'hard'
  const [ack1, setAck1] = useState(false)
  const [ack2, setAck2] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [msg, setMsg] = useState(null)
  const [report, setReport] = useState(null)

  const resetMut = useMutation({
    mutationFn: () => api.post('/accounting/system-reset/', {
      mode, confirm: confirmText,
    }).then(r => r.data),
    onSuccess: (d) => {
      setReport(d)
      setMsg(null)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا در ریست' }),
  })

  const ready = mode && ack1 && ack2 && confirmText === 'RESET'

  const MODES = {
    soft: {
      title: 'حالت ۱ — پاک شدن تراکنش‌ها',
      desc: 'فاکتورهای خرید و فروش، دریافت و پرداخت‌ها، سفارش‌های سایت و حرکات کاردکس حذف و موجودی انبار، مانده اول دوره اشخاص و موجودی بانک‌ها صفر می‌شود.',
      keep: '✅ می‌ماند: طرف حساب‌ها، کالاها و دسته‌بندی‌ها، حساب‌های بانکی، کاربران، نقش‌ها',
      color: '#FF9500',
    },
    hard: {
      title: 'حالت ۲ — ریست کامل (پاک شدن همه اطلاعات ورودی)',
      desc: 'همه چیز پاک می‌شود: تراکنش‌ها، طرف حساب‌ها، حساب‌های بانکی، محصولات، دسته‌بندی‌ها، پکیج‌ها و کاربران غیر superuser.',
      keep: '✅ می‌ماند: فقط superuserها، انبارها، نرخ یوان و تنظیمات SEO',
      color: '#FF3B3B',
    },
  }

  if (report) {
    return (
      <div className="card p-5 mb-6" style={{ borderRight: '4px solid #00C896' }}>
        <h2 className="text-base font-bold text-green-400 mb-3">✅ ریست انجام شد ({report.mode === 'soft' ? 'حالت ۱' : 'حالت ۲ — کامل'})</h2>
        <div className="text-xs text-gray-steel space-y-1 mb-3">
          {Object.entries(report.report || {}).map(([k, v]) => (
            <div key={k}>• {k}: <b className="text-white">{Number(v).toLocaleString('fa-IR')}</b></div>
          ))}
        </div>
        {report.safety && (
          <div className="text-xs text-blue-300 bg-blue-500/10 rounded px-3 py-2">🛡 {report.safety} — از تاریخچه بک‌اپ قابل بازیابی است</div>
        )}
        <button onClick={() => window.location.reload()} className="btn-primary text-xs px-4 py-2 mt-4">بارگذاری مجدد صفحه</button>
      </div>
    )
  }

  return (
    <div className="card p-5 mb-6" style={{ borderRight: '4px solid #FF3B3B' }}>
      <h2 className="text-base font-bold text-white mb-2">🗑 ریست سیستم</h2>
      <div className="text-xs text-red-300 bg-red-500/10 p-3 rounded mb-4 leading-6">
        ⚠️ این عمل <strong>غیرقابل بازگشت</strong> است و فقط با بازیابی بک‌اپ می‌توان برگشت.
        قبل از ریست، به‌صورت خودکار یک <strong>safety backup</strong> گرفته می‌شود.
      </div>

      {msg && (
        <div className="rounded-lg px-3 py-2 text-xs mb-3 bg-red-500/20 text-red-400">{msg.text}</div>
      )}

      {/* انتخاب حالت */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        {Object.entries(MODES).map(([k, m]) => (
          <button key={k} onClick={() => setMode(k)}
            className={`text-right rounded-xl border p-4 transition-all ${
              mode === k ? 'border-red-400 bg-red-500/10' : 'border-white/10 hover:border-white/30'
            }`}>
            <div className="text-sm font-bold mb-1" style={{ color: m.color }}>{m.title}</div>
            <div className="text-[11px] text-gray-steel leading-5">{m.desc}</div>
            <div className="text-[11px] text-green-400 mt-2">{m.keep}</div>
          </button>
        ))}
      </div>

      {/* سه تایید مرحله‌ای */}
      {mode && (
        <div className="space-y-3 bg-white/5 rounded-xl p-4">
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={ack1} onChange={e => setAck1(e.target.checked)} />
            <span><b className="text-white">تایید اول:</b> می‌دانم این عمل غیرقابل بازگشت است و داده‌های حذف‌شده فقط با بک‌اپ برمی‌گردند.</span>
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={ack2} onChange={e => setAck2(e.target.checked)} />
            <span><b className="text-white">تایید دوم:</b> لیست موارد حذف‌شده در «{MODES[mode].title}» را خواندم و می‌پذیرم.</span>
          </label>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-steel"><b className="text-white">تایید سوم:</b> کلمه RESET را تایپ کنید</span>
            <input value={confirmText} onChange={e => setConfirmText(e.target.value)}
              placeholder="RESET" dir="ltr"
              className="input text-xs w-32 text-center" />
            <button onClick={() => resetMut.mutate()} disabled={!ready || resetMut.isPending}
              className="bg-red-500 text-white text-xs px-5 py-2 rounded-lg font-bold disabled:opacity-30">
              {resetMut.isPending ? '⏳ در حال ریست...' : '🗑 اجرای ریست'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════════
export default function BackupPage() {
  const qc = useQueryClient()
  const [msg, setMsg] = useState(null)
  const [showRestore, setShowRestore] = useState(false)
  const [showReset, setShowReset] = useState(false)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['backup-settings'],
    queryFn: () => api.get('/accounting/backup/settings/').then(r => r.data),
  })

  const { data: logs = [] } = useQuery({
    queryKey: ['backup-logs'],
    queryFn: () => api.get('/accounting/backup/logs/').then(r => r.data),
  })

  const [form, setForm] = useState(null)

  // مقداردهی اولیه فرم با دریافت تنظیمات
  if (settings && !form) {
    setForm(settings)
  }

  const saveMut = useMutation({
    mutationFn: (d) => api.post('/accounting/backup/settings/', d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries(['backup-settings'])
      setMsg({ type: 'success', text: '✅ تنظیمات ذخیره شد' })
      setTimeout(() => setMsg(null), 3000)
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  const runMut = useMutation({
    mutationFn: (is_daily) => api.post('/accounting/backup/run/', { is_daily }).then(r => r.data),
    onSuccess: (d) => {
      qc.invalidateQueries(['backup-logs'])
      qc.invalidateQueries(['backup-settings'])
      const log = d.log
      if (log.status === 'success') {
        const ch = [log.sent_email && 'ایمیل', log.sent_telegram && 'تلگرام'].filter(Boolean).join(' و ')
        setMsg({ type: 'success', text: `✅ بک‌اپ گرفته شد — ${log.file_size_mb}MB${ch ? ` (${ch})` : ''}\n📁 ${log.file_path}` })
      } else {
        setMsg({ type: log.status === 'partial' ? 'warning' : 'error', text: log.error || 'خطا' })
      }
    },
    onError: (e) => setMsg({ type: 'error', text: e.response?.data?.error || 'خطا' }),
  })

  async function browsePath() {
    try {
      const r = await api.get('/accounting/backup/browse/')
      const data = r.data
      if (data.path) {
        setForm(f => ({ ...f, backup_path: data.path }))
        alert(`📁 مسیر انتخاب شد:\n${data.path}\n\n⚠️ برای اعمال، دکمه «ذخیره تنظیمات» را بزنید!`)
      }
    } catch (e) {
      alert('خطا: ' + (e.response?.data?.error || e.message))
    }
  }

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  if (isLoading || !form) {
    return <div className="container-main py-8 text-center text-gray-steel">در حال بارگذاری...</div>
  }

  return (
    <div className="container-main py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">📦 سیستم بک‌اپ</h1>
        <div className="flex gap-2">
          <button onClick={() => { setShowRestore(s => !s); setShowReset(false) }}
            className="btn-secondary text-sm px-4 py-2">
            {showRestore ? '✕ بستن بازیابی' : '🔄 بازیابی اطلاعات'}
          </button>
          <button onClick={() => { setShowReset(s => !s); setShowRestore(false) }}
            className="text-sm px-4 py-2 rounded-lg border border-red-500/40 text-red-400 hover:bg-red-500/10 transition-colors">
            {showReset ? '✕ بستن ریست' : '🗑 ریست سیستم'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="card p-3 text-center">
          <div className="text-xs text-gray-steel">آخرین بک‌اپ ساعتی</div>
          <div className="text-sm font-bold text-white mt-1">🕐 {fmtDate(form.last_backup_at)}</div>
        </div>
        <div className="card p-3 text-center">
          <div className="text-xs text-gray-steel">آخرین بک‌اپ روزانه</div>
          <div className="text-sm font-bold text-white mt-1">📅 {fmtDate(form.last_daily_backup_at)}</div>
        </div>
      </div>

      {msg && (
        <div className={`rounded-lg px-4 py-3 text-sm mb-4 whitespace-pre-line ${
          msg.type === 'success' ? 'bg-green-500/20 text-green-400' :
          msg.type === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
          'bg-red-500/20 text-red-400'
        }`}>{msg.text}</div>
      )}

      {showRestore && <RestoreSection />}
      {showReset && <ResetSection />}

      {/* بک‌اپ دستی */}
      <div className="card p-5 mb-6 text-center">
        <h2 className="font-semibold text-sm text-white mb-3">گرفتن بک‌اپ دستی</h2>
        <div className="flex justify-center gap-3">
          <button onClick={() => { if (confirm('شروع شود؟')) runMut.mutate(false) }}
            disabled={runMut.isPending}
            className="bg-green-500 text-white px-6 py-3 rounded-lg text-sm font-bold disabled:opacity-50">
            📥 بک‌اپ ساعتی
          </button>
          <button onClick={() => { if (confirm('شروع شود؟')) runMut.mutate(true) }}
            disabled={runMut.isPending}
            className="bg-purple-500 text-white px-6 py-3 rounded-lg text-sm font-bold disabled:opacity-50">
            📅 بک‌اپ روزانه (با media)
          </button>
        </div>
      </div>

      {/* مسیر + کاهش حجم */}
      <div className="card p-5 mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">📁 مسیر و کاهش حجم</h2>
        <div className="mb-3">
          <label className="label text-xs mb-1 block">مسیر ذخیره *</label>
          <div className="flex gap-2">
            <input value={form.backup_path || ''} onChange={e => set('backup_path', e.target.value)}
              placeholder="D:\\backups"
              className="input text-sm flex-1" />
            <button type="button" onClick={browsePath}
              className="btn-primary text-xs px-4 py-2 whitespace-nowrap">📂 انتخاب پوشه</button>
          </div>
          <div className="text-[11px] text-gray-steel mt-1">پوشه‌ای که فایل‌های ZIP بک‌اپ در آن ذخیره می‌شوند</div>
        </div>

        <div className="bg-blue-500/10 border-r-2 border-blue-500 p-3 rounded text-xs text-blue-300 leading-6 mb-3">
          💡 <b>برای کاهش حجم بک‌اپ:</b>
          <ul className="list-disc list-inside mt-1">
            <li>LZMA: 30-50٪ کوچک‌تر</li>
            <li>VACUUM: حذف فضای خالی SQLite</li>
            <li>بک‌اپ ساعتی بدون media: media را فقط در روزانه نگه دارید</li>
          </ul>
        </div>

        <div className="space-y-2">
          {[
            ['use_lzma_compression', '🗜 فشرده‌سازی LZMA (پیشنهادی)'],
            ['vacuum_sqlite_before_backup', '⚡ VACUUM SQLite قبل از بک‌اپ'],
            ['include_media_in_hourly', '📷 بک‌اپ ساعتی شامل media (توصیه: خاموش)'],
            ['include_media_in_daily', '📷 بک‌اپ روزانه شامل media (توصیه: روشن)'],
            ['safety_backup_enabled', '🛡 بک‌اپ خودکار قبل از ریست/بازیابی'],
          ].map(([k, label]) => (
            <label key={k} className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
              <input type="checkbox" checked={!!form[k]} onChange={e => set(k, e.target.checked)} />
              {label}
            </label>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <label className="label text-xs mb-1 block">حداکثر بک‌اپ ساعتی</label>
            <input type="number" min="1" value={form.keep_count || 10}
              onChange={e => set('keep_count', Number(e.target.value))}
              className="input text-xs" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">حداکثر بک‌اپ روزانه</label>
            <input type="number" min="1" value={form.daily_keep_count || 30}
              onChange={e => set('daily_keep_count', Number(e.target.value))}
              className="input text-xs" />
          </div>
        </div>
      </div>

      {/* بک‌اپ خودکار */}
      <div className="card p-5 mb-4">
        <h2 className="text-sm font-semibold text-white mb-3">⏰ بک‌اپ خودکار (Windows Task Scheduler)</h2>
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={!!form.is_auto_enabled} onChange={e => set('is_auto_enabled', e.target.checked)} />
            بک‌اپ ساعتی فعال
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-steel cursor-pointer">
            <input type="checkbox" checked={!!form.daily_backup_enabled} onChange={e => set('daily_backup_enabled', e.target.checked)} />
            📅 بک‌اپ روزانه فعال
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <label className="label text-xs mb-1 block">بازه ساعتی</label>
            <input type="number" min="1" max="168" value={form.interval_hours || 1}
              onChange={e => set('interval_hours', Number(e.target.value))}
              className="input text-xs" />
          </div>
          <div>
            <label className="label text-xs mb-1 block">ساعت روزانه (HH:MM)</label>
            <input value={form.daily_backup_time || '23:30'}
              onChange={e => set('daily_backup_time', e.target.value)}
              className="input text-xs" />
          </div>
        </div>
        <div className="bg-yellow-500/10 border-r-2 border-yellow-500 p-3 rounded text-[11px] text-yellow-300 leading-6 mt-3">
          برای فعال‌سازی، در Windows Task Scheduler دو task بسازید:<br/>
          <code className="text-white bg-black/30 px-2 py-0.5 rounded">python manage.py run_backup --trigger auto</code> (ساعتی)<br/>
          <code className="text-white bg-black/30 px-2 py-0.5 rounded">python manage.py run_daily_backup</code> (روزانه)
        </div>
      </div>

      {/* ایمیل + تلگرام */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-3">📧 ایمیل</h2>
          <label className="flex items-center gap-2 text-xs text-gray-steel mb-3 cursor-pointer">
            <input type="checkbox" checked={!!form.email_enabled} onChange={e => set('email_enabled', e.target.checked)} />
            فعال
          </label>
          <input type="email" value={form.email_to || ''} onChange={e => set('email_to', e.target.value)}
            placeholder="me@example.com" className="input text-xs" />
        </div>

        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-3">📲 تلگرام</h2>
          <label className="flex items-center gap-2 text-xs text-gray-steel mb-3 cursor-pointer">
            <input type="checkbox" checked={!!form.telegram_enabled} onChange={e => set('telegram_enabled', e.target.checked)} />
            فعال
          </label>
          <input value={form.telegram_token || ''} onChange={e => set('telegram_token', e.target.value)}
            placeholder="توکن ربات" className="input text-xs mb-2" />
          <input value={form.telegram_chat_id || ''} onChange={e => set('telegram_chat_id', e.target.value)}
            placeholder="Chat ID" className="input text-xs" />
        </div>
      </div>

      {/* دکمه ذخیره */}
      <div className="card p-5 mb-6 text-center">
        <button onClick={() => saveMut.mutate(form)} disabled={saveMut.isPending}
          className="btn-primary px-8 py-3 font-bold disabled:opacity-50">
          {saveMut.isPending ? 'در حال ذخیره...' : '💾 ذخیره تنظیمات'}
        </button>
      </div>

      {/* تاریخچه */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-white mb-3">📋 تاریخچه آخرین بک‌اپ‌ها</h2>
        {logs.length === 0 ? (
          <div className="text-center py-8 text-gray-steel text-xs">هنوز بک‌اپی نیست</div>
        ) : (
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.1)' }}>
                  {['تاریخ', 'دسته', 'وضعیت', 'منبع', 'اندازه', 'ارسال', 'توضیحات'].map(h => (
                    <th key={h} style={{ padding: '8px', textAlign: 'right', color: 'var(--color-text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map((log, i) => {
                  const ch = []
                  if (log.sent_email) ch.push('📧')
                  if (log.sent_telegram) ch.push('📲')
                  const kind = log.is_daily ? '📅 روزانه' : log.trigger === 'safety' ? '🛡 ایمنی' : '⏰ ساعتی'
                  return (
                    <tr key={log.id} style={{
                      borderBottom: '0.5px solid rgba(255,255,255,0.05)',
                      background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent',
                    }}>
                      <td style={{ padding: '8px', fontSize: 11 }}>{fmtDate(log.created_at)}</td>
                      <td style={{ padding: '8px', fontSize: 11 }}>{kind}</td>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          color: STATUS_COLORS[log.status] || '#888',
                          fontWeight: 'bold',
                        }}>{log.status_display}</span>
                      </td>
                      <td style={{ padding: '8px', fontSize: 11 }}>{log.trigger_display}</td>
                      <td style={{ padding: '8px', fontSize: 11 }}>{log.file_size_mb || '—'} MB</td>
                      <td style={{ padding: '8px', textAlign: 'center' }}>{ch.join(' ') || '—'}</td>
                      <td style={{ padding: '8px', fontSize: 10, color: '#888' }}>
                        {log.error?.slice(0, 60) || log.note || '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
