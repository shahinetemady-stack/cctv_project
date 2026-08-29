import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../services/catalog'
import api from '../services/api'
import ProductCard from '../components/product/ProductCard'
import FilterPanel from '../components/product/FilterPanel'
import { PageLoader, EmptyState, ErrorMessage, Spinner } from '../components/ui'
import Seo from '../components/Seo'

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
    category:      searchParams.get('category') || '',
    category_type: searchParams.get('category_type') || '',
    brand:         searchParams.get('brand') || '',
    search:        searchParams.get('search') || '',
    in_stock:      searchParams.get('in_stock') || '',
    discounted:    searchParams.get('discounted') || '',
  })
  const [page, setPage] = useState(1)
  const [showFilter, setShowFilter] = useState(false)
  // جستجوی هوشمند دوزبانه — وقتی فعال است، جایگزین لیست عادی می‌شود
  const [smartInput, setSmartInput] = useState('')
  const [smartQuery, setSmartQuery] = useState('')

  const { data: smartData, isFetching: smartLoading } = useQuery({
    queryKey: ['products-smart-search', smartQuery],
    queryFn: () => api.get('/catalog/products/search/', { params: { q: smartQuery } }).then(r => r.data),
    enabled: smartQuery.trim().length >= 2,
  })
  const smartMode = smartQuery.trim().length >= 2

  // جستجوی زنده — با کمی تأخیر بعد از توقف تایپ، بدون نیاز به اینتر
  useEffect(() => {
    const t = setTimeout(() => setSmartQuery(smartInput.trim()), 400)
    return () => clearTimeout(t)
  }, [smartInput])

  // sync params → filters — پارامتر search همیشه به جستجوی هوشمند می‌رود (نه فیلتر ساده)
  useEffect(() => {
    const q = Object.fromEntries(searchParams)
    const { search, ...rest } = q
    setFilters(prev => ({ ...prev, ...rest, search: '' }))
    if (search) {
      setSmartInput(search)
      setSmartQuery(search)
    }
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

  const products = smartMode ? (smartData?.results || []) : (data?.results || [])
  const totalPages = data && !smartMode ? Math.ceil(data.count / 24) : 0

  return (
    <div className="container-main py-8">
      <Seo
        title="محصولات | دوربینکار"
        description="کاتالوگ قطعات دوربین مداربسته — برد، لنز، مودم، بدنه و متعلقات با به‌روزترین قیمت‌ها."
        canonical="/products"
      />

      {/* نوار جستجوی هوشمند دوزبانه */}
      <form
        onSubmit={(e) => { e.preventDefault(); setSmartQuery(smartInput.trim()) }}
        className="relative mb-6"
      >
        <input
          value={smartInput}
          onChange={(e) => {
            setSmartInput(e.target.value)
            if (!e.target.value.trim()) setSmartQuery('')
          }}
          placeholder="جستجوی هوشمند: فارسی یا English... (مثل: لنز ytot 5mp یا برد سونی)"
          className="input w-full text-sm py-3"
          style={{ paddingRight: '2.75rem', paddingLeft: smartMode ? '6.5rem' : '1rem' }}
        />
        <svg className="w-4 h-4 absolute right-4 top-1/2 -translate-y-1/2 text-gray-steel pointer-events-none"
          fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-4.35-4.35M17 10a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        {smartMode && (
          <button type="button" onClick={() => { setSmartInput(''); setSmartQuery('') }}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-xs px-3 py-1.5 rounded-lg bg-white/5 text-gray-steel hover:text-white transition-colors">
            ✕ حذف جستجو
          </button>
        )}
      </form>

      {/* سربرگ */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-2xl text-white">محصولات</h1>
          {smartMode
            ? smartData && (
              <p className="text-sm text-gray-steel mt-1">
                {smartData.count.toLocaleString('fa-IR')} نتیجه هوشمند برای «{smartQuery}»
              </p>
            )
            : data && (
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
          {(isLoading || smartLoading) ? (
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
              <Pagination page={page} totalPages={totalPages}
                onPage={(p) => { setPage(p); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
