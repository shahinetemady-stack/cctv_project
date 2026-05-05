/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ─── Tech Steel Blue Palette ───────────────────────────────
        navy:    { DEFAULT: '#0A1628', 800: '#0d1e38', 700: '#112548' },
        steel:   { DEFAULT: '#1E3A5F', light: '#2a4f80' },
        brand:   { DEFAULT: '#0066FF', light: '#3385ff', dark: '#0052cc' },
        cyan:    { DEFAULT: '#00D4FF', dim: '#00b8e0' },
        gray:    { steel: '#8892A4',   soft: '#CBD5E1' },
        surface: { light: '#F0F4F8',   card: '#ffffff' },
        alert:   { red: '#FF3B3B',     green: '#00C896', orange: '#FF9500' },
      },
      fontFamily: {
        // سفارشی — فونت وزیرمتن برای فارسی + JetBrains Mono برای کدها
        sans:  ['Vazirmatn', 'system-ui', 'sans-serif'],
        mono:  ['JetBrains Mono', 'monospace'],
        display: ['Exo 2', 'Vazirmatn', 'sans-serif'],
      },
      backgroundImage: {
        'grid-pattern': `
          linear-gradient(rgba(0,102,255,0.05) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,102,255,0.05) 1px, transparent 1px)
        `,
        'hero-glow': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,102,255,0.15), transparent)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'fade-in':    'fadeIn 0.4s ease-out',
        'slide-up':   'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'scan':       'scan 3s linear infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 },                      to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        scan:    { '0%,100%': { backgroundPosition: '0 0' },  '50%': { backgroundPosition: '0 100%' } },
      },
      boxShadow: {
        'brand':   '0 0 0 1px rgba(0,102,255,0.3), 0 4px 24px rgba(0,102,255,0.15)',
        'card':    '0 1px 3px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06)',
        'card-dark': '0 1px 3px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.3)',
        'glow':    '0 0 20px rgba(0,212,255,0.3)',
      },
    },
  },
  plugins: [],
}
