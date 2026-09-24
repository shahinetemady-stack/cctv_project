import { Sun, Moon } from 'lucide-react'
import useThemeStore from '../../../store/useThemeStore'

// دکمه تعویض تم دارک/لایت — آیکون خورشید/ماه با انیمیشن چرخشی
export default function ThemeToggle({ className = '' }) {
  const { theme, toggle } = useThemeStore()
  const isDark = theme === 'dark'
  return (
    <button
      onClick={toggle}
      className={`${className} transition-transform active:scale-[0.85] active:rotate-[25deg]`}
      aria-label={isDark ? 'حالت روشن' : 'حالت تاریک'}
      title={isDark ? 'حالت روشن' : 'حالت تاریک'}
    >
      {/* key بر اساس تم: با تعویض تم، آیکون دوباره مانت و انیمیشن ورود CSS اجرا می‌شود */}
      <span key={theme} className="animate-theme-icon" style={{ display: 'flex' }}>
        {isDark ? <Sun size={19} /> : <Moon size={19} />}
      </span>
    </button>
  )
}
