import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDownIcon, UserIcon, GridIcon, LogoutIcon } from './icons'

const SPRING_SNAPPY = { type: 'spring', stiffness: 500, damping: 35 }
const SPRING_SMOOTH = { type: 'spring', stiffness: 300, damping: 30 }

const scaleIn = {
  hidden: { opacity: 0, scale: 0.96, y: -4 },
  visible: { opacity: 1, scale: 1, y: 0, transition: SPRING_SNAPPY },
  exit: { opacity: 0, scale: 0.96, y: -4, transition: { duration: 0.12 } },
}
const itemFadeUp = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: SPRING_SMOOTH },
}

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
        <motion.div whileTap={{ scale: 0.97 }} transition={SPRING_SNAPPY}>
          <Link
            to="/auth/login"
            className="text-xs font-semibold px-4 py-2 rounded-xl border border-[var(--color-border-strong)] text-[var(--color-text-primary)] hover:border-gold hover:text-gold transition-colors"
          >
            ورود
          </Link>
        </motion.div>
        <motion.div
          whileHover={{ scale: 1.04, y: -1 }}
          whileTap={{ scale: 0.96, y: 0 }}
          transition={SPRING_SNAPPY}
        >
          <Link to="/auth/register" className="btn-gold text-xs">
            ثبت‌نام
          </Link>
        </motion.div>
      </>
    )
  }

  return (
    <div className="relative" ref={ref}>
      <motion.button
        onClick={() => setOpen((v) => !v)}
        whileTap={{ scale: 0.97 }}
        transition={SPRING_SNAPPY}
        className={`flex items-center gap-2 px-2 py-1.5 rounded-xl border transition-colors ${
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
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={SPRING_SNAPPY}>
          <ChevronDownIcon className="text-[var(--color-text-muted)]" />
        </motion.span>
      </motion.button>

      {/* key بر اساس مسیر: با ناوبری، دراپ‌داون فوراً آن‌مانت می‌شود و باز نمی‌ماند */}
      <AnimatePresence key={location.pathname}>
        {open && (
          <motion.div
            className="absolute left-0 top-full mt-2 w-60 glass rounded-2xl p-2 z-50"
            variants={scaleIn}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{ transformOrigin: 'top left', boxShadow: 'var(--shadow-modal)' }}
          >
            <motion.div
              variants={itemFadeUp}
              className="flex items-center gap-3 p-3 mb-1 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)]"
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
            </motion.div>

            <motion.div variants={itemFadeUp}>
              <Link to="/account" className={menuItemCls} onClick={() => setOpen(false)}>
                <UserIcon />
                <span>حساب کاربری</span>
              </Link>
            </motion.div>

            {isStaff && (
              <motion.div variants={itemFadeUp}>
                <Link to="/admin/dashboard" className={menuItemCls} onClick={() => setOpen(false)}>
                  <GridIcon />
                  <span>پنل مدیریت</span>
                </Link>
              </motion.div>
            )}

            <hr className="divider my-1" />

            <motion.button
              onClick={onLogout}
              variants={itemFadeUp}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] w-full text-alert-red hover:bg-[rgba(248,113,113,0.08)] transition-colors"
            >
              <LogoutIcon />
              <span>خروج</span>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
