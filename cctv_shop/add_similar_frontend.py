import os, shutil

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن import useQuery اگر نبود
if 'useQuery' not in content:
    content = content.replace(
        "import { ",
        "import { useQuery, "
    )

# اضافه کردن import api اگر نبود
if "import api from" not in content:
    content = content.replace(
        "import { Link",
        "import api from '../services/api'\nimport { Link"
    )

# اضافه کردن سکشن جایگزین‌ها قبل از بستن div اصلی
similar_section = """
      {/* جایگزین‌های پیشنهادی */}
      <SimilarProducts slug={product.slug} />

"""

# اضافه کردن قبل از آخرین </div>
old_end = """      {product.compatible_with?.length > 0 && ("""
new_end = similar_section + """      {product.compatible_with?.length > 0 && ("""

if old_end in content and 'SimilarProducts' not in content:
    content = content.replace(old_end, new_end)
    print("✓ سکشن جایگزین اضافه شد")

# اضافه کردن کامپوننت SimilarProducts در ابتدای فایل
similar_component = """
// ─── جایگزین‌های پیشنهادی ────────────────────────────────────
function SimilarProducts({ slug }) {
  const { data } = useQuery({
    queryKey: ['similar-products', slug],
    queryFn: () => api.get(`/catalog/products/${slug}/similar/`).then(r => r.data),
    staleTime: 60000,
  })

  if (!data?.similar?.length) return null

  return (
    <section className="mt-8">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="font-display font-bold text-xl text-white">
          {data.is_out_of_stock ? '🔄 جایگزین‌های پیشنهادی' : '📦 محصولات مشابه'}
        </h2>
        {data.is_out_of_stock && (
          <span className="text-xs bg-red-500/20 text-red-400 px-3 py-1 rounded-full">
            کالا ناموجود است
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4">
        {data.similar.map(p => (
          <Link key={p.id} to={`/products/${p.slug}`}
            className="card p-4 hover:border-brand/30 transition-all group">
            {p.image && (
              <img src={p.image} alt={p.name}
                className="w-full h-32 object-contain mb-3 rounded-lg bg-white/5" />
            )}
            <div className="text-sm font-semibold text-white group-hover:text-brand transition-colors truncate">
              {p.name}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                p.is_available ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {p.is_available ? `موجود (${p.stock} عدد)` : 'ناموجود'}
              </span>
              {p.category && (
                <span className="text-[10px] text-gray-steel">{p.category}</span>
              )}
            </div>
            {p.sensor_name && (
              <div className="text-[10px] text-gray-steel mt-1">سنسور: {p.sensor_name}</div>
            )}
          </Link>
        ))}
      </div>
    </section>
  )
}

"""

# اضافه کردن قبل از export default
if 'SimilarProducts' not in content:
    content = content.replace('export default function', similar_component + 'export default function')
    print("✓ کامپوننت SimilarProducts اضافه شد")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ ProductDetailPage.jsx آپدیت شد")
print("Lines:", content.count('\n'))
