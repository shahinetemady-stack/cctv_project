import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'

const EMPTY_FORM = {
  api_key: '', line_number: '',
  otp_template_id: '', order_status_template_id: '', payment_reminder_template_id: '',
  tier_change_template_id: '', partner_approved_template_id: '', invoice_confirmed_template_id: '',
  account_info_template_id: '',
  order_status_enabled: true, payment_reminder_enabled: true, tier_change_enabled: true,
  partner_approved_enabled: true, invoice_confirmed_enabled: true, account_info_enabled: true,
}

const TEMPLATES = [
  { key: 'otp_template_id',            label: 'کد تأیید (ثبت‌نام/بازیابی رمز)', params: ['%CODE%'] },
  { key: 'order_status_template_id',   label: 'تغییر وضعیت سفارش',             params: ['%ORDERID%', '%STATUS%'] },
  { key: 'payment_reminder_template_id', label: 'یادآوری سررسید بدهی',          params: ['%NAME%', '%AMOUNT%', '%DATE%'] },
  { key: 'tier_change_template_id',    label: 'تغییر سطح همکار',                params: ['%NAME%', '%TIER%'] },
  { key: 'partner_approved_template_id', label: 'تأیید همکار',                  params: ['%NAME%'] },
  { key: 'invoice_confirmed_template_id', label: 'تأیید فاکتور',                params: ['%NAME%', '%NUMBER%'] },
  { key: 'account_info_template_id',   label: 'اطلاعات حساب پرداخت',            params: ['%NAME%', '%AMOUNT%', '%ACCOUNT%', '%HOLDER%'] },
]

const TOGGLES = [
  { key: 'order_status_enabled',      label: 'تغییر وضعیت سفارش' },
  { key: 'payment_reminder_enabled',  label: 'یادآوری سررسید بدهی' },
  { key: 'tier_change_enabled',       label: 'تغییر سطح همکار' },
  { key: 'partner_approved_enabled',  label: 'تأیید همکار' },
  { key: 'invoice_confirmed_enabled', label: 'تأیید فاکتور' },
  { key: 'account_info_enabled',      label: 'اطلاعات حساب پرداخت' },
]

// ─── کلید تاگل پیامک‌های خودکار ─────────────────────────────
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

// ─── صفحه تنظیمات پیامک ─────────────────────────────────────
export default function SmsSettingsPage() {
  const qc = useQueryClient()
  const [form, setForm] = useState(EMPTY_FORM)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sms-settings'],
    queryFn: () => api.get('/notifications/sms-settings/').then(r => r.data),
  })

  useEffect(() => {
    if (data) setForm({ ...EMPTY_FORM, ...data })
  }, [data])

  const saveMut = useMutation({
    mutationFn: (payload) => api.put('/notifications/sms-settings/', payload).then(r => r.data),
    onSuccess: (saved) => {
      qc.setQueryData(['sms-settings'], saved)
      toast.success('تنظیمات ذخیره شد')
    },
    onError: (e) => toast.error(e.response?.data?.error || JSON.stringify(e.response?.data) || 'خطا در ذخیره تنظیمات'),
  })

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))
  const setBool = (key) => (v) => setForm(f => ({ ...f, [key]: v }))

  return (
    <div className="container-main py-8 max-w-3xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">تنظیمات پیامک</h1>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : isError ? (
        <div className="rounded-lg px-4 py-3 text-sm bg-red-500/20 text-red-400">خطا در دریافت تنظیمات</div>
      ) : (
        <div className="space-y-6">
          {/* اتصال به sms.ir */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">اتصال به sms.ir</h3>
            <div className="space-y-4">
              <div>
                <label className="label text-xs mb-1 block">کلید API</label>
                <input value={form.api_key} onChange={set('api_key')}
                  className="input text-sm font-mono" placeholder="کلید API" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">شماره خط ارسال</label>
                <input value={form.line_number} onChange={set('line_number')}
                  className="input text-sm font-mono" placeholder="شماره خط ارسال — برای کمپین گروهی" dir="ltr" />
              </div>
            </div>
          </div>

          {/* قالب‌های Verify */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">قالب‌های Verify (شناسه عددی از پنل sms.ir)</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {TEMPLATES.map(t => (
                <div key={t.key}>
                  <label className="label text-xs mb-1 block">{t.label}</label>
                  <input type="number" min="0" value={form[t.key]} onChange={set(t.key)}
                    className="input text-sm font-mono" placeholder="شناسه قالب" dir="ltr" />
                  <div className="text-[11px] text-gray-steel mt-1">
                    {t.params.length > 1 ? 'پارامترها: ' : 'پارامتر: '}
                    {t.params.map((p, i) => (
                      <span key={p}><span className="font-mono" dir="ltr">{p}</span>{i < t.params.length - 1 ? '، ' : ''}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* پیامک‌های خودکار */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">پیامک‌های خودکار</h3>
            <div className="space-y-2">
              {TOGGLES.map(t => (
                <Toggle key={t.key} checked={!!form[t.key]} onChange={setBool(t.key)} label={t.label} />
              ))}
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
