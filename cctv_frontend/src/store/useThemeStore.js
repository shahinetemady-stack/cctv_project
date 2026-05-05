import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useThemeStore = create(
  persist(
    (set, get) => ({
      dark: true,
      toggle: () => {
        const next = !get().dark
        document.documentElement.classList.toggle('dark', next)
        set({ dark: next })
      },
      init: () => {
        document.documentElement.classList.toggle('dark', get().dark)
      },
    }),
    { name: 'theme-store' }
  )
)

export default useThemeStore
