import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      toggle: () => set({ theme: get().theme === 'dark' ? 'light' : 'dark' }),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'site-theme' }
  )
)

// اعمال تم روی <html> — data-theme موتور تعویض توکن‌های CSS است
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', theme === 'dark' ? '#0A0A0B' : '#FAF8F3')
}

// هر تغییر تم بلافاصله اعمال شود
useThemeStore.subscribe((s) => applyTheme(s.theme))

export default useThemeStore
