import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── کامپوننت PackageCard ────────────────────────────────────
pkg_component = '''import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'

function fmt(n) { return Number(n || 0).toLocaleString('fa-IR') }

// ─── کارت پکیج ───────────────────────────────────────────────
function PackageCard({ pkg }) {
  return (
    <div className="card p-5 hover:border-brand/30 transition-all">
      {/* هدر */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-bold text-white text-sm">{pkg.name}</h3>
          {pkg.description && (
            <p className="text-xs text-gray-steel mt-1 line-clamp-2">{pkg.description}</p>
          )}
        </div>
        <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded-full font-bold flex-shrink-0 mr-2">
          {pkg.discount_percent}% تخفیف
        </span>
      </div>

      {/* محصولات */}
      <div className="space-y-2 mb-4">
        {pkg.items?.map((item, i) => (
          <div key={i} className="flex items-center gap-3 bg-white/5 rounded-lg p-2">
            {item.image && (
              <img src={item.image} alt={item.product_name}
                className="w-10 h-10 object-contain rounded bg-white/5 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="text-xs text-white truncate">{item.product_name}</div>
              <div className="text-[10px] text-gray-steel">× {item.quantity} عدد | {fmt(item.unit_price)} ت</div>
            </div>
          </div>
        ))}
      </div>

      {/* قیمت */}
      <div className="border-t border-white/5 pt-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-steel">قیمت اصلی:</span>
          <span className="text-xs text-gray-steel line-through">{fmt(pkg.original_price)} ت</span>
        </div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-green-400">صرفه‌جویی:</span>
          <span className="text-xs text-green-400 font-bold">{fmt(pkg.savings)} ت</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-bold text-white">قیمت پکیج:</span>
          <span className="text-lg font-bold text-brand">{fmt(pkg.final_price)} ت</span>
        </div>
      </div>

      <Link to={`/packages/${pkg.slug}`}
        className="btn-primary w-full text-center text-sm py-2.5 mt-4 block">
        مشاهده و خرید پکیج
      </Link>
    </div>
  )
}

// ─── سکشن پکیج‌های ویژه ─────────────────────────────────────
export function FeaturedPackages() {
  const { data: packages = [] } = useQuery({
    queryKey: ['featured-packages'],
    queryFn: () => api.get('/catalog/packages/?featured=1').then(r => r.data),
    staleTime: 300000,
  })

  if (!packages.length) return null

  return (
    <section className="py-12">
      <div className="container-main">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display font-bold text-2xl text-white">🎁 پکیج‌های پیشنهادی</h2>
            <p className="text-sm text-gray-steel mt-1">ترکیب بهترین قطعات با تخفیف ویژه</p>
          </div>
          <Link to="/packages" className="text-sm text-brand hover:text-brand/80">
            همه پکیج‌ها ←
          </Link>
        </div>
        <div className="grid grid-cols-3 gap-6">
          {packages.slice(0, 3).map(pkg => (
            <PackageCard key={pkg.id} pkg={pkg} />
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── پکیج‌های مرتبط با محصول ────────────────────────────────
export function ProductPackages({ productId }) {
  const { data: allPackages = [] } = useQuery({
    queryKey: ['all-packages'],
    queryFn: () => api.get('/catalog/packages/').then(r => r.data),
    staleTime: 300000,
  })

  // فیلتر پکیج‌هایی که این محصول را دارند
  const related = allPackages.filter(pkg =>
    pkg.items?.some(item => item.product_id === productId)
  )

  if (!related.length) return null

  return (
    <section className="mt-8">
      <h2 className="font-display font-bold text-xl text-white mb-4">🎁 پکیج‌های شامل این محصول</h2>
      <div className="grid grid-cols-2 gap-4">
        {related.map(pkg => (
          <PackageCard key={pkg.id} pkg={pkg} />
        ))}
      </div>
    </section>
  )
}

export default PackageCard
'''

# ذخیره کامپوننت
components_dir = os.path.join(FRONTEND, 'components')
os.makedirs(components_dir, exist_ok=True)
with open(os.path.join(components_dir, 'PackageComponents.jsx'), 'w', encoding='utf-8') as f:
    f.write(pkg_component)
print("✓ PackageComponents.jsx ساخته شد")

# ─── اضافه کردن به ProductDetailPage ────────────────────────
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')
with open(page_path, encoding='utf-8') as f:
    content = f.read()

if 'ProductPackages' not in content:
    # اضافه کردن import
    content = content.replace(
        "import { PageLoader",
        "import { ProductPackages } from '../components/PackageComponents'\nimport { PageLoader"
    )
    # اضافه کردن سکشن قبل از SimilarProducts
    content = content.replace(
        '      {/* جایگزین‌های پیشنهادی */}\n      <SimilarProducts slug={product.slug} />',
        '      {/* پکیج‌های مرتبط */}\n      <ProductPackages productId={product.id} />\n\n      {/* جایگزین‌های پیشنهادی */}\n      <SimilarProducts slug={product.slug} />'
    )
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ ProductPackages به ProductDetailPage اضافه شد")

# ─── ساخت PackagesPage ───────────────────────────────────────
packages_page = '''import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'
import PackageCard from '../components/PackageComponents'

export default function PackagesPage() {
  const { data: packages = [], isLoading } = useQuery({
    queryKey: ['all-packages'],
    queryFn: () => api.get('/catalog/packages/').then(r => r.data),
  })

  if (isLoading) return (
    <div className="container-main py-20 text-center text-gray-steel">در حال بارگذاری...</div>
  )

  return (
    <div className="container-main py-12">
      <div className="mb-8">
        <h1 className="font-display font-bold text-3xl text-white mb-2">🎁 پکیج‌های پیشنهادی</h1>
        <p className="text-gray-steel">ترکیب بهینه قطعات دوربین مداربسته با تخفیف ویژه</p>
      </div>

      {packages.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-4xl mb-4">📦</div>
          <div className="text-gray-steel">هنوز پکیجی تعریف نشده</div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-6">
          {packages.map(pkg => (
            <PackageCard key={pkg.id} pkg={pkg} />
          ))}
        </div>
      )}
    </div>
  )
}
'''

with open(os.path.join(FRONTEND, 'pages', 'PackagesPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(packages_page)
print("✓ PackagesPage.jsx ساخته شد")

# ─── آپدیت App.jsx ───────────────────────────────────────────
app_path = os.path.join(FRONTEND, 'App.jsx')
with open(app_path, encoding='utf-8') as f:
    app = f.read()

if 'PackagesPage' not in app:
    app = app.replace(
        "import ProductsPage",
        "import PackagesPage from './pages/PackagesPage'\nimport ProductsPage"
    )
    app = app.replace(
        '<Route path="products"',
        '<Route path="packages" element={<PackagesPage />} />\n        <Route path="products"'
    )
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(app)
    print("✓ App.jsx آپدیت شد")

print("\nآدرس‌های جدید:")
print("  /packages  — صفحه همه پکیج‌ها")
print("  پکیج‌ها در صفحه محصول هم نمایش داده می‌شوند")
