import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronDownIcon, UserIcon, GridIcon, LogoutIcon } from './icons'

const menuItemCls =
  'flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] text-[var(--color-text-secondary)] hover:text-gold hover:bg-[var(--color-brand-softer)] transition-colors'

// برچسب نوع عضویت کاربر — زیر شماره/نام در منو
const TIER_LABELS = { silver: 'همکار سیلور', gold: 'همکار گلد', platinum: 'همکار پلاتینیوم' }
function membershipLabel(user) {
  const p = user?.profile
  if (p?.user_type === 'partner') {
    if (!p.is_approved) return 'همکار (در انتظار تأیید)'
    return TIER_LABELS[p.partner_tier] || 'همکار'
  }
  return 'مشتری عمومی'
}

// ─── نام نمایشی مشتری — نام و نام خانوادگی، وگرنه شماره موبایل ─────────────
function displayName(user) {
  const full = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return full || user?.username || user?.phone || ''
}

// ─── منوی کاربر (وضعیت لاگین / مهمان) — فقط دسکتاپ ────────────
export default function UserMenu({ user, isStaff, onLogout }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const location = useLocation()

  // بستن با کلیک بیرون
  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  // بستن با تغییر مسیر
  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  // حالت مهمان: ورود / ثبت‌نام
  if (!user) {
    return (
      <>
        <div className="transition-transform active:scale-[0.97]">
          <Link
            to="/auth/login"
            className="text-xs font-semibold px-4 py-2 rounded-xl border border-[var(--color-border-strong)] text-[var(--color-text-primary)] hover:border-gold hover:text-gold transition-colors"
          >
            ورود
          </Link>
        </div>
        <div className="transition-transform hover:scale-[1.04] hover:-translate-y-px active:scale-[0.96] active:translate-y-0">
          <Link to="/auth/register" className="btn-gold text-xs">
            ثبت‌نام
          </Link>
        </div>
      </>
    )
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-2 px-2 py-1.5 rounded-xl border transition-all active:scale-[0.97] ${
          open
            ? 'border-[rgba(251,192,45,0.35)] bg-[var(--color-brand-softer)]'
            : 'border-transparent hover:bg-white/5'
        }`}
      >
        {/* کادر نارنجی = نام مشتری (عرض متناسب با متن) — کنارش شماره موبایل */}
        <div
          className="h-8 px-2.5 rounded-lg flex items-center justify-center text-xs font-bold whitespace-nowrap max-w-[140px] truncate"
          style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
        >
          {displayName(user)}
        </div>
        <span className="text-xs font-medium hidden lg:block font-mono" dir="ltr">
          {user.phone || user.username}
        </span>
        <span className={`inline-flex transition-transform duration-300 ${open ? 'rotate-180' : ''}`}>
          <ChevronDownIcon className="text-[var(--color-text-muted)]" />
        </span>
      </button>

      {/* رندر شرطی + انیمیشن ورود CSS — بدون انیمیشن خروج تا با ناوبری گیر نکند */}
      {open && (
        <div
          className="absolute left-0 top-full mt-2 w-60 glass rounded-2xl p-2 z-50 animate-dropdown-in"
          style={{ boxShadow: 'var(--shadow-modal)' }}
        >
          <div
            className="flex items-center gap-3 p-3 mb-1 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] animate-fade-up-sm"
          >
              <div
                className="h-10 px-3 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0 max-w-[130px] truncate"
                style={{ background: 'var(--gradient-gold)', color: 'var(--color-brand-contrast)' }}
              >
                {displayName(user)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-bold text-[var(--color-text-primary)] truncate font-mono" dir="ltr">
                  {user.phone || user.username}
                </div>
                <div className={`text-[11px] ${isStaff ? 'text-gold' : 'text-[var(--color-text-muted)]'}`}>
                  {isStaff ? '✦ کاربر ارشد' : membershipLabel(user)}
                </div>
              </div>
          </div>

          <div className="animate-fade-up-sm" style={{ animationDelay: '0.05s' }}>
            <Link to="/account" className={menuItemCls} onClick={() => setOpen(false)}>
              <UserIcon />
              <span>حساب کاربری</span>
            </Link>
          </div>

          {isStaff && (
            <div className="animate-fade-up-sm" style={{ animationDelay: '0.1s' }}>
              <Link to="/admin/dashboard" className={menuItemCls} onClick={() => setOpen(false)}>
                <GridIcon />
                <span>پنل مدیریت</span>
              </Link>
            </div>
          )}

          <hr className="divider my-1" />

          <button
            onClick={onLogout}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] w-full text-alert-red hover:bg-[rgba(248,113,113,0.08)] transition-all active:scale-[0.98] animate-fade-up-sm"
            style={{ animationDelay: '0.15s' }}
          >
            <LogoutIcon />
            <span>خروج</span>
          </button>
        </div>
      )}
    </div>
  )
}
