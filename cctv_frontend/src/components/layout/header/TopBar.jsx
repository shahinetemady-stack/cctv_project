import { SparkleIcon } from './icons'

// ─── نوار اطلاع‌رسانی بالای سایت (متن از تنظیمات سایت) ────────
export default function TopBar({ settings }) {
  const text = settings?.announcement_text
  const phone = settings?.contact_phone

  // رندر شرطی + انیمیشن ورود CSS فقط روی opacity/transform —
  // انیمیشن height:auto فریم‌به‌فریم باعث forced reflow می‌شد
  if (!text) return null

  return (
    <div
      className="relative overflow-hidden pt-safe animate-topbar-in"
      style={{ background: 'var(--gradient-gold)' }}
    >
      <div
        className="container-site flex items-center justify-center gap-2 py-1.5 text-center"
        style={{ color: 'var(--color-brand-contrast)' }}
      >
        <span className="animate-wiggle">
          <SparkleIcon />
        </span>
        <span className="text-xs font-semibold">{text}</span>
        <span className="animate-wiggle-rev">
          <SparkleIcon />
        </span>
        {phone && (
          <a
            href={`tel:${phone}`}
            dir="ltr"
            className="hidden md:inline-flex items-center gap-1 mr-4 text-[11px] font-bold opacity-75 hover:opacity-100 transition-opacity"
          >
            📞 {phone}
          </a>
        )}
      </div>
    </div>
  )
}
