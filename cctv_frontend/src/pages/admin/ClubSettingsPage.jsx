import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import AmountInput from '../../components/ui/AmountInput'

const EMPTY = {
  silver_to_gold_amount: '',
  gold_to_platinum_amount: '',
  period_months: 3,
  auto_evaluate_enabled: true,
  overdue_warn_workdays: 3,
  overdue_cash_only_days: 7,
  tier_benefits_silver: '',
  tier_benefits_gold: '',
  tier_benefits_platinum: '',
}

// ─── تنظیمات باشگاه همکاران — آستانه‌های ارتقای سطح (قابل تعدیل با تورم) ─────
export default function ClubSettingsPage() {
  const qc = useQueryClient()
  const [form, setForm] = useState(EMPTY)
  const [evalResult, setEvalResult] = useState(null)
  const [snoozeSel, setSnoozeSel] = useState(new Set())

  const { data, isLoading, isError } = useQuery({
    queryKey: ['club-settings'],
    queryFn: () => api.get('/users/club-settings/').then(r => r.data),
  })

  useEffect(() => {
    if (data) setForm({ ...EMPTY, ...data })
  }, [data])

  const saveMut = useMutation({
    mutationFn: () => api.put('/users/club-settings/', {
      ...form,
      silver_to_gold_amount: Number(form.silver_to_gold_amount) || 0,
      gold_to_platinum_amount: Number(form.gold_to_platinum_amount) || 0,
      period_months: Number(form.period_months) || 3,
      overdue_warn_workdays: Number(form.overdue_warn_workdays) || 3,
      overdue_cash_only_days: Number(form.overdue_cash_only_days) || 7,
    }).then(r => r.data),
    onSuccess: (saved) => {
      qc.setQueryData(['club-settings'], saved)
      toast.success('تنظیمات باشگاه ذخیره شد')
    },
    onError: (e) => {
      const d = e.response?.data
      toast.error(d?.gold_to_platinum_amount?.[0] || d?.error || 'خطا در ذخیره تنظیمات')
    },
  })

  const evalMut = useMutation({
    mutationFn: () => api.post('/users/club-settings/evaluate/').then(r => r.data),
    onSuccess: (r) => {
      setEvalResult(r)
      toast.success(`ارزیابی انجام شد — ${r.upgraded} ارتقای سطح` + (r.at_risk?.length ? `، ${r.at_risk.length} نفر در آستانه تنزل` : ''))
    },
    onError: () => toast.error('خطا در اجرای ارزیابی'),
  })

  const snoozeMut = useMutation({
    mutationFn: () => api.post('/users/club-settings/at-risk/snooze/', { phones: [...snoozeSel] }).then(r => r.data),
    onSuccess: (r) => {
      toast.success(`هشدار ${Number(r.snoozed).toLocaleString('fa-IR')} همکار برای ${Number(r.days).toLocaleString('fa-IR')} روز پنهان شد`)
      setSnoozeSel(new Set())
      qc.invalidateQueries({ queryKey: ['club-settings'] })
    },
    onError: () => toast.error('خطا در پنهان‌سازی هشدار'),
  })

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  return (
    <div className="container-main py-8 max-w-2xl">
      <h1 className="font-display font-bold text-2xl text-white mb-2">تنظیمات باشگاه همکاران</h1>
      <p className="text-gray-steel text-sm mb-6 leading-6">
        آستانه‌های ارتقای سطح را با توجه به تورم بازار تعدیل کنید. ملاک سطح هر همکار:
        مجموع خرید آنلاین {form.period_months || 3} ماه اخیر + سابقه خرید قبلی خارج از سایت (که در کارت مشتری ثبت می‌کنید).
        سیستم روزی یک‌بار سطوح را ارزیابی می‌کند و فقط ارتقا می‌دهد — تنزل سطح همیشه دستی است.
      </p>

      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : isError ? (
        <div className="rounded-lg px-4 py-3 text-sm bg-red-500/20 text-red-400">خطا در دریافت تنظیمات</div>
      ) : (
        <div className="space-y-6">
          {data.at_risk_count > 0 && (
            <div className="card p-4 border-r-4 border-amber-500/70 bg-amber-500/10">
              <div className="text-sm font-semibold text-amber-300 mb-1">
                ⚠️ هشدار تنزل سطح — {Number(data.at_risk_count).toLocaleString('fa-IR')} همکار
              </div>
              <p className="text-[11px] text-gray-steel leading-5 mb-2">
                «سطح متناسب» یعنی سطحی که مجموع خرید این همکار در {form.period_months || 3} ماه اخیر
                (+ سابقه خرید ثبت‌شده) فعلاً به آن می‌رسد. سیستم تنزل خودکار نمی‌دهد —
                اگر سطحشان را نگه می‌دارید، تیک بزنید و «پنهان برای ۱ ماه» را بزنید تا دوباره هشدار بگیرند؛
                برای تنزل واقعی از «طرف حساب‌ها ← ویرایش» اقدام کنید.
              </p>
              <div className="flex items-center justify-between mb-1 px-1">
                <label className="flex items-center gap-1.5 text-[11px] text-gray-300 cursor-pointer">
                  <input type="checkbox" className="accent-amber-500"
                    checked={snoozeSel.size > 0 && snoozeSel.size === data.at_risk.length}
                    onChange={(e) => setSnoozeSel(e.target.checked ? new Set(data.at_risk.map(r => r.phone)) : new Set())} />
                  انتخاب همه
                </label>
                {snoozeSel.size > 0 && (
                  <button onClick={() => snoozeMut.mutate()} disabled={snoozeMut.isPending}
                    className="text-[11px] bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 rounded-lg px-3 py-1 transition-colors disabled:opacity-50">
                    {snoozeMut.isPending ? 'در حال پنهان‌سازی...' : `🤐 پنهان برای ۱ ماه (${Number(snoozeSel.size).toLocaleString('fa-IR')} نفر)`}
                  </button>
                )}
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto pl-1">
                {data.at_risk.map((r, i) => (
                  <div key={i} className="text-[11px] text-gray-300 flex items-center gap-3">
                    <label className="flex items-center gap-1.5 cursor-pointer shrink-0">
                      <input type="checkbox" className="accent-amber-500"
                        checked={snoozeSel.has(r.phone)}
                        onChange={(e) => setSnoozeSel(s => {
                          const n = new Set(s)
                          e.target.checked ? n.add(r.phone) : n.delete(r.phone)
                          return n
                        })} />
                    </label>
                    <span className="shrink-0" dir="ltr">{r.phone}{r.name ? ` (${r.name})` : ''}</span>
                    <span className="text-amber-300 whitespace-nowrap">
                      {r.tier} → متناسب: {r.eligible_tier} ({Number(r.total).toLocaleString('fa-IR')} ریال)
                    </span>
                  </div>
                ))}
              </div>
              {data.at_risk_snoozed_count > 0 && (
                <div className="text-[11px] text-gray-steel mt-2">
                  🔇 {Number(data.at_risk_snoozed_count).toLocaleString('fa-IR')} نفر به درخواست شما تا یک ماه دیگر در این هشدار نمایش داده نمی‌شوند.
                </div>
              )}
            </div>
          )}
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">آستانه‌های ارتقا (ریال)</h3>

            <div>
              <label className="label text-xs mb-1 block">حداقل مجموع خرید برای ارتقا سیلور → گلد</label>
              <AmountInput value={form.silver_to_gold_amount} onChange={set('silver_to_gold_amount')}
                className="input text-sm" placeholder="مثال: ۵۰۰٬۰۰۰٬۰۰۰" />
            </div>

            <div>
              <label className="label text-xs mb-1 block">حداقل مجموع خرید برای ارتقا گلد → پلاتینیوم</label>
              <AmountInput value={form.gold_to_platinum_amount} onChange={set('gold_to_platinum_amount')}
                className="input text-sm" placeholder="مثال: ۲٬۰۰۰٬۰۰۰٬۰۰۰۰" />
            </div>

            <div>
              <label className="label text-xs mb-1 block">بازه محاسبه خرید آنلاین (ماه)</label>
              <input type="number" min="1" max="36" value={form.period_months}
                onChange={set('period_months')} className="input text-sm" dir="ltr" />
              <div className="text-[11px] text-gray-steel mt-1">
                خریدهای آنلاین این چند ماه اخیر محاسبه می‌شود؛ سابقه خرید قبلی (دستی) همیشه به آن اضافه می‌شود.
              </div>
            </div>

            <button type="button"
              onClick={() => setForm(f => ({ ...f, auto_evaluate_enabled: !f.auto_evaluate_enabled }))}
              className="w-full flex items-center justify-between bg-white/5 rounded-xl px-4 py-3 hover:bg-white/10 transition-all">
              <span className="text-sm text-white">ارزیابی خودکار روزانه سطوح</span>
              <span className={`relative inline-flex h-[22px] w-10 rounded-full transition-all shrink-0 ${form.auto_evaluate_enabled ? 'bg-brand' : 'bg-white/15'}`}>
                <span className={`absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white transition-all ${form.auto_evaluate_enabled ? 'right-0.5' : 'right-[19px]'}`} />
              </span>
            </button>
          </div>

          {/* متن مزایای هر سطح */}
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">متن مزایای هر سطح (نمایش در صفحه باشگاه)</h3>
            <p className="text-[11px] text-gray-steel leading-5">
              این متن در کارت هر سطح در صفحه «باشگاه همکاران» نمایش داده می‌شود. اگر خالی بماند، متن پیش‌فرض «مزایای این سطح به‌زودی اعلام می‌شود» نمایش داده می‌شود.
            </p>
            <div>
              <label className="label text-xs mb-1 block">مزایای سطح سیلور</label>
              <textarea rows={3} value={form.tier_benefits_silver} onChange={set('tier_benefits_silver')}
                className="input text-sm w-full resize-y" placeholder="مثال: قیمت همکاری، ارسال سریع..." />
            </div>
            <div>
              <label className="label text-xs mb-1 block">مزایای سطح گلد</label>
              <textarea rows={3} value={form.tier_benefits_gold} onChange={set('tier_benefits_gold')}
                className="input text-sm w-full resize-y" placeholder="مثال: تخفیف بیشتر، اولویت موجودی..." />
            </div>
            <div>
              <label className="label text-xs mb-1 block">مزایای سطح پلاتینیوم</label>
              <textarea rows={3} value={form.tier_benefits_platinum} onChange={set('tier_benefits_platinum')}
                className="input text-sm w-full resize-y" placeholder="مثال: بهترین قیمت، پشتیبانی اختصاصی..." />
            </div>
          </div>

          {/* سیاست برخورد با معوقات */}
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white">سیاست برخورد با معوقات تسویه</h3>
            <p className="text-[11px] text-gray-steel leading-5">
              پس از سررسید: تا مهلت اول فقط هشدار می‌رود؛ بعد تا مهلت دوم فقط خرید نقدی ممکن است؛
              پس از آن ثبت سفارش کاملاً بسته می‌شود. جمعه و تعطیلات رسمی در مهلت اول حساب نمی‌شوند.
              ادمین می‌تواند از کارت مشتری محدودیت را دستی باز کند.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label text-xs mb-1 block">مهلت هشدار (روز کاری)</label>
                <input type="number" min="1" max="30" value={form.overdue_warn_workdays}
                  onChange={set('overdue_warn_workdays')} className="input text-sm" dir="ltr" />
              </div>
              <div>
                <label className="label text-xs mb-1 block">مهلت فقط نقدی (روز تقویمی)</label>
                <input type="number" min="1" max="60" value={form.overdue_cash_only_days}
                  onChange={set('overdue_cash_only_days')} className="input text-sm" dir="ltr" />
              </div>
            </div>
          </div>

          <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}
            className="btn-primary w-full text-sm py-3 disabled:opacity-50">
            {saveMut.isPending ? 'در حال ذخیره...' : 'ذخیره تنظیمات'}
          </button>

          <div className="card p-5">
            <h3 className="text-sm font-semibold text-white mb-2">اجرای دستی ارزیابی سطوح</h3>
            <p className="text-[11px] text-gray-steel mb-3 leading-5">
              سطح همه همکاران تأییدشده بر اساس آستانه‌های بالا بررسی می‌شود. فقط ارتقا اعمال می‌شود و برای هر ارتقا پیامک اطلاع‌رسانی می‌رود.
            </p>
            <button onClick={() => { setEvalResult(null); evalMut.mutate() }} disabled={evalMut.isPending}
              className="btn-secondary w-full text-sm py-2.5 disabled:opacity-50">
              {evalMut.isPending ? 'در حال ارزیابی...' : '⚡ ارزیابی الان'}
            </button>
            {evalResult && (
              <div className="mt-3 text-xs bg-white/5 rounded-xl p-3 space-y-1">
                <div className="text-gray-steel">
                  {evalResult.checked} همکار بررسی شد — <span className="text-white">{evalResult.upgraded} ارتقا</span>
                </div>
                {evalResult.details?.map((d, i) => (
                  <div key={i} className="text-green-400" dir="ltr">
                    {d.phone}: {d.from} → {d.to} ({Number(d.total).toLocaleString('fa-IR')} ریال)
                  </div>
                ))}
                {evalResult.at_risk?.length > 0 && (
                  <>
                    <div className="text-amber-300 pt-1">
                      ⚠️ {evalResult.at_risk.length} همکار مجموع خریدشان زیر سطح فعلی است (تنزل دستی):
                    </div>
                    {evalResult.at_risk.map((r, i) => (
                      <div key={i} className="text-amber-200/80 flex items-center gap-2">
                        <span className="shrink-0" dir="ltr">{r.phone}</span>
                        <span className="whitespace-nowrap">{r.tier} → متناسب {r.eligible_tier} ({Number(r.total).toLocaleString('fa-IR')} ریال)</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
