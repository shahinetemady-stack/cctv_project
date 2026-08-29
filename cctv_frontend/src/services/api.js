import axios from 'axios'

// ─── Axios instance ────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

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
              return data.access
            })
            .finally(() => { refreshPromise = null })
          const access = await refreshPromise
          original.headers.Authorization = `Bearer ${access}`
          return api(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/auth/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

export default api
