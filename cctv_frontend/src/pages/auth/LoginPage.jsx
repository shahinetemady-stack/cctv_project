// src/pages/auth/LoginPage.jsx
import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { authService } from '../../services/auth'
import useAuthStore from '../../store/useAuthStore'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const from = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authService.login(form)
      setAuth(data.user, data.access, data.refresh)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.response?.data?.non_field_errors?.[0] || 'خطا در ورود')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* لوگو */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-brand rounded-2xl flex items-center justify-center
            shadow-brand mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.889L15 14v-4zM3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/>
            </svg>
          </div>
          <h1 className="font-display font-bold text-2xl text-white">ورود به حساب</h1>
          <p className="text-gray-steel text-sm mt-1">فروشگاه قطعات دوربین مداربسته</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          {error && (
            <div className="bg-alert-red/10 border border-alert-red/20 rounded-xl p-3 text-sm text-alert-red">
              {error}
            </div>
          )}

          <div>
            <label className="label">ایمیل</label>
            <input type="email" value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              required placeholder="example@email.com"
              className="input" dir="ltr" />
          </div>

          <div>
            <label className="label">رمز عبور</label>
            <input type="password" value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              required placeholder="••••••••"
              className="input" dir="ltr" />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full py-3">
            {loading ? '...' : 'ورود'}
          </button>

          <p className="text-center text-sm text-gray-steel">
            حساب ندارید؟{' '}
            <Link to="/auth/register" className="text-brand dark:text-cyan hover:underline">
              ثبت‌نام کنید
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
