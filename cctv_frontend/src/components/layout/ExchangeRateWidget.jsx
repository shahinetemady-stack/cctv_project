// ویجت «نرخ یوان روز» — فقط در پنل پرسنل (سایدبار/دراور ادمین) رندر می‌شود
// مشاهده برای همه پرسنل — ویرایش فقط با پرمیشن exchange_rate_edit (ادمین/حسابدار)
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '../../services/api'
import usePermissions from '../../hooks/usePermissions'
import AmountInput from '../ui/AmountInput'

export default function ExchangeRateWidget() {
  const { can } = usePermissions()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')

  const { data } = useQuery({
    queryKey: ['exchange-rate'],
    queryFn: () => api.get('/catalog/exchange-rate/').then(r => r.data),
    staleTime: 60000,
  })

  const save = useMutation({
    mutationFn: (rate) => api.put('/catalog/exchange-rate/', { rate_cny_to_irt: Number(rate) }),
    onSuccess: () => {
      toast.success('نرخ یوان روز به‌روز شد')
      queryClient.invalidateQueries({ queryKey: ['exchange-rate'] })
      setEditing(false)
    },
    onError: (err) => toast.error(err?.response?.data?.error || 'خطا در ذخیره نرخ یوان'),
  })

  const rate = data?.rate_cny_to_irt
  const canEdit = can('exchange_rate_edit')

  const now = new Date()
  const weekday = new Intl.DateTimeFormat('fa-IR', { weekday: 'long', timeZone: 'Asia/Tehran' }).format(now)
  const todayDate = new Intl.DateTimeFormat('fa-IR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Tehran' }).format(now)

  // ساعت زنده به وقت تهران (تایم‌زون سرور) — هر ثانیه به‌روز می‌شود
  const [clock, setClock] = useState('')
  useEffect(() => {
    const fmt = new Intl.DateTimeFormat('fa-IR', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Tehran' })
    const tick = () => setClock(fmt.format(new Date()))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  function openEdit() {
    setValue(rate ? String(rate) : '')
    setEditing(true)
  }

  return (
    <>
      <div className="flex items-center justify-center mt-2">
        <span className="text-base font-bold font-mono" dir="ltr" style={{ color: 'var(--color-text-secondary)' }}>
          {clock}
        </span>
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>تاریخ امروز</span>
        <span className="text-[11px] font-bold" style={{ color: 'var(--color-text-secondary)' }}>
          {weekday}، {todayDate}
        </span>
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>نرخ یوان روز</span>
        <span className="flex items-center gap-1">
          <span className="text-[11px] font-bold font-mono" style={{ color: 'var(--color-brand)' }}>
            {rate != null ? Number(rate).toLocaleString('fa-IR') : '—'}
          </span>
          <span className="text-[9px]" style={{ color: 'var(--color-text-secondary)' }}>ریال</span>
          {canEdit && (
            <button
              onClick={openEdit}
              className="text-[10px] mr-1 opacity-70 hover:opacity-100 transition-opacity"
              title="ویرایش نرخ یوان"
            >
              ✏️
            </button>
          )}
        </span>
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="card p-6 w-full max-w-xs">
            <h2 className="font-bold text-white text-sm mb-4">✏️ ویرایش نرخ یوان روز</h2>
            <label className="label text-xs mb-1 block">هر یوان چینی چند ریال؟</label>
            <AmountInput
              value={value}
              onChange={e => setValue(e.target.value)}
              className="input text-sm"
              placeholder="مثلاً 270,000"
            />
            <div className="flex gap-2 mt-5">
              <button
                onClick={() => save.mutate(value)}
                disabled={!value || save.isPending}
                className="btn-gold flex-1 text-sm py-2 disabled:opacity-50"
              >
                {save.isPending ? '...' : 'ذخیره'}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="flex-1 text-sm py-2 rounded-xl border border-white/10 text-gray-steel hover:text-white transition-colors"
              >
                انصراف
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
