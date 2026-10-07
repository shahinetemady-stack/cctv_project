// بنر پیشنهاد نصب وب‌اپ (PWA)
// ── کروم/اج (اندروید، ویندوز، لینوکس): رویداد beforeinstallprompt → نصب با یک دکمه
// ── iOS (سافاری): چنین رویدادی ندارد → راهنمای دستی Share → Add to Home Screen
// ── فایرفاکس: نصب وب‌اپ را پشتیبانی نمی‌کند → بنر نشان داده نمی‌شود
// اگر اپ نصب باشد یا کاربر بنر را تا ۷ روز پیش بسته باشد، چیزی نمایش داده نمی‌شود.
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

const DISMISS_KEY = 'installPromptDismissedAt'
const DISMISS_DAYS = 7
const SHOW_DELAY_MS = 8000

const isIos = () => /iphone|ipad|ipod/i.test(window.navigator.userAgent)

const isInstalled = () =>
  window.matchMedia('(display-mode: standalone)').matches ||
  window.navigator.standalone === true

const dismissedRecently = () => {
  const ts = Number(localStorage.getItem(DISMISS_KEY) || 0)
  return !!ts && Date.now() - ts < DISMISS_DAYS * 864e5
}

function ShareIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4 inline-block align-[-2px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v13" />
      <polyline points="7 8 12 3 17 8" />
      <path d="M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" />
    </svg>
  )
}

export default function InstallPrompt() {
  const deferredRef = useRef(null)
  const [canInstall, setCanInstall] = useState(false)
  const [visible, setVisible] = useState(false)
  const [ios] = useState(isIos)

  // شنود رویداد نصب (فقط کروم/اج) + ثبت نصب موفق
  useEffect(() => {
    if (isInstalled() || dismissedRecently()) return
    const onBeforeInstall = (e) => {
      e.preventDefault()
      deferredRef.current = e
      setCanInstall(true)
    }
    const onInstalled = () => {
      localStorage.setItem(DISMISS_KEY, String(Date.now()))
      setVisible(false)
      toast.success('برنامه دوربینکار با موفقیت نصب شد 🎉')
    }
    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  // نمایش بنر با تاخیر — نه بلافاصله بعد از ورود کاربر
  useEffect(() => {
    if (isInstalled() || dismissedRecently()) return
    if (!canInstall && !ios) return
    const t = setTimeout(() => setVisible(true), SHOW_DELAY_MS)
    return () => clearTimeout(t)
  }, [canInstall, ios])

  if (!visible) return null

  const install = async () => {
    const promptEvent = deferredRef.current
    if (!promptEvent) return
    promptEvent.prompt()
    const { outcome } = await promptEvent.userChoice
    if (outcome === 'accepted') {
      localStorage.setItem(DISMISS_KEY, String(Date.now()))
      setVisible(false)
      toast.success('برنامه دوربینکار با موفقیت نصب شد 🎉')
    }
    deferredRef.current = null
    setCanInstall(false)
  }

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
    setVisible(false)
  }

  return (
    // لایه بیرونی فقط جایگذاری می‌کند (بدون transform روی خود کارت) تا با
    // transform انیمیشن ورود تداخل نکند — قبلاً کارت به راست بیرون می‌زد.
    // موبایل: کمی بالاتر از ناوبری پایین — دسکتاپ: وسط صفحه
    <div
      className="fixed inset-x-0 bottom-[calc(150px+env(safe-area-inset-bottom,0px))] md:top-0 md:bottom-0 md:items-center z-[70] flex justify-center px-4 pointer-events-none"
    >
      <div
        dir="rtl"
        role="dialog"
        aria-label="پیشنهاد نصب اپلیکیشن"
        className="pointer-events-auto relative w-full max-w-sm rounded-2xl overflow-hidden shadow-2xl animate-mega-in"
        style={{
          background: 'var(--color-bg-elevated)',
          border: '1px solid rgba(251,192,45,0.3)',
          boxShadow: '0 24px 64px -12px rgba(0,0,0,0.75), 0 0 0 1px rgba(251,192,45,0.06)',
        }}
      >
        {/* خط طلایی بالای کارت — هم‌سبک مگامنو */}
        <div className="h-[3px] w-full" style={{ background: 'var(--gradient-gold)' }} />

        <button
          onClick={dismiss}
          aria-label="بستن"
          className="absolute top-3 left-3 z-10 p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        <div className="p-5 flex flex-col items-center text-center">
          {/* آیکن اپ با هاله طلایی */}
          <div
            className="w-14 h-14 rounded-2xl overflow-hidden mb-3"
            style={{ boxShadow: 'var(--shadow-gold)', border: '1px solid rgba(251,192,45,0.4)' }}
          >
            <img src="/icons/icon-96.png" alt="" width={56} height={56} className="w-full h-full" />
          </div>
          <div className="font-display font-extrabold text-[15px] text-[var(--color-text-primary)] tracking-tight">
            برنامه <span className="gold-text">دوربینکار</span> را نصب کن
          </div>
          <div className="text-[11px] leading-relaxed mt-1.5 text-[var(--color-text-secondary)]">
            {ios ? (
              <>
                از به‌روزترین قیمت‌ها و اخبار دوربین مداربسته اولین نفر باخبر شو —
                دکمهٔ <ShareIcon /> (اشتراک‌گذاری) سافاری را بزنید و
                «<span dir="ltr">Add to Home Screen</span>» را انتخاب کنید
              </>
            ) : (
              'از به‌روزترین قیمت‌ها و اخبار دوربین مداربسته اولین نفر باخبر شو'
            )}
          </div>
          {canInstall && (
            <button onClick={install} className="btn-gold w-full text-sm py-2.5 mt-3.5 font-bold">
              نصب اپلیکیشن
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
