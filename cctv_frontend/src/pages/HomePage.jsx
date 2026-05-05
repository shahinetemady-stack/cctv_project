import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogService } from '../services/catalog'
import ProductCard from '../components/product/ProductCard'

function Hero() {
  return (
    <section className="relative overflow-hidden py-24 md:py-32">
      <div className="absolute inset-0 bg-hero-glow" />
      <div className="absolute inset-0 bg-grid-pattern bg-grid opacity-40" />
      <div className="container-main relative text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-brand/30 bg-brand/10 text-cyan text-xs font-mono">
          <span className="w-1.5 h-1.5 bg-cyan rounded-full" />
          تأمین‌کننده تخصصی قطعات دوربین مداربسته
        </div>
        <h1 className="font-display font-extrabold text-4xl md:text-6xl text-white leading-tight mb-6">
          قطعات دوربین
          <span className="block text-transparent bg-clip-text bg-gradient-to-l from-cyan to-brand">
            با کیفیت اصل
          </span>
        </h1>
        <p className="text-gray-steel text-lg max-w-xl mx-auto mb-10">
          سنسور، لنز، برد، ISP و تمام قطعات موردنیاز دوربین مداربسته
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link to="/products" className="btn-primary px-8 py-3 text-base">مشاهده محصولات</Link>
          <Link to="/auth/register" className="btn-secondary px-8 py-3 text-base">عضویت همکار</Link>
        </div>
      </div>
    </section>
  )
}

const CATEGORY_ICONS = {
  'سنسور':'📷','لنز':'🔭','برد':'🔌','ISP':'💻',
  'کیس':'📦','IR-Cut':'🔴','موتور':'⚙️','سایر':'🔧',
}

function Categories() {
  const { data, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: catalogService.getCategories,
  })
  if (isLoading) return null
  const categories = Array.isArray(data) ? data : (data?.results || [])
  if (categories.length === 0) return null
  return (
    <div className="grid grid-cols-4 md:grid-cols-8 gap-3">
      {categories.map(cat => (
        <Link key={cat.id} to={`/products?category=${cat.id}`}
          className="card card-hover flex flex-col items-center justify-center gap-2 p-4 text-center group">
          <span className="text-2xl group-hover:scale-110 transition-transform">
            {CATEGORY_ICONS[cat.name] || '📦'}
          </span>
          <span className="text-xs text-gray-700 dark:text-gray-300 leading-tight">{cat.name}</span>
        </Link>
      ))}
    </div>
  )
}

function LatestProducts() {
  const { data, isLoading } = useQuery({
    queryKey: ['products', 'latest'],
    queryFn: () => catalogService.getProducts({ ordering: '-created_at', page_size: 8 }),
  })
  if (isLoading) return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {Array(8).fill(0).map((_, i) => <div key={i} className="skeleton h-72 rounded-2xl" />)}
    </div>
  )
  const products = Array.isArray(data) ? data : (data?.results || [])
  if (products.length === 0) return (
    <div className="text-center py-12 text-gray-steel">
      <div className="text-4xl mb-3">📦</div>
      <p>هنوز محصولی اضافه نشده</p>
      <a href="/admin/catalog/product/add/" className="text-brand text-sm mt-2 inline-block">
        + اضافه کردن محصول از پنل ادمین
      </a>
    </div>
  )
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {products.map(p => <ProductCard key={p.id} product={p} />)}
    </div>
  )
}

export default function HomePage() {
  return (
    <div>
      <Hero />
      <div className="container-main space-y-16 pb-16">
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-display font-bold text-xl text-white">دسته‌بندی‌ها</h2>
          </div>
          <Categories />
        </section>
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-display font-bold text-xl text-white">آخرین محصولات</h2>
            <Link to="/products" className="text-sm text-brand hover:text-cyan transition-colors">مشاهده همه ←</Link>
          </div>
          <LatestProducts />
        </section>
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-brand to-steel p-10 text-center">
          <div className="relative">
            <div className="text-4xl mb-4">🤝</div>
            <h3 className="font-display font-bold text-2xl text-white mb-3">عضویت ویژه همکاران</h3>
            <p className="text-blue-100 mb-6 max-w-md mx-auto text-sm">
              به عنوان همکار ثبت‌نام کنید و از قیمت‌های اختصاصی بهره‌مند شوید
            </p>
            <Link to="/auth/register" className="inline-flex items-center gap-2 px-8 py-3 bg-white text-brand font-bold rounded-xl hover:bg-blue-50 transition-colors shadow-lg">
              ثبت‌نام همکار
            </Link>
          </div>
        </section>
      </div>
    </div>
  )
}