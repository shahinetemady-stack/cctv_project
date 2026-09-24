import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { authService } from '../../services/auth'
import useAuthStore from '../../store/useAuthStore'
import { PasswordInput } from '../../components/ui'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setAuth } = useAuthStore()
  // ورود از صفحه ثبت‌نام با شماره تکراری → شماره از پیش پر می‌شود و در صورت حساب سایه، فلوی «تعیین رمز» باز است
  const initialPhone = location.state?.phone || ''
  const startForgot = location.state?.mode === 'forgot'
  const [mode, setMode] = useState(startForgot ? 'forgot' : 'login')   // login | forgot | reset
  const [form, setForm] = useState({ username: initialPhone, password: '' })
  const [phone, setPhone] = useState(initialPhone)
  const [code, setCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState(() => {
    // نشست منقضی‌شده — api.js قبل از ریدایرکت به ورود این پرچم را می‌گذارد
    if (sessionStorage.getItem('auth_notice') === 'expired') {
      sessionStorage.removeItem('auth_notice')
      return 'نشست شما به دلیل گذشت زمان منقضی شده است؛ لطفاً دوباره وارد شوید'
    }
    return startForgot ? 'حساب این شماره از قبل ساخته شده است؛ کد تأیید را بگیرید و رمز خود را تعیین کنید' : ''
  })
  const [loading, setLoading] = useState(false)
  const from = location.state?.from?.pathname || '/'

  // تبدیل ارقام فارسی به لاتین (کیبورد گوشی ممکن است فارسی تایپ کند)
  const fa2en = (s) => s.replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))

  const finishLogin = (data) => {
    setAuth(data.user, data.access, data.refresh)
    navigate(from, { replace: true })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authService.login({
        username: fa2en(form.username.trim()),
        password: fa2en(form.password),
      })
      finishLogin(data)
    } catch (err) {
      setError(err.response?.data?.non_field_errors?.[0] || 'اطلاعات ورود اشتباه است')
    } finally {
      setLoading(false)
    }
  }

  const handleForgot = async (e) => {
    e.preventDefault()
    setError(''); setNotice('')
    setLoading(true)
    try {
      const r = await authService.forgotPassword(fa2en(phone.trim()))
      setNotice(r.message || 'کد تأیید پیامک شد')
      setMode('reset')
    } catch (err) {
      setError(err.response?.data?.error || 'خطا در ارسال کد؛ دوباره تلاش کنید')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authService.resetPassword({
        phone: fa2en(phone.trim()),
        code: fa2en(code.trim()),
        password: newPassword,
      })
      finishLogin(data)
    } catch (err) {
      setError(err.response?.data?.error || 'کد تأیید اشتباه یا منقضی است')
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
          <h1 className="font-display font-bold text-2xl text-white">
            {mode === 'login' ? 'ورود به حساب' : 'بازیابی رمز عبور'}
          </h1>
          <p className="text-gray-steel text-sm mt-1">فروشگاه قطعات دوربین مداربسته</p>
        </div>

        {mode === 'login' && (
          <form onSubmit={handleSubmit} className="card p-6 space-y-4">
            {error && (
              <div className="bg-alert-red/10 border border-alert-red/20 rounded-xl p-3 text-sm text-alert-red">
                {error}
              </div>
            )}

            <div>
              <label className="label">شماره موبایل یا ایمیل</label>
              <input
                type="text" value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                required placeholder="09123456789 یا example@email.com"
                className="input" dir="ltr"
                autoCapitalize="off" autoCorrect="off" spellCheck={false}
              />
            </div>

            <div>
              <label className="label">رمز عبور</label>
              <PasswordInput
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                required placeholder="••••••••"
                className="input" dir="ltr"
              />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full py-3">
              {loading ? '...' : 'ورود'}
            </button>

            <button type="button" onClick={() => { setMode('forgot'); setError('') }}
              className="w-full text-center text-xs text-gray-steel hover:text-brand transition-colors">
              رمز عبور را فراموش کرده‌اید؟ / حساب من توسط فروشگاه ساخته شده
            </button>

            <p className="text-center text-sm text-gray-steel">
              حساب ندارید؟{' '}
              <Link to="/auth/register" className="text-brand dark:text-cyan hover:underline">
                ثبت‌نام کنید
              </Link>
            </p>
          </form>
        )}

        {mode === 'forgot' && (
          <form onSubmit={handleForgot} className="card p-6 space-y-4">
            <p className="text-xs text-gray-steel leading-6">
              شماره موبایل‌تان را وارد کنید؛ اگر حسابی با این شماره وجود داشته باشد (یا حساب شما را فروشگاه ساخته باشد)، کد تأیید پیامک می‌شود و با آن رمز جدید تعیین می‌کنید.
            </p>
            {notice && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 text-xs text-green-400">{notice}</div>
            )}
            {error && (
              <div className="bg-alert-red/10 border border-alert-red/20 rounded-xl p-3 text-sm text-alert-red">{error}</div>
            )}
            <div>
              <label className="label">شماره موبایل</label>
              <input
                type="text" value={phone}
                onChange={e => setPhone(e.target.value)}
                required placeholder="09123456789" maxLength={11}
                className="input" dir="ltr" inputMode="numeric"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full py-3">
              {loading ? '...' : 'ارسال کد تأیید'}
            </button>
            <button type="button" onClick={() => { setMode('login'); setError('') }}
              className="w-full text-center text-xs text-gray-steel hover:text-white transition-colors">
              ← برگشت به ورود
            </button>
          </form>
        )}

        {mode === 'reset' && (
          <form onSubmit={handleReset} className="card p-6 space-y-4">
            {notice && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 text-xs text-green-400">{notice}</div>
            )}
            {error && (
              <div className="bg-alert-red/10 border border-alert-red/20 rounded-xl p-3 text-sm text-alert-red">{error}</div>
            )}
            <div>
              <label className="label">کد تأیید پیامک‌شده به <span dir="ltr">{phone}</span></label>
              <input
                type="text" value={code}
                onChange={e => setCode(e.target.value)}
                required placeholder="کد ۵ رقمی" maxLength={5}
                className="input text-center tracking-[0.4em]" dir="ltr" inputMode="numeric"
              />
            </div>
            <div>
              <label className="label">رمز عبور جدید</label>
              <PasswordInput
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                required placeholder="حداقل ۸ کاراکتر"
                className="input" dir="ltr"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full py-3">
              {loading ? '...' : 'تعیین رمز و ورود'}
            </button>
            <button type="button" onClick={() => { setMode('forgot'); setError(''); setNotice('') }}
              className="w-full text-center text-xs text-gray-steel hover:text-white transition-colors">
              ارسال مجدد کد
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
