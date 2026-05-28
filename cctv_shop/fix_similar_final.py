import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

similar_component = '''
// ─── جایگزین‌های پیشنهادی ────────────────────────────────────
function SimilarProducts({ slug }) {
  const { data } = useQuery({
    queryKey: ['similar-products', slug],
    queryFn: () => fetch(`/api/catalog/products/${slug}/similar/`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
    }).then(r => r.json()),
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
            <div className="flex items-center gap-2 mt-2 flex-wrap">
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

'''

# اضافه کردن دقیقاً قبل از export default function
if 'function SimilarProducts' not in content:
    content = content.replace(
        'export default function ProductDetailPage',
        similar_component + 'export default function ProductDetailPage'
    )
    print("✓ SimilarProducts اضافه شد")
else:
    # حذف و اضافه مجدد در جای درست
    start = content.find('\n// ─── جایگزین')
    if start < 0:
        start = content.find('\nfunction SimilarProducts')
    export_idx = content.find('\nexport default function ProductDetailPage')
    
    if start > export_idx:
        # استخراج و جابجایی
        end = export_idx
        block = content[start:end]
        content = content[:start] + content[end:]
        content = content.replace(
            'export default function ProductDetailPage',
            block + '\nexport default function ProductDetailPage'
        )
        print("✓ SimilarProducts جابجا شد")
    else:
        print("✓ ترتیب درست است")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)

# تأیید
lines = content.split('\n')
for i, l in enumerate(lines, 1):
    if 'SimilarProducts' in l or 'export default' in l:
        print(f"line {i}: {l.strip()[:60]}")
