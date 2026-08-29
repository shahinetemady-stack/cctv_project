import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// ─── صفحه کمپین پیامکی ──────────────────────────────────────
export default function SmsCampaignPage() {
  const [segment, setSegment] = useState('')
  const [text, setText] = useState('')
  const [confirming, setConfirming] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['sms-segments'],
    queryFn: () => api.get('/notifications/sms-campaign/segments/').then(r => r.data),
  })
  const segments = data?.segments || []
  const selected = segments.find(s => s.key === segment)

  const sendMut = useMutation({
    mutationFn: (payload) => api.post('/notifications/sms-campaign/send/', payload).then(r => r.data),
    onSuccess: (res) => {
      toast.success(`ارسال شد: ${fmt(res.sent)} از ${fmt(res.total)}`)
      setConfirming(false)
      setText('')
    },
    onError: (e) => {
      toast.error(e.response?.data?.error || 'خطا در ارسال')
      setConfirming(false)
    },
  })

  function handleSend() {
    if (!segment) return toast.error('گروه گیرندگان را انتخاب کنید')
    if (!text.trim()) return toast.error('متن پیام را بنویسید')
    setConfirming(true)
  }

  const smsParts = Math.max(1, Math.ceil(text.length / 70))

  return (
    <div className="container-main py-8 max-w-3xl">
      <h1 className="font-display font-bold text-2xl text-white mb-6">کمپین پیامکی</h1>

      {/* انتخاب گروه گیرندگان */}
      <h3 className="text-sm font-semibold text-white mb-4">گروه گیرندگان</h3>
      {isLoading ? (
        <div className="text-center py-10 text-gray-steel text-sm">در حال بارگذاری...</div>
      ) : isError ? (
        <div className="rounded-lg px-4 py-3 text-sm bg-red-500/20 text-red-400 mb-6">خطا در دریافت گروه‌ها</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
          {segments.map(s => (
            <button key={s.key} type="button" onClick={() => { setSegment(s.key); setConfirming(false) }}
              className={`card p-4 text-right transition-all ${segment === s.key ? 'ring-2 ring-brand' : 'hover:bg-white/5'}`}>
              <div className="text-sm font-semibold text-white mb-2">{s.label}</div>
              <span className={segment === s.key ? 'badge badge-gold' : 'badge'}>
                {fmt(s.count)} گیرنده
              </span>
            </button>
          ))}
        </div>
      )}

      {/* متن پیام */}
      <div className="card p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <label className="label text-xs">متن پیام</label>
          <span className="text-[11px] text-gray-steel" dir="ltr">
            {fmt(text.length)} کاراکتر — {fmt(smsParts)} پیامک
          </span>
        </div>
        <textarea value={text} onChange={e => { setText(e.target.value); setConfirming(false) }}
          rows={5} className="input text-sm w-full resize-y"
          placeholder="متن پیامک را بنویسید..." />
        <div className="text-[11px] text-gray-steel mt-2">هر پیامک فارسی ۷۰ کاراکتر محاسبه می‌شود.</div>
      </div>

      {/* تأیید و ارسال */}
      {confirming && selected ? (
        <div className="card p-5 border border-brand/40">
          <p className="text-sm text-white mb-4">
            ارسال به {fmt(selected.count)} نفر ({selected.label}) مطمئنید؟
          </p>
          <div className="flex gap-3">
            <button onClick={() => sendMut.mutate({ segment, text: text.trim() })} disabled={sendMut.isPending}
              className="btn-primary flex-1 text-sm py-2.5 disabled:opacity-50">
              {sendMut.isPending ? 'در حال ارسال...' : 'تأیید و ارسال'}
            </button>
            <button onClick={() => setConfirming(false)} className="btn-ghost text-sm py-2.5 px-6">انصراف</button>
          </div>
        </div>
      ) : (
        <button onClick={handleSend} disabled={sendMut.isPending || !segment || !text.trim()}
          className="btn-primary w-full text-sm py-3 disabled:opacity-50">
          ارسال کمپین
        </button>
      )}

      {/* راهنما */}
      <div className="mt-6 rounded-lg px-4 py-3 text-sm bg-brand/10 text-brand">
        این ارسال با خط اختصاصی انجام می‌شود؛ شماره خط را در{' '}
        <Link to="/admin/sms-settings" className="underline font-semibold">تنظیمات پیامک</Link>
        {' '}وارد کرده باشید.
      </div>
    </div>
  )
}
