// صفحه «ویژگی‌های دسته‌ها» — مدیریت متمرکز اینکه هر دسته چه ویژگی‌هایی دارد
// این ویژگی‌ها در ویرایشگر محصول (کاتالوگ) برای محصولات همان دسته پر می‌شوند
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Tag } from 'lucide-react'
import api from '../../services/api'
import { PageLoader } from '../../components/ui'
import CategoryFieldsManager from '../../components/admin/CategoryFieldsManager'

const TYPE_LABEL = { board: 'برد', lens: 'لنز', modem: 'مودم', housing: 'بدنه', accessory: 'لوازم جانبی', recorder: 'برد دستگاه ضبط', other: 'سایر' }

export default function AdminCategoryFieldsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('cat') ? Number(searchParams.get('cat')) : null

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ['admin-categories-full'],
    queryFn: () => api.get('/catalog/categories/admin/').then(r => r.data),
  })

  // درخت دو سطحی برای چیپ‌های انتخاب
  const ordered = categories.filter(c => !c.parent)
    .flatMap(r => [r, ...categories.filter(c => c.parent === r.id)])
  const selected = categories.find(c => c.id === selectedId) || ordered[0] || null

  return (
    <div className="container-main py-8 max-w-4xl">
      <h1 className="font-display font-bold text-2xl text-white mb-2">ویژگی‌های دسته‌ها</h1>
      <p className="text-xs text-gray-steel mb-6">
        مشخص کنید هر دسته چه ویژگی‌هایی داشته باشد — این فیلدها در ویرایشگر محصول برای محصولات همان دسته پر می‌شوند.
      </p>

      {isLoading ? <PageLoader /> : (
        <>
          {/* انتخاب دسته */}
          <div className="flex gap-2 mb-6 flex-wrap">
            {ordered.map(c => (
              <button key={c.id} onClick={() => setSearchParams({ cat: String(c.id) })}
                className={`text-xs px-4 py-2 rounded-full border transition-all ${
                  selected?.id === c.id
                    ? 'bg-brand border-brand text-white'
                    : 'border-white/10 text-gray-steel hover:border-white/30'
                } ${c.parent ? 'mr-4' : ''}`}>
                {c.parent && <span className="font-normal ml-1">└</span>}
                {c.name}
                <span className="text-[9px] opacity-70 mr-1">({c.spec_fields.length})</span>
              </button>
            ))}
          </div>

          {selected && (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[var(--color-border)]">
                <Tag size={16} className="text-gold" />
                <span className="font-bold text-white text-sm">{selected.name}</span>
                <span className="badge text-[10px]">{TYPE_LABEL[selected.category_type] || selected.category_type}</span>
                <span className="text-[11px] text-gray-steel mr-auto">{selected.product_count} محصول</span>
              </div>
              <CategoryFieldsManager cat={selected} parentCat={selected.parent ? categories.find(x => x.id === selected.parent) : null} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
