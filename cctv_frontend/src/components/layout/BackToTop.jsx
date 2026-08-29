import { useEffect, useState } from 'react'
import { ArrowUp } from 'lucide-react'

// ─── دکمه شناور «بازگشت به بالا» — بعد از کمی اسکرول ظاهر می‌شود ───
// حلقه دور دکمه درصد پیشرفت اسکرول صفحه را نشان می‌دهد.
// گوشه پایین-راست؛ در موبایل بالای BottomNav می‌ایستد تا هم‌پوشانی نکند.
const R = 20
const CIRCUMFERENCE = 2 * Math.PI * R

export default function BackToTop() {
  const [visible, setVisible] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      setVisible(window.scrollY > 400)
      setProgress(max > 0 ? Math.min(1, window.scrollY / max) : 0)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="بازگشت به بالای صفحه"
      title="بازگشت به بالا"
      className="fixed right-4 bottom-20 md:bottom-6 z-[99996] w-12 h-12 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-elevated)]/85 backdrop-blur-md text-[var(--color-text-secondary)] hover:text-gold hover:border-gold/50 hover:shadow-lg hover:shadow-gold/10 transition-all duration-300 flex items-center justify-center"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(12px)',
        pointerEvents: visible ? 'auto' : 'none',
      }}
    >
      {/* حلقه پیشرفت اسکرول */}
      <svg viewBox="0 0 48 48" className="absolute inset-0 w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="24" cy="24" r={R} fill="none" strokeWidth="2.5"
          stroke="var(--color-border)" />
        <circle cx="24" cy="24" r={R} fill="none" strokeWidth="2.5" strokeLinecap="round"
          stroke="var(--color-brand)"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - progress)} />
      </svg>
      <ArrowUp size={18} strokeWidth={2.2} />
    </button>
  )
}
