/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ─── DOORBINKAR SENTINEL — رنگ‌ها var-driven تا با تم لایت/دارک عوض شوند
        // نام‌ها (gold/navy/...) برای سازگاری با کلاس‌های موجود حفظ شده‌اند
        gold: {
          DEFAULT: 'rgb(var(--color-brand-rgb) / <alpha-value>)',
          light: 'rgb(var(--color-brand-light-rgb) / <alpha-value>)',
          dark: '#F9A825',
          deep: '#C49000',
        },
        brand: {
          DEFAULT: 'rgb(var(--color-brand-rgb) / <alpha-value>)',
          light: 'rgb(var(--color-brand-light-rgb) / <alpha-value>)',
          dark: '#F9A825',
        },
        ink: {
          DEFAULT: 'rgb(var(--color-bg-secondary-rgb) / <alpha-value>)',
          900: 'rgb(var(--color-bg-secondary-rgb) / <alpha-value>)',
          800: 'rgb(var(--color-bg-secondary-rgb) / <alpha-value>)',
          700: 'rgb(var(--color-bg-card-rgb) / <alpha-value>)',
          600: 'rgb(var(--color-bg-elevated-rgb) / <alpha-value>)',
          500: 'rgb(var(--color-bg-elevated-rgb) / <alpha-value>)',
        },
        smoke: {
          DEFAULT: '#A1A1AA',
          light: '#D4D4D8',
          dim: '#71717A',
        },
        alert: {
          red: 'var(--color-danger)',
          green: 'var(--color-success)',
          orange: 'var(--color-warning)',
          blue: 'var(--color-info)',
        },
        // ─── Back-compat aliases ──────────────────────────────
        navy: {
          DEFAULT: 'rgb(var(--color-bg-secondary-rgb) / <alpha-value>)',
          800: 'rgb(var(--color-bg-secondary-rgb) / <alpha-value>)',
          700: 'rgb(var(--color-bg-card-rgb) / <alpha-value>)',
        },
        steel: {
          DEFAULT: 'rgb(var(--color-bg-elevated-rgb) / <alpha-value>)',
          light: 'rgb(var(--color-bg-elevated-rgb) / <alpha-value>)',
        },
        cyan: { DEFAULT: 'rgb(var(--color-brand-light-rgb) / <alpha-value>)', dim: '#F9A825' },
        gray: { steel: '#A1A1AA', soft: '#D4D4D8' },
        surface: { light: 'rgb(var(--color-bg-secondary-rgb) / <alpha-value>)', card: 'rgb(var(--color-bg-card-rgb) / <alpha-value>)' },
      },
      fontFamily: {
        sans: ['Vazirmatn', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Exo 2', 'Vazirmatn', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-gold': 'var(--gradient-gold)',
        'gold-radial': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(251,192,45,0.12), transparent)',
        'grid-pattern': `
          linear-gradient(var(--bg-grid-line) 1px, transparent 1px),
          linear-gradient(90deg, var(--bg-grid-line) 1px, transparent 1px)
        `,
        'hero-glow': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(251,192,45,0.12), transparent)',
      },
      backgroundSize: {
        'grid': '44px 44px',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'float': 'float 5s ease-in-out infinite',
        'pulse-gold': 'pulseGold 2.5s ease-in-out infinite',
        'shimmer': 'shimmer 1.4s infinite',
        // aliases قدیمی
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'scan': 'scan 3s linear infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        float: { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-10px)' } },
        pulseGold: {
          '0%,100%': { boxShadow: '0 0 0 0 rgba(251,192,45,0.35)' },
          '50%': { boxShadow: '0 0 0 10px rgba(251,192,45,0)' },
        },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        scan: { '0%,100%': { backgroundPosition: '0 0' }, '50%': { backgroundPosition: '0 100%' } },
      },
      boxShadow: {
        'card': 'var(--shadow-card)',
        'card-hover': 'var(--shadow-card-hover)',
        'gold': 'var(--shadow-gold)',
        'gold-strong': 'var(--shadow-gold-strong)',
        // aliases قدیمی
        'brand': 'var(--shadow-gold)',
        'card-dark': 'var(--shadow-card)',
        'glow': '0 0 20px rgba(251,192,45,0.3)',
      },
    },
  },
  plugins: [],
}
