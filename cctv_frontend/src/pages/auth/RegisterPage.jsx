import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authService } from '../../services/auth'
import useAuthStore from '../../store/useAuthStore'
import { PasswordInput } from '../../components/ui'

const STEPS = { account: 'account', type: 'type', partner: 'partner', verify: 'verify' }

export default function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth, updateUser } = useAuthStore()
  const [step, setStep] = useState(STEPS.account)
  const [userType, setUserType] = useState('public')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // وقتی شماره قبلاً ثبت شده: 'claimable' = حساب سایه فروشگاه (تعیین رمز) | 'exists' = حساب عادی (ورود)
  const [claimCta, setClaimCta] = useState(null)
  const [resendIn, setResendIn] = useState(0)

  const [form, setForm] = useState({
    phone: '', email: '', password: '', password2: '',
    first_name: '', last_name: '', code: '',
    company_name: '', national_id: '', address: '',
  })

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleAccount = (e) => {
    e.preventDefault()
    if (!form.first_name.trim() || !form.last_name.trim()) {
      setError('نام و نام خانوادگی الزامی است')
      return
    }
    if (/[۰-۹٠-٩]/.test(form.phone)) {
      setError('شماره موبایل را با اعداد انگلیسی وارد کنید (مثال: 09123456789)')
      return
    }
    if (!form.phone.startsWith('09') || form.phone.length !== 11) {
      setError('شماره موبایل معتبر نیست (مثال: 09123456789)')
      return
    }
    if (form.password !== form.password2) {
      setError('رمزهای عبور مطابقت ندارند')
      return
    }
    setError('')
    setStep(STEPS.type)
  }

  const handleType = (type) => {
    setUserType(type)
    if (type === 'partner') setStep(STEPS.partner)
    else goVerify()
  }

  // ارسال کد تأیید پیامکی و رفتن به مرحله آخر
  const goVerify = async () => {
    setLoading(true)
    setError('')
    setClaimCta(null)
    try {
      await authService.registerSendCode(form.phone)
      setForm(f => ({ ...f, code: '' }))
      setResendIn(60)
      setStep(STEPS.verify)
    } catch (err) {
      const d = err.response?.data
      setError(d?.error || 'خطا در ارسال پیامک؛ دوباره تلاش کنید')
      // حساب از قبل وجود دارد → دکمه هدایت به تعیین رمز/ورود زیر پیام خطا نمایش داده می‌شود
      if (d?.reason === 'account_claimable') setClaimCta('claimable')
      else if (d?.reason === 'account_exists') setClaimCta('exists')
    } finally {
      setLoading(false)
    }
  }

  // هدایت به صفحه ورود با شماره از پیش پرشده — حساب سایه مستقیم به فلوی «تعیین رمز» می‌رود
  const goClaim = () => {
    navigate('/auth/login', {
      state: { phone: form.phone, mode: claimCta === 'claimable' ? 'forgot' : 'login' },
    })
  }

  useEffect(() => {
    if (resendIn <= 0) return
    const t = setTimeout(() => setResendIn(s => s - 1), 1000)
    return () => clearTimeout(t)
  }, [resendIn])

  const handleRegister = async (type = userType) => {
    setLoading(true)
    setError('')
    try {
      const payload = {
        phone: form.phone,
        code: form.code,
        password: form.password,
        password2: form.password2,
        first_name: form.first_name,
        last_name: form.last_name,
      }
      if (form.email) payload.email = form.email
      if (form.company_name) payload.company_name = form.company_name

      const data = await authService.register(payload)

      if (type === 'partner') {
        // اول setAuth کن تا token در header باشد
        setAuth(data.user, data.access, data.refresh)
        // بعد partner را ثبت کن
        await authService.registerPartner({
          company_name: form.company_name,
          national_id: form.national_id || '',
          address: form.address || '',
        })
        // پروفایل را تازه کن تا منو بلافاصله «همکار (در انتظار تأیید)» نشان بدهد
        authService.getMe().then(updateUser).catch(() => {})
        navigate('/auth/pending')
      } else {
        setAuth(data.user, data.access, data.refresh)
        navigate('/')
      }
    } catch (err) {
      const d = err.response?.data
      const msg = d?.phone?.[0] || d?.code || d?.email?.[0] || d?.password?.[0] || d?.detail || d?.company_name?.[0] || 'خطا در ثبت‌نام'
      // اگر کاربر ساخته شده ولی partner نشده، به صفحه pending برو
      if (msg.includes('موبایل') && msg.includes('موجود') && type === 'partner') {
        // کاربر قبلاً ثبت شده - سعی کن فقط partner را ثبت کنی
        try {
          await authService.registerPartner({
            company_name: form.company_name,
            national_id: form.national_id,
            address: form.address,
          })
          navigate('/auth/pending')
          return
        } catch {}
      }
      setError(msg)
      // اگر در مرحله نهایی هم خطای «قبلاً ثبت شده» برگشت، دکمه ورود/تعیین رمز نشان بده
      if (d?.reason === 'account_claimable') setClaimCta('claimable')
      else if (d?.reason === 'account_exists' || (msg.includes('قبلاً') && msg.includes('ثبت'))) setClaimCta('exists')
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
          {[STEPS.account, STEPS.type, ...(userType === 'partner' ? [STEPS.partner] : []), STEPS.verify].map((s, i, arr) => (
            <div key={s} className={`h-1 flex-1 rounded-full transition-all
              ${arr.indexOf(step) >= i && arr.includes(step) ? 'bg-brand' : 'bg-white/10'}`} />
          ))}
        </div>

        <div className="card p-6">
          {error && (
            <div className="bg-alert-red/10 border border-alert-red/20 rounded-xl p-3 text-sm text-alert-red mb-4">
              {error}
              {claimCta && (
                <button type="button" onClick={goClaim}
                  className="btn-primary w-full mt-3 py-2.5 text-sm">
                  {claimCta === 'claimable' ? '🔑 تعیین رمز عبور و ورود' : 'ورود به حساب کاربری ←'}
                </button>
              )}
            </div>
          )}

          {/* مرحله ۱: اطلاعات حساب */}
          {step === STEPS.account && (
            <form onSubmit={handleAccount} className="space-y-4">
              <h2 className="font-semibold text-base">اطلاعات حساب کاربری</h2>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">نام <span className="text-alert-red">*</span></label>
                  <input value={form.first_name} onChange={set('first_name')} required
                    className="input" placeholder="نام" />
                </div>
                <div>
                  <label className="label">نام خانوادگی <span className="text-alert-red">*</span></label>
                  <input value={form.last_name} onChange={set('last_name')} required
                    className="input" placeholder="نام خانوادگی" />
                </div>
              </div>

              <div>
                <label className="label">
                  نام فروشگاه / شرکت
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <input value={form.company_name} onChange={set('company_name')}
                  className="input" placeholder="نام فروشگاه یا شرکت" />
              </div>

              <div>
                <label className="label">شماره موبایل <span className="text-alert-red">*</span></label>
                <input
                  type="tel" value={form.phone} onChange={set('phone')} required
                  maxLength={11} className="input" placeholder="09123456789" dir="ltr"
                />
              </div>

              <div>
                <label className="label">
                  ایمیل
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <input type="email" value={form.email} onChange={set('email')}
                  className="input" placeholder="example@email.com" dir="ltr" />
              </div>

              <div>
                <label className="label">رمز عبور <span className="text-alert-red">*</span></label>
                <PasswordInput value={form.password} onChange={set('password')} required
                  minLength={8} className="input" placeholder="حداقل ۸ کاراکتر" dir="ltr" />
              </div>

              <div>
                <label className="label">تکرار رمز عبور <span className="text-alert-red">*</span></label>
                <PasswordInput value={form.password2} onChange={set('password2')} required
                  className="input" placeholder="••••••••" dir="ltr" />
              </div>

              <button type="submit" className="btn-primary w-full py-3">ادامه →</button>

              <p className="text-center text-sm text-gray-steel">
                حساب دارید?{' '}
                <Link to="/auth/login" className="text-brand dark:text-cyan hover:underline">ورود</Link>
              </p>
            </form>
          )}

          {/* مرحله ۲: نوع کاربر */}
          {step === STEPS.type && (
            <div className="space-y-4">
              <h2 className="font-semibold text-base">نوع عضویت را انتخاب کنید</h2>
              <button onClick={() => handleType('public')} disabled={loading}
                className="w-full card card-hover p-4 text-right border-2 border-transparent hover:border-brand/30 transition-all">
                <div className="text-2xl mb-2">🛒</div>
                <div className="font-semibold text-sm">مشتری عمومی</div>
                <div className="text-xs text-gray-steel mt-1">خرید آنلاین با قیمت ثابت — پرداخت فوری</div>
              </button>
              <button onClick={() => handleType('partner')} disabled={loading}
                className="w-full card card-hover p-4 text-right border-2 border-transparent hover:border-brand/30 transition-all">
                <div className="text-2xl mb-2">🤝</div>
                <div className="font-semibold text-sm">مشتری همکار</div>
                <div className="text-xs text-gray-steel mt-1">قیمت اختصاصی — نیاز به تأیید ادمین</div>
              </button>
            </div>
          )}

          {/* مرحله ۳: اطلاعات همکار */}
          {step === STEPS.partner && (
            <form onSubmit={(e) => { e.preventDefault(); goVerify() }} className="space-y-4">
              <h2 className="font-semibold text-base">اطلاعات شرکت / کسب‌وکار</h2>
              <div>
                <label className="label">
                  نام شرکت / برند
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <input value={form.company_name} onChange={set('company_name')}
                  className="input" placeholder="نام شرکت یا برند" />
              </div>
              <div>
                <label className="label">
                  کد ملی / شناسه ملی
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <input value={form.national_id} onChange={set('national_id')}
                  className="input" placeholder="کد ملی یا شناسه ملی شرکت" dir="ltr" />
              </div>
              <div>
                <label className="label">
                  آدرس
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <textarea value={form.address} onChange={set('address')}
                  rows={3} className="input resize-none" placeholder="آدرس کامل..." />
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(STEPS.type)}
                  className="btn-ghost flex-1">← برگشت</button>
                <button type="submit" disabled={loading} className="btn-primary flex-1 py-3">
                  {loading ? '...' : 'ادامه'}
                </button>
              </div>
            </form>
          )}

          {/* مرحله نهایی: تأیید شماره با کد پیامکی */}
          {step === STEPS.verify && (
            <form onSubmit={(e) => { e.preventDefault(); handleRegister() }} className="space-y-4">
              <h2 className="font-semibold text-base">تأیید شماره موبایل</h2>
              <p className="text-sm text-gray-steel">
                کد ۵ رقمی پیامک‌شده به <span className="text-white font-mono" dir="ltr">{form.phone}</span> را وارد کنید
              </p>
              <div>
                <label className="label">کد تأیید <span className="text-alert-red">*</span></label>
                <input
                  value={form.code} onChange={set('code')} required
                  inputMode="numeric" maxLength={5} autoFocus
                  className="input text-center tracking-[0.5em] font-mono" placeholder="─────" dir="ltr"
                />
              </div>
              <button type="submit" disabled={loading || form.code.length !== 5} className="btn-primary w-full py-3">
                {loading ? '...' : 'تکمیل ثبت‌نام'}
              </button>
              <div className="flex items-center justify-between text-sm">
                <button type="button" onClick={() => setStep(STEPS.account)}
                  className="text-gray-steel hover:text-white">← اصلاح اطلاعات</button>
                <button type="button" onClick={goVerify} disabled={resendIn > 0 || loading}
                  className="text-brand dark:text-cyan hover:underline disabled:opacity-50 disabled:no-underline">
                  {resendIn > 0 ? `ارسال مجدد (${resendIn})` : 'ارسال مجدد کد'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
