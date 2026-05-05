import { create } from 'zustand'

// این store فقط cache محلی است — داده واقعی از API می‌آید
const useCartStore = create((set) => ({
  count: 0,
  inquiryCount: 0,
  setCount: (n) => set({ count: n }),
  setInquiryCount: (n) => set({ inquiryCount: n }),
  increment: () => set((s) => ({ count: s.count + 1 })),
  decrement: () => set((s) => ({ count: Math.max(0, s.count - 1) })),
}))

export default useCartStore
