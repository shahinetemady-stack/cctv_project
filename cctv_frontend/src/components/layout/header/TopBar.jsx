import { motion, AnimatePresence } from 'framer-motion'
import { SparkleIcon } from './icons'

const SPRING_SMOOTH = { type: 'spring', stiffness: 300, damping: 30 }

// ─── نوار اطلاع‌رسانی بالای سایت (متن از تنظیمات سایت) ────────
export default function TopBar({ settings }) {
  const text = settings?.announcement_text
  const phone = settings?.contact_phone

  return (
    <AnimatePresence>
      {text && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={SPRING_SMOOTH}
          className="relative overflow-hidden pt-safe"
          style={{ background: 'var(--gradient-gold)' }}
        >
          <div
            className="container-site flex items-center justify-center gap-2 py-1.5 text-center"
            style={{ color: 'var(--color-brand-contrast)' }}
          >
            <motion.span
              animate={{ rotate: [0, 15, -15, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            >
              <SparkleIcon />
            </motion.span>
            <span className="text-xs font-semibold">{text}</span>
            <motion.span
              animate={{ rotate: [0, -15, 15, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            >
              <SparkleIcon />
            </motion.span>
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
        </motion.div>
      )}
    </AnimatePresence>
  )
}
