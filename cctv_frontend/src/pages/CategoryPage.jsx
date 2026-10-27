import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../services/catalog'
import ProductCard from '../components/product/ProductCard'
import { PageLoader, EmptyState, ErrorMessage } from '../components/ui'
import Seo, { absoluteUrl } from '../components/Seo'
import { ArrowLeft, ChevronLeft } from 'lucide-react'

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

export default function CategoryPage() {
  const { slug } = useParams()
  const [page, setPage] = useState(1)

  const {
    data: category,
    isLoading: catLoading,
    isError: catError,
    refetch: refetchCat,
  } = useQuery({
    queryKey: ['category', slug],
    queryFn: () => catalogService.getCategory(slug),
  })

  const {
    data: productsData,
    isLoading: prodLoading,
    isError: prodError,
    refetch: refetchProd,
  } = useQuery({
    queryKey: ['category-products', slug, page],
    queryFn: () => catalogService.getCategoryProducts(slug, { page }),
    keepPreviousData: true,
  })

  if (catLoading) return <PageLoader />
  if (catError) return <ErrorMessage message="خطا در بارگذاری دسته‌بندی" retry={refetchCat} />
  if (!category) return <EmptyState icon="📂" title="دسته‌بندی یافت نشد" />

  const products = productsData?.results || []
  const totalPages = productsData ? Math.ceil(productsData.count / 24) : 0

  // ─── SEO/GEO ─────────────────────────────────────────────────
  const canonical = `/categories/${category.slug}/`
  const breadcrumbLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'خانه', item: absoluteUrl('/') },
      { '@type': 'ListItem', position: 2, name: 'محصولات', item: absoluteUrl('/products') },
      { '@type': 'ListItem', position: 3, name: category.name, item: absoluteUrl(canonical) },
    ],
  }

  return (
    <div className="container-main py-8">
      <Seo
        title={category.meta_title || `${category.name} | دوربینکار`}
        description={category.meta_description || category.description}
        canonical={canonical}
        image={category.image}
        jsonLd={breadcrumbLd}
      />
      {/* بردکرامب */}
      <div className="flex items-center gap-2 text-sm text-gray-steel mb-4">
        <Link to="/" className="hover:text-brand transition-colors">خانه</Link>
        <ChevronLeft size={14} />
        <Link to="/products" className="hover:text-brand transition-colors">محصولات</Link>
        <ChevronLeft size={14} />
        <span className="text-white">{category.name}</span>
      </div>

      {/* هدر دسته */}
      <div className="mb-8">
        <h1 className="font-display font-bold text-2xl text-white mb-3">{category.name}</h1>
        {category.description ? (
          <p className="text-gray-steel leading-relaxed max-w-3xl">{category.description}</p>
        ) : (
          <p className="text-gray-steel text-sm">کاتالوگ محصولات {category.name}</p>
        )}
      </div>

      {/* زیردسته‌ها */}
      {category.children && category.children.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-bold text-white mb-3">زیردسته‌ها</h2>
          <div className="flex flex-wrap gap-2">
            {category.children.map((child) => (
              <Link
                key={child.slug}
                to={`/categories/${child.slug}`}
                className="px-4 py-2 rounded-xl border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:text-gold hover:border-[rgba(251,192,45,0.4)] hover:bg-[var(--color-brand-softer)] transition-colors"
              >
                {child.name}
                {child.product_count > 0 && (
                  <span className="mr-1.5 text-xs text-gray-steel">({Number(child.product_count).toLocaleString('fa-IR')})</span>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* لیست محصولات */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white">محصولات</h2>
          {productsData && (
            <span className="text-sm text-gray-steel">
              {productsData.count.toLocaleString('fa-IR')} محصول
            </span>
          )}
        </div>

        {prodLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Array(8).fill(0).map((_, i) => <div key={i} className="skeleton h-72 rounded-2xl" />)}
          </div>
        ) : prodError ? (
          <ErrorMessage message="خطا در بارگذاری محصولات" retry={refetchProd} />
        ) : products.length === 0 ? (
          <EmptyState
            icon="📂"
            title="محصولی در این دسته یافت نشد"
            description="در حال حاضر هیچ محصولی در این دسته ثبت نشده است."
            action={
              <Link to="/products" className="btn-secondary inline-flex items-center gap-2">
                <ArrowLeft size={14} /> همه محصولات
              </Link>
            }
          />
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {products.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
            <Pagination page={page} totalPages={totalPages} onPage={setPage} />
          </>
        )}
      </div>
    </div>
  )
}
