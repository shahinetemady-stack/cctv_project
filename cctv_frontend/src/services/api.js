import axios from 'axios'
import useAuthStore from '../store/useAuthStore'

// ─── Axios instance ────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ── خروج کامل: پاک کردن localStorage + استور zustand + رفتن به صفحه ورود ──
// بدون پاک کردن استور، GuestOnly کاربر را از صفحه ورود به / برمی‌گرداند و
// منو همچنان «لاگین» نمایش داده می‌شود در حالی که همه درخواست‌ها 401 می‌خورند
function forceLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  useAuthStore.setState({ user: null, accessToken: null, refreshToken: null })
  // نشست منقضی شده — به کاربر اطلاع بده (LoginPage این پرچم را می‌خواند)
  sessionStorage.setItem('auth_notice', 'expired')
  if (window.location.pathname !== '/auth/login') {
    window.location.href = '/auth/login'
  }
}

// ── Request interceptor: attach JWT ──────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  // پیش‌فرض سراسری application/json است — برای آپلود فایل (FormData) باید حذف شود
  // تا مرورگر خودش multipart/form-data با boundary درست بسازد
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

// ── Response interceptor: token refresh on 401 ───────────────────────────
// بک‌اند با ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION کار می‌کند، پس:
// ۱) توکن رفرش جدید برگردانده‌شده باید ذخیره شود وگرنه رفرش بعدی حتماً شکست می‌خورد
// ۲) چند درخواست موازی ۴۰۱ نباید هرکدام جداگانه رفرش بزنند — اولی توکن را rotate
//    می‌کند و بقیه با توکن blacklist‌شده می‌افتند بیرون و کاربر لاگ‌اوت می‌شود.
//    همه روی یک Promise رفرش مشترک سوار می‌شوند.
let refreshPromise = null

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          refreshPromise ??= axios
            .post(
              `${import.meta.env.VITE_API_URL || '/api'}/users/auth/refresh/`,
              { refresh }
            )
            .then(({ data }) => {
              localStorage.setItem('access_token', data.access)
              if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
              // استور zustand هم به‌روز شود تا با localStorage هماهنگ بماند
              useAuthStore.setState({
                accessToken: data.access,
                ...(data.refresh ? { refreshToken: data.refresh } : {}),
              })
              return data.access
            })
            .finally(() => { refreshPromise = null })
          const access = await refreshPromise
          original.headers.Authorization = `Bearer ${access}`
          return api(original)
        } catch {
          forceLogout()
        }
      } else if (useAuthStore.getState().accessToken) {
        // استور فکر می‌کند لاگین است ولی توکنی در localStorage نیست —
        // نشست قبلاً منقضی شده؛ کامل خارج شو تا کاربر فقط «ورود» را بزند
        forceLogout()
      }
    }
    return Promise.reject(err)
  }
)

export default api
