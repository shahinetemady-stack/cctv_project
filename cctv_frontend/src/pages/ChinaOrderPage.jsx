import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import useAuthStore from '../store/useAuthStore'
import Globe from '../components/Globe'

export default function ChinaOrderPage() {
  const { user } = useAuthStore()
  const [form, setForm] = useState({
    name: user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() : '',
    phone: user?.phone || '',
    email: user?.email || '',
    product_name: '',
    quantity: '1',
    description: '',
    product_link: '',
  })
  const [status, setStatus] = useState(null) // null | 'loading' | 'success' | 'error'
  const [msg, setMsg] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name || !form.phone || !form.product_name) {
      setStatus('error'); setMsg('نام، شماره تماس و نام کالا الزامی است'); return
    }
    setStatus('loading')
    try {
      const res = await api.post('/orders/china-request/', { ...form, quantity: Number(form.quantity) })
      setStatus('success')
      setMsg(res.data.message)
    } catch (err) {
      setStatus('error')
      setMsg(err.response?.data?.error || 'خطا در ثبت درخواست')
    }
  }

  if (status === 'success') return (
    <div className="container-main py-20 max-w-lg text-center">
      <div className="text-6xl mb-6">✅</div>
      <h1 className="font-display font-bold text-2xl text-white mb-4">درخواست ثبت شد!</h1>
      <p className="text-gray-steel mb-8">{msg}</p>
      <div className="flex gap-4 justify-center">
        <Link to="/" className="btn-primary px-6 py-3">بازگشت به خانه</Link>
        <button onClick={() => { setStatus(null); setForm(f => ({ ...f, product_name: '', quantity: '1', description: '', product_link: '' })) }}
          className="btn-secondary px-6 py-3">ثبت درخواست جدید</button>
      </div>
    </div>
  )

  return (
    <div className="container-main py-12 max-w-4xl">
      {/* هدر — متن سمت راست، کره زمین سمت چپ (روی موبایل: متن بالا، کره پایین) */}
      <div className="china-hero" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 'clamp(4px, 2vw, 20px)',
        flexWrap: 'wrap', marginBottom: '2.5rem', direction: 'rtl',
      }}>
        <div style={{ flex: '0 1 420px', textAlign: 'right' }}>
          <div className="text-5xl mb-4">🇨🇳</div>
          <h1 className="font-display font-bold text-5xl mb-4" style={{ color: 'var(--color-text-primary)' }}>
            سفارش مستقیم از چین
          </h1>
          <p className="text-xl" style={{ color: 'var(--color-text-secondary)', lineHeight: 2 }}>
            کالایی که در سایت ما موجود نیست؟ درخواست خود را ثبت کنید تا کارشناسان ما آن را مستقیماً از چین تهیه کنند.
          </p>
        </div>
        <div style={{ flex: '0 0 auto', width: 'min(450px, 88vw)' }}>
          <Globe size={450} />
        </div>
      </div>

      {/* مزایا */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { icon: '💰', title: 'قیمت مناسب', desc: 'مستقیم از کارخانه' },
          { icon: '🚀', title: 'سریع', desc: 'کوتاه‌ترین مسیر' },
          { icon: '✅', title: 'تضمین کیفیت', desc: 'بازرسی قبل از ارسال' },
        ].map(item => (
          <div key={item.title} className="card p-4 text-center">
            <div className="text-2xl mb-2">{item.icon}</div>
            <div className="text-sm font-semibold text-white">{item.title}</div>
            <div className="text-xs text-gray-steel">{item.desc}</div>
          </div>
        ))}
      </div>

      {/* فرم */}
      <div className="card p-6">
        <h2 className="font-semibold text-white mb-6">اطلاعات درخواست</h2>
        <form onSubmit={handleSubmit} className="space-y-4">

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-sm mb-1 block">نام و نام خانوادگی *</label>
              <input value={form.name} onChange={e => set('name', e.target.value)}
                className="input" placeholder="شاهین محمدی" />
            </div>
            <div>
              <label className="label text-sm mb-1 block">شماره تماس *</label>
              <input value={form.phone} onChange={e => set('phone', e.target.value)}
                className="input" placeholder="09XXXXXXXXX" dir="ltr" />
            </div>
          </div>

          <div>
            <label className="label text-sm mb-1 block">ایمیل (اختیاری)</label>
            <input value={form.email} onChange={e => set('email', e.target.value)}
              className="input" placeholder="example@email.com" dir="ltr" type="email" />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="label text-sm mb-1 block">نام کالا *</label>
              <input value={form.product_name} onChange={e => set('product_name', e.target.value)}
                className="input" placeholder="مثلاً: برد دوربین IP 8MP H.265" />
            </div>
            <div>
              <label className="label text-sm mb-1 block">تعداد *</label>
              <input inputMode="numeric" value={form.quantity}
                onChange={e => set('quantity', e.target.value)}
                className="input" min="1" />
            </div>
          </div>

          <div>
            <label className="label text-sm mb-1 block">توضیحات و مشخصات فنی</label>
            <textarea value={form.description} onChange={e => set('description', e.target.value)}
              className="input resize-none" rows={4}
              placeholder="مشخصات فنی، برند مورد نظر، کاربرد، و هر اطلاعاتی که به ما کمک می‌کند..." />
          </div>

          <div>
            <label className="label text-sm mb-1 block">لینک کالا (اختیاری)</label>
            <input value={form.product_link} onChange={e => set('product_link', e.target.value)}
              className="input" placeholder="https://alibaba.com/..." dir="ltr" type="url" />
            <p className="text-xs text-gray-steel mt-1">اگر کالا را در Alibaba یا 1688 پیدا کردید، لینک آن را وارد کنید</p>
          </div>

          {status === 'error' && (
            <div className="bg-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm">{msg}</div>
          )}

          <button type="submit" disabled={status === 'loading'}
            className="btn-primary w-full py-3 text-sm font-semibold disabled:opacity-50">
            {status === 'loading' ? 'در حال ثبت...' : '📤 ثبت درخواست'}
          </button>
        </form>
      </div>

      <p className="text-center text-xs text-gray-steel mt-6">
        پس از ثبت درخواست، کارشناسان ما ظرف ۲۴ ساعت با شما تماس خواهند گرفت.
      </p>
    </div>
  )
}
