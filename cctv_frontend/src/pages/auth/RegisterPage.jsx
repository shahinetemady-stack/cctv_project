import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authService } from '../../services/auth'
import useAuthStore from '../../store/useAuthStore'
import { PasswordInput } from '../../components/ui'

const STEPS = { type: 'type', account: 'account', partner: 'partner', verify: 'verify' }
const DOC_MAX_MB = 5

export default function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth, updateUser } = useAuthStore()
  const [step, setStep] = useState(STEPS.type)
  const [userType, setUserType] = useState('public')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // وقتی شماره قبلاً ثبت شده: 'claimable' = حساب سایه فروشگاه (تعیین رمز) | 'exists' = حساب عادی (ورود)
  const [claimCta, setClaimCta] = useState(null)
  const [resendIn, setResendIn] = useState(0)
  const [docFile, setDocFile] = useState(null)
  const [docPreview, setDocPreview] = useState(null)

  const [form, setForm] = useState({
    phone: '', email: '', password: '', password2: '',
    first_name: '', last_name: '', code: '',
    company_name: '', national_id: '', address: '', social_url: '',
  })

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  // انتخاب مدرک شناسایی (کارت ویزیت / کارت ملی) — فقط تصویر، حداکثر ۵ مگابایت
  const pickDoc = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('فقط فایل تصویری (JPG/PNG) قابل قبول است')
      return
    }
    if (file.size > DOC_MAX_MB * 1024 * 1024) {
      setError(`حجم تصویر باید کمتر از ${DOC_MAX_MB} مگابایت باشد`)
      return
    }
    setError('')
    setDocFile(file)
    setDocPreview(URL.createObjectURL(file))
  }

  const handleType = (type) => {
    setUserType(type)
    setError('')
    setStep(STEPS.account)
  }

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
    if (!/[A-Za-zآ-ی]/.test(form.password) || !/\d/.test(form.password)) {
      setError('رمز عبور باید ترکیبی از حروف و عدد باشد (فقط عدد یا فقط حرف کافی نیست)')
      return
    }
    setError('')
    if (userType === 'partner') setStep(STEPS.partner)
    else goVerify()
  }

  const handlePartner = (e) => {
    e.preventDefault()
    if (!form.address.trim()) {
      setError('آدرس برای ارسال بار الزامی است')
      return
    }
    if (!docFile) {
      setError('تصویر کارت ویزیت یا عکس صفحه ادمین پیج اجباری است')
      return
    }
    setError('')
    goVerify()
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

  const buildPartnerFormData = () => {
    const fd = new FormData()
    fd.append('company_name', form.company_name)
    fd.append('national_id', form.national_id || '')
    fd.append('address', form.address)
    fd.append('social_url', form.social_url || '')
    if (docFile) fd.append('document', docFile)
    return fd
  }

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

      const data = await authService.register(payload)

      if (type === 'partner') {
        // اول setAuth کن تا token در header باشد
        setAuth(data.user, data.access, data.refresh)
        // بعد درخواست همکاری را با مدارک ثبت کن
        await authService.registerPartner(buildPartnerFormData())
        // پروفایل را تازه کن تا منو بلافاصله «همکار (در انتظار تأیید)» نشان بدهد
        authService.getMe().then(updateUser).catch(() => {})
        navigate('/auth/pending')
      } else {
        setAuth(data.user, data.access, data.refresh)
        navigate('/')
      }
    } catch (err) {
      const d = err.response?.data
      const msg = d?.phone?.[0] || d?.code || d?.email?.[0] || d?.password?.[0]
        || d?.social_url?.[0] || d?.address?.[0] || d?.document?.[0]
        || d?.detail || d?.company_name?.[0] || 'خطا در ثبت‌نام'
      // اگر کاربر ساخته شده ولی partner نشده، به صفحه pending برو
      if (msg.includes('موبایل') && msg.includes('موجود') && type === 'partner') {
        // کاربر قبلاً ثبت شده - سعی کن فقط partner را ثبت کنی
        try {
          await authService.registerPartner(buildPartnerFormData())
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
          {[STEPS.type, STEPS.account, ...(userType === 'partner' ? [STEPS.partner] : []), STEPS.verify].map((s, i, arr) => (
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

          {/* مرحله ۱: نوع عضویت */}
          {step === STEPS.type && (
            <div className="space-y-4">
              <h2 className="font-semibold text-base">نوع عضویت را انتخاب کنید</h2>
              <button onClick={() => handleType('public')} disabled={loading}
                className="w-full card card-hover p-4 text-right border-2 border-transparent hover:border-brand/30 transition-all">
                <div className="text-2xl mb-2">🛒</div>
                <div className="font-semibold text-sm">مشتری عمومی</div>
                <div className="text-xs text-gray-steel mt-1">ثبت‌نام سریع با نام، موبایل و رمز — دسترسی فوری با قیمت عمومی</div>
              </button>
              <button onClick={() => handleType('partner')} disabled={loading}
                className="w-full card card-hover p-4 text-right border-2 border-transparent hover:border-brand/30 transition-all">
                <div className="text-2xl mb-2">🤝</div>
                <div className="font-semibold text-sm">مشتری همکار</div>
                <div className="text-xs text-gray-steel mt-1">قیمت‌های همکاری — پس از بررسی مدارک و تأیید ادمین فعال می‌شود</div>
              </button>
              <Link to="/club"
                className="block text-center text-xs text-brand dark:text-cyan hover:underline">
                🤝 همکار هستید؟ مزایا، سطوح و قوانین باشگاه همکاران را قبل از ثبت‌نام بخوانید
              </Link>
              <p className="text-center text-sm text-gray-steel">
                حساب دارید?{' '}
                <Link to="/auth/login" className="text-brand dark:text-cyan hover:underline">ورود</Link>
              </p>
            </div>
          )}

          {/* مرحله ۲: اطلاعات حساب */}
          {step === STEPS.account && (
            <form onSubmit={handleAccount} className="space-y-4" autoComplete="off">
              <h2 className="font-semibold text-base">اطلاعات حساب کاربری</h2>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">
                    {userType === 'partner' ? 'نام / نام برند شخصی' : 'نام'} <span className="text-alert-red">*</span>
                  </label>
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
                <label className="label">شماره موبایل <span className="text-alert-red">*</span></label>
                <input
                  type="tel" value={form.phone} onChange={set('phone')} required
                  maxLength={11} className="input" dir="ltr" autoComplete="off" name="reg-mobile"
                />
                <div className="text-[11px] text-gray-steel/60 mt-1">مثال: 09123456789</div>
                {userType === 'partner' && (
                  <div className="text-[11px] text-gray-steel mt-1">این شماره برای هماهنگی و ارسال بار استفاده می‌شود</div>
                )}
              </div>

              <div>
                <label className="label">
                  ایمیل
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <input type="email" value={form.email} onChange={set('email')}
                  className="input" dir="ltr" autoComplete="off" name="reg-email" />
                <div className="text-[11px] text-gray-steel/60 mt-1">مثال: name@gmail.com</div>
              </div>

              <div>
                <label className="label">رمز عبور <span className="text-alert-red">*</span></label>
                <PasswordInput value={form.password} onChange={set('password')} required
                  minLength={8} className="input" autoComplete="new-password"
                  placeholder="رمز عبور خود را وارد کنید" />
                <div className="text-[11px] text-gray-steel/60 mt-1">
                  حداقل ۸ کاراکتر و ترکیبی از حروف و عدد باشد (فقط عدد یا فقط حرف قبول نیست)
                </div>
              </div>

              <div>
                <label className="label">تکرار رمز عبور <span className="text-alert-red">*</span></label>
                <PasswordInput value={form.password2} onChange={set('password2')} required
                  className="input" autoComplete="new-password"
                  placeholder="رمز عبور خود را تکرار کنید" />
              </div>

              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(STEPS.type)}
                  className="btn-ghost flex-1">← برگشت</button>
                <button type="submit" className="btn-primary flex-1 py-3">ادامه</button>
              </div>
            </form>
          )}

          {/* مرحله ۳: اطلاعات همکار — فروشگاهی و نصاب مستقل */}
          {step === STEPS.partner && (
            <form onSubmit={handlePartner} className="space-y-4">
              <h2 className="font-semibold text-base">اطلاعات همکاری</h2>
              <p className="text-[11px] text-gray-steel leading-5">
                اگر نصاب مستقل هستید و مغازه ندارید، در فیلد فروشگاه نام برند شخصی خودتان را بنویسید.
              </p>
              <div className="card p-3 text-[11px] text-gray-steel leading-5 border-r-2 border-gold/60">
                🏅 سطح همکاری از «سیلور» شروع می‌شود و با مجموع خرید ۳ ماهه به‌صورت خودکار ارتقا می‌یابد (گلد و پلاتینیوم).
                سطح با مجموع خرید ۳ ماهه به‌صورت خودکار ارتقا یا تنزل می‌یابد.{' '}
                <Link to="/club" className="text-brand dark:text-cyan hover:underline">مشاهده کامل قوانین و مزایا</Link>
              </div>

              <div>
                <label className="label">نام فروشگاه / شرکت / برند شخصی <span className="text-alert-red">*</span></label>
                <input value={form.company_name} onChange={set('company_name')} required
                  className="input" placeholder="نام فروشگاه، شرکت یا برند شخصی" />
              </div>

              <div>
                <label className="label">
                  کد ملی / شناسه ملی
                  <span className="text-gray-steel text-xs mr-1">(اختیاری)</span>
                </label>
                <input value={form.national_id} onChange={set('national_id')}
                  className="input" placeholder="کد ملی یا شناسه ملی" dir="ltr" />
              </div>

              <div>
                <label className="label">آدرس صفحه اینستاگرام یا کانال تلگرام</label>
                <input value={form.social_url} onChange={set('social_url')}
                  className="input" placeholder="instagram.com/... یا t.me/..." dir="ltr" />
                <div className="text-[11px] text-gray-steel mt-1">برای بررسی نمونه‌کارها و فعالیت شما در حوزه دوربین</div>
              </div>

              <div>
                <label className="label">تصویر کارت ویزیت یا عکس صفحه ادمین پیج <span className="text-alert-red">*</span></label>
                <input type="file" accept="image/*" onChange={pickDoc} className="hidden" id="partner-doc" />
                {docPreview ? (
                  <div className="relative">
                    <img src={docPreview} alt="مدرک" className="w-full h-32 object-cover rounded-xl border border-white/10" />
                    <button type="button"
                      onClick={() => { setDocFile(null); setDocPreview(null) }}
                      className="absolute top-2 left-2 bg-black/70 text-white text-xs rounded-lg px-2 py-1">
                      ✕ حذف
                    </button>
                  </div>
                ) : (
                  <label htmlFor="partner-doc"
                    className="block w-full border-2 border-dashed border-white/15 hover:border-brand/40 rounded-xl p-4 text-center text-xs text-gray-steel cursor-pointer transition-all">
                    📷 انتخاب تصویر (حداکثر {DOC_MAX_MB} مگابایت)
                  </label>
                )}
                <div className="text-[11px] text-gray-steel mt-1">بارگذاری این تصویر برای بررسی درخواست همکاری اجباری است</div>
              </div>

              <div>
                <label className="label">آدرس <span className="text-alert-red">*</span></label>
                <textarea value={form.address} onChange={set('address')} required
                  rows={3} className="input resize-none" placeholder="آدرس کامل برای ارسال بار..." />
              </div>

              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(STEPS.account)}
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
