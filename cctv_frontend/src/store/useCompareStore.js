import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { toast } from 'sonner'

export const MAX_COMPARE = 4

const useCompareStore = create(
  persist(
    (set, get) => ({
      // [{slug, name, category_id, image, min_price}]
      items: [],

      add: (product) => {
        const { items } = get()
        if (items.some(i => i.slug === product.slug)) {
          toast.info('این محصول قبلاً به مقایسه اضافه شده')
          return false
        }
        if (items.length >= MAX_COMPARE) {
          toast.error(`حداکثر ${MAX_COMPARE} محصول قابل مقایسه است`)
          return false
        }
        if (items.length > 0 && items[0].category_id !== product.category_id) {
          toast.error('فقط محصولات هم‌دسته قابل مقایسه هستند')
          return false
        }
        set({ items: [...items, product] })
        toast.success(items.length === 0
          ? 'به مقایسه اضافه شد — از آیکون ⚖ بالای صفحه می‌توانید ببینیدش'
          : 'به مقایسه اضافه شد')
        return true
      },

      remove: (slug) => set({ items: get().items.filter(i => i.slug !== slug) }),

      clear: () => set({ items: [] }),

      has: (slug) => get().items.some(i => i.slug === slug),
    }),
    { name: 'compare-storage' }
  )
)

export default useCompareStore
