import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

// ─── قالب‌های موجود ──────────────────────────────────────────
const THEMES = [
  {
    id: 'explode',
    name: 'مونتاژ قطعات',
    desc: 'اسکرول سینماتیک — قطعات دوربین با اسکرول مونتاژ می‌شوند',
    icon: '🔧',
    preview: 'bg-black',
    gradient: 'linear-gradient(135deg, #050505, #1a1a1a)',
    accent: '#ffa500',
  },
  {
    id: 'video',
    name: 'ویدیو فول‌صفحه',
    desc: 'ویدیوی دوربین به عنوان پس‌زمینه با parallax اسکرول',
    icon: '🎬',
    gradient: 'linear-gradient(135deg, #0a0a0a, #1a0a00)',
    accent: '#ffa500',
  },
  {
    id: 'minimal',
    name: 'مینیمال',
    desc: 'ساده و حرفه‌ای — محصولات در اولویت',
    icon: '⬜',
    gradient: 'linear-gradient(135deg, #f8f8f8, #e8e8e8)',
    accent: '#333',
  },
]

// ─── قطعات پیش‌فرض Hero ──────────────────────────────────────
const DEFAULT_PARTS = [
  { id: 'body',  label: 'بدنه آلومینیوم',  spec: 'IP67 | ضدآب | ضدضربه',      file: 'cam_body.png' },
  { id: 'pcb',   label: 'برد اصلی PCB',    spec: 'HiSilicon Hi3516 | 4 لایه',  file: 'cam_pcb.jpg' },
  { id: 'lens',  label: 'لنز اصلی',         spec: '3.6mm | F1.6 | M12',         file: 'cam_lens.jpg' },
  { id: 'lens2', label: 'هولدر لنز',        spec: 'M12 Mount | آلومینیوم',      file: 'cam_lens2.jpg' },
  { id: 'parts', label: 'ماژول LED + PCB', spec: 'Warm Light | 3000K | IP65',   file: 'cam_parts.jpg' },
]

export default function ThemeSettingsPage() {
  const [activeTab, setActiveTab] = useState('theme')
  const [selectedTheme, setSelectedTheme] = useState(() => localStorage.getItem('site_theme') || 'explode')
  const [parts, setParts] = useState(() => {
    try { return JSON.parse(localStorage.getItem('hero_parts_config')) || DEFAULT_PARTS } catch { return DEFAULT_PARTS }
  })
  const [saved, setSaved] = useState(false)
  const [uploadingId, setUploadingId] = useState(null)

  function saveTheme() {
    localStorage.setItem('site_theme', selectedTheme)
    localStorage.setItem('hero_parts_config', JSON.stringify(parts))
    setSaved(true)
    // اطلاع به سایر tab ها
    window.dispatchEvent(new StorageEvent('storage', { key: 'site_theme', newValue: selectedTheme }))
    setTimeout(() => setSaved(false), 2000)
  }

  async function uploadImage(partId, file) {
    setUploadingId(partId)
    try {
      const fd = new FormData()
      fd.append('image', file)
      fd.append('folder', 'hero')
      // آپلود به پوشه public/images
      const res = await api.post('/core/upload-image/', fd)
      const filename = res.data.filename
      setParts(prev => prev.map(p =>
        p.id === partId ? { ...p, file: filename, img: `/images/${filename}` } : p
      ))
    } catch (e) {
      alert('خطا در آپلود: ' + (e.response?.data?.error || e.message))
    }
    setUploadingId(null)
  }

  // آپلود دستی با URL
  function setPartFile(partId, filename) {
    setParts(prev => prev.map(p =>
      p.id === partId ? { ...p, file: filename } : p
    ))
  }

  function updatePart(partId, field, value) {
    setParts(prev => prev.map(p =>
      p.id === partId ? { ...p, [field]: value } : p
    ))
  }

  function resetToDefault() {
    if (window.confirm('آیا مطمئنید؟ تمام تنظیمات به حالت پیش‌فرض برمی‌گردد.')) {
      setParts(DEFAULT_PARTS)
      setSelectedTheme('explode')
    }
  }

  const tabs = [
    { id: 'theme', label: '🎨 انتخاب قالب' },
    { id: 'hero', label: '🔧 قطعات Hero' },
    { id: 'content', label: '📝 محتوای قالب' },
  ]

  return (
    <div className="container-main py-8 max-w-4xl" dir="rtl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-2xl text-white">🎨 تنظیمات قالب سایت</h1>
          <p className="text-sm text-gray-steel mt-1">انتخاب قالب و تنظیم تصاویر Hero Section</p>
        </div>
        <div className="flex gap-3">
          <button onClick={resetToDefault}
            className="btn-secondary text-xs px-4 py-2">
            ↺ بازگشت به پیش‌فرض
          </button>
          <button onClick={saveTheme}
            className={`text-sm px-6 py-2 rounded-xl font-semibold transition-all ${saved ? 'bg-green-500 text-white' : 'btn-primary'}`}>
            {saved ? '✓ ذخیره شد!' : 'ذخیره تنظیمات'}
          </button>
        </div>
      </div>

      {/* tabs */}
      <div className="flex gap-2 mb-6 border-b border-white/10">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`text-sm px-5 py-2.5 rounded-t-lg border-b-2 transition-all ${activeTab === t.id ? 'border-brand text-white bg-brand/10' : 'border-transparent text-gray-steel hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── تب انتخاب قالب ── */}
      {activeTab === 'theme' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-steel mb-4">قالب صفحه اصلی سایت را انتخاب کنید:</p>
          <div className="grid grid-cols-3 gap-4">
            {THEMES.map(theme => (
              <button key={theme.id} onClick={() => setSelectedTheme(theme.id)}
                className={`card p-0 overflow-hidden text-right transition-all ${selectedTheme === theme.id ? 'border-brand ring-1 ring-brand' : 'hover:border-white/20'}`}>
                {/* preview */}
                <div style={{
                  height: 120,
                  background: theme.gradient,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 36,
                  position: 'relative',
                }}>
                  {theme.icon}
                  {selectedTheme === theme.id && (
                    <div style={{
                      position: 'absolute', top: 8, left: 8,
                      background: '#0066FF', borderRadius: '50%',
                      width: 20, height: 20,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 12, color: 'white',
                    }}>✓</div>
                  )}
                  {/* demo dots */}
                  <div style={{
                    position: 'absolute', bottom: 10, right: 10, left: 10,
                    display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end',
                  }}>
                    <div style={{ background: theme.accent, height: 2, width: '60%', borderRadius: 1, opacity: 0.7 }}/>
                    <div style={{ background: 'rgba(255,255,255,0.2)', height: 2, width: '80%', borderRadius: 1 }}/>
                    <div style={{ background: 'rgba(255,255,255,0.1)', height: 2, width: '40%', borderRadius: 1 }}/>
                  </div>
                </div>
                <div className="p-4">
                  <div className="font-semibold text-white text-sm mb-1">{theme.name}</div>
                  <div className="text-xs text-gray-steel leading-relaxed">{theme.desc}</div>
                </div>
              </button>
            ))}
          </div>

          <div className="card p-4 mt-4">
            <div className="text-xs text-gray-steel">
              <strong className="text-white">قالب فعال:</strong> {THEMES.find(t => t.id === selectedTheme)?.name}
              {' '} — بعد از ذخیره، صفحه اصلی آپدیت می‌شود.
            </div>
          </div>
        </div>
      )}

      {/* ── تب قطعات Hero ── */}
      {activeTab === 'hero' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-steel mb-2">
            تصاویر قطعات دوربین در Hero Section را تغییر دهید.
            <span className="text-white"> PNG با پس‌زمینه شفاف پیشنهاد می‌شود.</span>
          </p>

          {parts.map((part) => (
            <div key={part.id} className="card p-5">
              <div className="flex items-start gap-4">
                {/* preview تصویر */}
                <div style={{
                  width: 80, height: 80,
                  background: '#111',
                  borderRadius: 8,
                  border: '0.5px solid rgba(255,255,255,0.1)',
                  flexShrink: 0,
                  overflow: 'hidden',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <img
                    src={`/images/${part.file}`}
                    alt={part.label}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    onError={e => { e.target.src = '/images/' + part.file.replace('.jpg', '.png').replace('.png', '.jpg') }}
                  />
                </div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-steel px-2 py-1 bg-white/5 rounded-lg font-mono">{part.id}</span>
                    <span className="text-sm font-semibold text-white">{part.label}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="label text-xs mb-1 block">نام نمایشی</label>
                      <input
                        value={part.label}
                        onChange={e => updatePart(part.id, 'label', e.target.value)}
                        className="input text-sm"
                      />
                    </div>
                    <div>
                      <label className="label text-xs mb-1 block">مشخصات فنی</label>
                      <input
                        value={part.spec}
                        onChange={e => updatePart(part.id, 'spec', e.target.value)}
                        className="input text-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="label text-xs mb-1 block">نام فایل تصویر</label>
                    <div className="flex gap-2 items-center">
                      <input
                        value={part.file}
                        onChange={e => updatePart(part.id, 'file', e.target.value)}
                        className="input text-sm flex-1 font-mono"
                        placeholder="cam_body.png"
                        dir="ltr"
                      />
                      <label className={`cursor-pointer text-xs px-3 py-2 rounded-lg transition-all ${uploadingId === part.id ? 'bg-white/5 text-gray-steel' : 'bg-brand/20 text-brand hover:bg-brand/30'}`}>
                        {uploadingId === part.id ? 'در حال آپلود...' : '⬆️ آپلود'}
                        <input
                          type="file"
                          accept="image/*"
                          className="hidden"
                          disabled={uploadingId !== null}
                          onChange={e => {
                            const file = e.target.files[0]
                            if (file) uploadImage(part.id, file)
                          }}
                        />
                      </label>
                    </div>
                    <div className="text-[10px] text-gray-steel mt-1 font-mono">
                      مسیر: /public/images/{part.file}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}

          <div className="card p-4 bg-blue-500/5 border-blue-500/20">
            <div className="text-xs text-blue-400 leading-relaxed">
              💡 <strong>راهنما:</strong> فایل‌های تصویر را در پوشه{' '}
              <span className="font-mono text-white">cctv_frontend/public/images/</span> قرار دهید.
              PNG با پس‌زمینه شفاف (transparent) بهترین نتیجه را می‌دهد.
            </div>
          </div>
        </div>
      )}

      {/* ── تب محتوا ── */}
      {activeTab === 'content' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-steel mb-4">متن‌های صفحه اصلی را ویرایش کنید:</p>

          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">Hero Section</h3>
            <div>
              <label className="label text-xs mb-1 block">عنوان اصلی (خط اول)</label>
              <input
                defaultValue={localStorage.getItem('hero_title_1') || 'قطعات'}
                onChange={e => localStorage.setItem('hero_title_1', e.target.value)}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="label text-xs mb-1 block">کلمه رنگی (نارنجی)</label>
              <input
                defaultValue={localStorage.getItem('hero_title_2') || 'دوربین'}
                onChange={e => localStorage.setItem('hero_title_2', e.target.value)}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="label text-xs mb-1 block">عنوان (خط آخر)</label>
              <input
                defaultValue={localStorage.getItem('hero_title_3') || 'مداربسته'}
                onChange={e => localStorage.setItem('hero_title_3', e.target.value)}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="label text-xs mb-1 block">متن badge (بالای عنوان)</label>
              <input
                defaultValue={localStorage.getItem('hero_badge') || 'واردکننده مستقیم از چین'}
                onChange={e => localStorage.setItem('hero_badge', e.target.value)}
                className="input text-sm"
              />
            </div>
          </div>

          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">آمار پایین صفحه</h3>
            <div className="grid grid-cols-2 gap-4">
              {[
                { key: 'stat1_val', label: 'عدد آمار ۱', def: '+۲۰۰۰' },
                { key: 'stat1_lbl', label: 'توضیح آمار ۱', def: 'نوع قطعه' },
                { key: 'stat2_val', label: 'عدد آمار ۲', def: '۱۰ sal' },
                { key: 'stat2_lbl', label: 'توضیح آمار ۲', def: 'سابقه فعالیت' },
                { key: 'stat3_val', label: 'عدد آمار ۳', def: '۴۸h' },
                { key: 'stat3_lbl', label: 'توضیح آمار ۳', def: 'تحویل اکسپرس' },
                { key: 'stat4_val', label: 'عدد آمار ۴', def: '۱۰۰٪' },
                { key: 'stat4_lbl', label: 'توضیح آمار ۴', def: 'ضمانت اصالت' },
              ].map(s => (
                <div key={s.key}>
                  <label className="label text-[10px] mb-1 block">{s.label}</label>
                  <input
                    defaultValue={localStorage.getItem(s.key) || s.def}
                    onChange={e => localStorage.setItem(s.key, e.target.value)}
                    className="input text-sm"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
