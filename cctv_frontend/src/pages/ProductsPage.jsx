import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../services/catalog'
import ProductCard from '../components/product/ProductCard'
import FilterPanel from '../components/product/FilterPanel'
import { PageLoader, EmptyState, ErrorMessage, Spinner } from '../components/ui'

function Pagination({ page, totalPages, onPage }) {
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center justify-center gap-2 mt-10">
      <button onClick={() => onPage(page - 1)} disabled={page === 1}
        className="btn-ghost px-3 py-2 disabled:opacity-30">← قبلی</button>
      {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
        const p = totalPages <= 7 ? i + 1 : page <= 4 ? i + 1 : page + i - 3
        if (p < 1 || p > totalPages) return null
        return (
          <button key={p} onClick={() => onPage(p)}
            className={`w-9 h-9 rounded-lg text-sm font-medium transition-all
              ${p === page ? 'bg-brand text-white shadow-brand' : 'btn-ghost'}`}>
            {p}
          </button>
        )
      })}
      <button onClick={() => onPage(page + 1)} disabled={page === totalPages}
        className="btn-ghost px-3 py-2 disabled:opacity-30">بعدی →</button>
    </div>
  )
}

export default function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState({
    part_type: searchParams.get('part_type') || '',
    chipset:   searchParams.get('chipset') || '',
    voltage:   searchParams.get('voltage') || '',
    lens_mount:searchParams.get('lens_mount') || '',
    in_stock:  searchParams.get('in_stock') || '',
    search:    searchParams.get('search') || '',
    category:  searchParams.get('category') || '',
  })
  const [page, setPage] = useState(1)
  const [showFilter, setShowFilter] = useState(false)

  // sync params → filters
  useEffect(() => {
    const q = Object.fromEntries(searchParams)
    setFilters(prev => ({ ...prev, ...q }))
    setPage(1)
  }, [searchParams])

  const activeFilters = Object.values(filters).filter(Boolean).length

  const params = { ...filters, page }
  Object.keys(params).forEach(k => !params[k] && delete params[k])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['products', params],
    queryFn: () => catalogService.getProducts(params),
    keepPreviousData: true,
  })

  const handleFilters = (f) => {
    setFilters(f)
    setPage(1)
    const next = {}
    Object.entries(f).forEach(([k, v]) => { if (v) next[k] = v })
    setSearchParams(next)
  }

  const products = data?.results || []
  const totalPages = data ? Math.ceil(data.count / 24) : 0

  return (
    <div className="container-main py-8">
      {/* سربرگ */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-2xl text-white">محصولات</h1>
          {data && (
            <p className="text-sm text-gray-steel mt-1">
              {data.count.toLocaleString('fa-IR')} محصول یافت شد
            </p>
          )}
        </div>
        <button
          onClick={() => setShowFilter(!showFilter)}
          className="btn-secondary md:hidden flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M3 4h18M7 12h10M11 20h2" />
          </svg>
          فیلتر
          {activeFilters > 0 && (
            <span className="badge-blue text-[10px]">{activeFilters}</span>
          )}
        </button>
      </div>

      <div className="flex gap-6">
        {/* فیلتر — دسکتاپ */}
        <div className="hidden md:block w-64 flex-shrink-0">
          <FilterPanel filters={filters} onChange={handleFilters} />
        </div>

        {/* فیلتر — موبایل */}
        {showFilter && (
          <div className="fixed inset-0 z-50 bg-black/60 md:hidden" onClick={() => setShowFilter(false)}>
            <div className="absolute left-0 top-0 h-full w-72 bg-navy p-4 overflow-y-auto"
              onClick={e => e.stopPropagation()}>
              <FilterPanel filters={filters} onChange={(f) => { handleFilters(f); setShowFilter(false) }} />
            </div>
          </div>
        )}

        {/* محصولات */}
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array(12).fill(0).map((_, i) => <div key={i} className="skeleton h-72 rounded-2xl" />)}
            </div>
          ) : isError ? (
            <ErrorMessage message="خطا در بارگذاری محصولات" retry={refetch} />
          ) : products.length === 0 ? (
            <EmptyState icon="🔍" title="محصولی یافت نشد"
              description="فیلترها را تغییر دهید یا عبارت جستجو را اصلاح کنید"
              action={<button onClick={() => handleFilters({})} className="btn-secondary">پاک کردن فیلترها</button>}
            />
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {products.map(p => <ProductCard key={p.id} product={p} />)}
              </div>
              <Pagination page={page} totalPages={totalPages} onPage={setPage} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
