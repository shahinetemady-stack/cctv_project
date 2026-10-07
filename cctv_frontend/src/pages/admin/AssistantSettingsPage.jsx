import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'

const EMPTY_FORM = {
  provider: 'modelscope',
  gemini_api_key: '', gemini_model: 'gemini-3.6-flash', gemini_enabled: true, gemini_proxy: '',
  ms_api_key: '', ms_model: 'Qwen/Qwen3-32B',
  zai_api_key: '', zai_model: 'glm-4.5-flash',
  ds_api_key: '', ds_model: 'deepseek-chat',
  learn_from_gemini: true,
}

function Toggle({ checked, onChange, label }) {
  return (
    <button type="button" onClick={() => onChange(!checked)}
      className="w-full flex items-center justify-between bg-white/5 rounded-xl px-4 py-3 hover:bg-white/10 transition-all">
      <span className="text-sm text-white">{label}</span>
      <span className={`relative inline-flex h-[22px] w-10 rounded-full transition-all shrink-0 ${checked ? 'bg-brand' : 'bg-white/15'}`}>
        <span className={`absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white transition-all ${checked ? 'right-0.5' : 'right-[19px]'}`} />
      </span>
    </button>
  )
}

const ENGINE_LABELS = {
  gemini:     { text: '⚡ Gemini (گوگل)', cls: 'text-emerald-400' },
  modelscope: { text: '☁️ ModelScope — Qwen3 ابری', cls: 'text-emerald-400' },
  zai:        { text: '☁️ z.ai — GLM', cls: 'text-emerald-400' },
  deepseek:   { text: '☁️ DeepSeek', cls: 'text-emerald-400' },
  qwen:       { text: '🖥 Qwen لوکال (پشتیبان)', cls: 'text-amber-400' },
}

// ─── صفحه تنظیمات ربات هوشمند ────────────────────────────────
export default function AssistantSettingsPage() {
  const qc = useQueryClient()
  const [form, setForm] = useState(EMPTY_FORM)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['assistant-settings'],
    queryFn: () => api.get('/assistant/settings/').then(r => r.data),
    refetchInterval: 15000, // وضعیت موتور زنده به‌روز شود
  })

  // فرم فقط در اولین لود از سرور پر شود — ری‌فچ ۱۵ثانیه‌ای نباید ورودی‌های در حال تایپ را پاک کند
  const [initialized, setInitialized] = useState(false)
  useEffect(() => {
    if (data && !initialized) {
      setForm({ ...EMPTY_FORM, ...data })
      setInitialized(true)
    }
  }, [data, initialized])

  const saveMut = useMutation({
    mutationFn: (payload) => api.put('/assistant/settings/', payload).then(r => r.data),
    onSuccess: (saved) => {
      qc.setQueryData(['assistant-settings'], saved)
      toast.success('تنظیمات ذخیره شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || 'خطا در ذخیره تنظیمات'),
  })

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))
  const setBool = (key) => (v) => setForm(f => ({ ...f, [key]: v }))

  const last = data?.last_engine
  const engineInfo = last && ENGINE_LABELS[last.engine]

  return (
    <div className="container-main py-8 max-w-3xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">تنظیمات ربات هوشمند</h1>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : isError ? (
        <div className="rounded-lg px-4 py-3 text-sm bg-red-500/20 text-red-400">خطا در دریافت تنظیمات</div>
      ) : (
        <div className="space-y-6">
          {/* وضعیت فعلی */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">وضعیت فعلی ربات</h3>
            <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
              <div>
                <span className="text-gray-steel text-xs block mb-1">آخرین موتور پاسخ‌دهنده</span>
                {engineInfo ? (
                  <span className={`font-bold ${engineInfo.cls}`}>{engineInfo.text}</span>
                ) : (
                  <span className="text-gray-steel">هنوز پاسخی با مدل ثبت نشده</span>
                )}
                {last?.elapsed != null && (
                  <span className="text-[10px] text-gray-steel block mt-1">
                    زمان پاسخ: {Number(last.elapsed).toLocaleString('fa-IR')} ثانیه
                  </span>
                )}
                {last?.at && (
                  <span className="text-[10px] text-gray-steel block mt-1" dir="ltr">
                    {new Date(last.at).toLocaleString('fa-IR', { timeZone: 'Asia/Tehran' })}
                  </span>
                )}
              </div>
              <div>
                <span className="text-gray-steel text-xs block mb-1">پاسخ‌های یادگرفته‌شده</span>
                <span className="text-white font-bold">{Number(data?.learned_count || 0).toLocaleString('fa-IR')}</span>
              </div>
            </div>
            <p className="text-[11px] text-gray-steel mt-4 leading-5">
              ترتیب پاسخ‌گویی: اول «موتور اصلی» انتخاب‌شده؛ اگر خطا داد، بقیه موتورهایی که کلید دارند و در نهایت Qwen لوکال.
              سرویس‌های چینی (ModelScope / z.ai / DeepSeek) از سرور بدون پروکسی در دسترس‌اند؛ Gemini به پروکسی نیاز دارد.
              زیر هر پاسخ ربات در چت سایت، موتور پاسخ‌دهنده فقط به ادمین‌ها نشان داده می‌شود.
            </p>
          </div>

          {/* موتور اصلی */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">موتور اصلی پاسخ‌گویی</h3>
            <select value={form.provider} onChange={set('provider')} className="input text-sm">
              <option value="modelscope">ModelScope — Qwen3 ابری (رایگان)</option>
              <option value="zai">z.ai — GLM-4.5-Flash (رایگان)</option>
              <option value="deepseek">DeepSeek (ارزان)</option>
              <option value="gemini">Google Gemini (نیازمند پروکسی)</option>
            </select>
          </div>

          {/* ModelScope */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">ModelScope — Qwen3 ابری (رایگان، بدون پروکسی)</h3>
            <div className="space-y-4">
              <div>
                <label className="label text-xs mb-1 block">کلید API (Access Token)</label>
                <input value={form.ms_api_key} onChange={set('ms_api_key')}
                  className="input text-sm font-mono" placeholder="از modelscope.cn ← Access Token" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">مدل</label>
                <input value={form.ms_model} onChange={set('ms_model')}
                  className="input text-sm font-mono" placeholder="Qwen/Qwen3-32B" dir="ltr" />
              </div>
            </div>
          </div>

          {/* z.ai */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">z.ai — GLM-4.5-Flash (رایگان، بدون پروکسی)</h3>
            <div className="space-y-4">
              <div>
                <label className="label text-xs mb-1 block">کلید API</label>
                <input value={form.zai_api_key} onChange={set('zai_api_key')}
                  className="input text-sm font-mono" placeholder="از z.ai ← API Keys" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">مدل</label>
                <input value={form.zai_model} onChange={set('zai_model')}
                  className="input text-sm font-mono" placeholder="glm-4.5-flash" dir="ltr" />
              </div>
            </div>
          </div>

          {/* DeepSeek */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">DeepSeek (ارزان، بدون پروکسی — نیازمند شارژ حساب)</h3>
            <div className="space-y-4">
              <div>
                <label className="label text-xs mb-1 block">کلید API</label>
                <input value={form.ds_api_key} onChange={set('ds_api_key')}
                  className="input text-sm font-mono" placeholder="از platform.deepseek.com" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">مدل</label>
                <input value={form.ds_model} onChange={set('ds_model')}
                  className="input text-sm font-mono" placeholder="deepseek-chat" dir="ltr" />
              </div>
            </div>
          </div>

          {/* Gemini */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Google Gemini (نیازمند پروکسی خارجی)</h3>
            <div className="space-y-4">
              <div>
                <label className="label text-xs mb-1 block">کلید API</label>
                <input value={form.gemini_api_key} onChange={set('gemini_api_key')}
                  className="input text-sm font-mono" placeholder="از aistudio.google.com/apikey" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">مدل</label>
                <input value={form.gemini_model} onChange={set('gemini_model')}
                  className="input text-sm font-mono" placeholder="gemini-3.6-flash" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">پروکسی (فقط برای جمینای)</label>
                <input value={form.gemini_proxy} onChange={set('gemini_proxy')}
                  className="input text-sm font-mono" placeholder="socks5://127.0.0.1:1080 یا http://user:pass@ip:port" dir="ltr" />
                <div className="text-[11px] text-gray-steel mt-1">
                  فقط درخواست‌های جمینای از این پروکسی رد می‌شوند؛ بقیه سایت مستقیم کار می‌کند.
                </div>
              </div>
            </div>
          </div>

          {/* رفتار */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">رفتار ربات</h3>
            <div className="space-y-2">
              <Toggle checked={!!form.gemini_enabled} onChange={setBool('gemini_enabled')}
                label="Gemini در زنجیره پاسخ‌گویی شرکت کند" />
              <Toggle checked={!!form.learn_from_gemini} onChange={setBool('learn_from_gemini')}
                label="یادگیری از پاسخ‌های موتورهای ابری (استفاده در سؤال‌های مشابه بعدی)" />
            </div>
          </div>

          <button onClick={() => saveMut.mutate(form)} disabled={saveMut.isPending}
            className="btn-primary w-full text-sm py-3 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره تنظیمات'}
          </button>
        </div>
      )}
    </div>
  )
}
