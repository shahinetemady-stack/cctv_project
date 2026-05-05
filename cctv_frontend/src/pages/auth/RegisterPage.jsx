import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authService } from '../../services/auth'
import useAuthStore from '../../store/useAuthStore'

const STEPS = { account: 'account', type: 'type', partner: 'partner' }

export default function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [step, setStep] = useState(STEPS.account)
  const [userType, setUserType] = useState('public')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    email: '', password: '', password2: '',
    first_name: '', last_name: '',
    company_name: '', national_id: '', address: '',
  })

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleAccount = (e) => {
    e.preventDefault()
    if (form.password !== form.password2) { setError('رمزهای عبور مطابقت ندارند'); return }
    setError('')
    setStep(STEPS.type)
  }

  const handleType = (type) => {
    setUserType(type)
    if (type === 'partner') setStep(STEPS.partner)
    else handleRegister(type)
  }

  const handleRegister = async (type = userType) => {
    setLoading(true)
    setError('')
    try {
      const payload = {
        email: form.email, password: form.password, password2: form.password2,
        first_name: form.first_name, last_name: form.last_name,
      }
      const data = await authService.register(payload)
      setAuth(data.user, data.access, data.refresh)

      if (type === 'partner') {
        await authService.registerPartner({
          company_name: form.company_name,
          national_id: form.national_id,
          address: form.address,
        })
        navigate('/auth/pending')
      } else {
        navigate('/')
      }
    } catch (err) {
      const d = err.response?.data
      setError(d?.email?.[0] || d?.password?.[0] || d?.detail || 'خطا در ثبت‌نام')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-brand rounded-2xl flex items-center justify-center shadow-brand mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.889L15 14v-4zM3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/>
            </svg>
          </div>
          <h1 className="font-display font-bold text-2xl text-white">ثبت‌نام</h1>
        </div>

        {/* نوار پیشرفت */}
        <div className="flex items-center gap-2 mb-6">
          {Object.values(STEPS).filter(s => s !== STEPS.partner || userType === 'partner').map((s, i) => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-all
              ${Object.keys(STEPS).indexOf(step) >= i ? 'bg-brand' : 'bg-white/10'}`} />
          ))}
        </div>

        <div className="card p-6">
          {error && (
            <div className="bg-alert-red/10 border border-alert-red/20 rounded-xl p-3 text-sm text-alert-red mb-4">
              {error}
            </div>
          )}

          {/* مرحله ۱: اطلاعات حساب */}
          {step === STEPS.account && (
            <form onSubmit={handleAccount} className="space-y-4">
              <h2 className="font-semibold text-base">اطلاعات حساب کاربری</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">نام</label>
                  <input value={form.first_name} onChange={set('first_name')} className="input" placeholder="نام" />
                </div>
                <div>
                  <label className="label">نام خانوادگی</label>
                  <input value={form.last_name} onChange={set('last_name')} className="input" placeholder="نام خانوادگی" />
                </div>
              </div>
              <div>
                <label className="label">ایمیل *</label>
                <input type="email" value={form.email} onChange={set('email')} required
                  className="input" placeholder="example@email.com" dir="ltr" />
              </div>
              <div>
                <label className="label">رمز عبور *</label>
                <input type="password" value={form.password} onChange={set('password')} required
                  minLength={8} className="input" placeholder="حداقل ۸ کاراکتر" dir="ltr" />
              </div>
              <div>
                <label className="label">تکرار رمز عبور *</label>
                <input type="password" value={form.password2} onChange={set('password2')} required
                  className="input" placeholder="••••••••" dir="ltr" />
              </div>
              <button type="submit" className="btn-primary w-full py-3">ادامه →</button>
              <p className="text-center text-sm text-gray-steel">
                حساب دارید؟{' '}
                <Link to="/auth/login" className="text-brand dark:text-cyan hover:underline">ورود</Link>
              </p>
            </form>
          )}

          {/* مرحله ۲: نوع کاربر */}
          {step === STEPS.type && (
            <div className="space-y-4">
              <h2 className="font-semibold text-base">نوع عضویت را انتخاب کنید</h2>
              <button onClick={() => handleType('public')} disabled={loading}
                className="w-full card card-hover p-4 text-right border-2 border-transparent
                  hover:border-brand/30 transition-all">
                <div className="text-2xl mb-2">🛒</div>
                <div className="font-semibold text-sm">مشتری عمومی</div>
                <div className="text-xs text-gray-steel mt-1">
                  خرید آنلاین با قیمت ثابت — پرداخت فوری
                </div>
              </button>
              <button onClick={() => handleType('partner')} disabled={loading}
                className="w-full card card-hover p-4 text-right border-2 border-transparent
                  hover:border-brand/30 transition-all">
                <div className="text-2xl mb-2">🤝</div>
                <div className="font-semibold text-sm">مشتری همکار</div>
                <div className="text-xs text-gray-steel mt-1">
                  قیمت اختصاصی — سیستم استعلام — نیاز به تأیید ادمین
                </div>
              </button>
            </div>
          )}

          {/* مرحله ۳: اطلاعات همکار */}
          {step === STEPS.partner && (
            <form onSubmit={(e) => { e.preventDefault(); handleRegister('partner') }} className="space-y-4">
              <h2 className="font-semibold text-base">اطلاعات شرکت / کسب‌وکار</h2>
              <div>
                <label className="label">نام شرکت / برند *</label>
                <input value={form.company_name} onChange={set('company_name')} required
                  className="input" placeholder="نام شرکت یا برند" />
              </div>
              <div>
                <label className="label">کد ملی / شناسه ملی *</label>
                <input value={form.national_id} onChange={set('national_id')} required
                  className="input" placeholder="کد ملی یا شناسه ملی شرکت" dir="ltr" />
              </div>
              <div>
                <label className="label">آدرس *</label>
                <textarea value={form.address} onChange={set('address')} required
                  rows={3} className="input resize-none" placeholder="آدرس کامل..." />
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(STEPS.type)}
                  className="btn-ghost flex-1">← برگشت</button>
                <button type="submit" disabled={loading} className="btn-primary flex-1 py-3">
                  {loading ? '...' : 'ثبت‌نام'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
