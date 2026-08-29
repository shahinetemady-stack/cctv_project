import { motion } from 'framer-motion'
import { Sun, Moon } from 'lucide-react'
import useThemeStore from '../../../store/useThemeStore'

// دکمه تعویض تم دارک/لایت — آیکون خورشید/ماه با انیمیشن چرخشی
export default function ThemeToggle({ className = '' }) {
  const { theme, toggle } = useThemeStore()
  const isDark = theme === 'dark'
  return (
    <motion.button
      onClick={toggle}
      className={className}
      aria-label={isDark ? 'حالت روشن' : 'حالت تاریک'}
      title={isDark ? 'حالت روشن' : 'حالت تاریک'}
      whileTap={{ scale: 0.85, rotate: 25 }}
      transition={{ type: 'spring', stiffness: 500, damping: 22 }}
    >
      <motion.span
        key={theme}
        initial={{ rotate: -60, opacity: 0, scale: 0.6 }}
        animate={{ rotate: 0, opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 350, damping: 20 }}
        style={{ display: 'flex' }}
      >
        {isDark ? <Sun size={19} /> : <Moon size={19} />}
      </motion.span>
    </motion.button>
  )
}
