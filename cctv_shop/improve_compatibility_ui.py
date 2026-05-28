import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
page_path = os.path.join(FRONTEND, 'pages', 'ProductDetailPage.jsx')

with open(page_path, encoding='utf-8') as f:
    content = f.read()

# بهبود سکشن compatible_with
old = """      {product.compatible_with?.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display font-bold text-xl text-white mb-4">محصولات سازگار</h2>
          <div className="flex flex-wrap gap-2">
            {product.compatible_with.map(p => (
              <Link key={p.id} to={`/products/${p.slug}`}
                className="px-4 py-2 rounded-xl border border-brand/20 bg-brand/5
                  text-brand dark:text-cyan text-sm hover:bg-brand/10 transition-colors">
                {p.name}
              </Link>
            ))}
          </div>
        </section>
      )}"""

new = """      {product.compatible_with?.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display font-bold text-xl text-white mb-4">🔗 قطعات سازگار</h2>
          <div className="grid grid-cols-2 gap-3">
            {product.compatible_with.map(p => (
              <Link key={p.id} to={`/products/${p.slug}`}
                className="card p-4 flex items-center gap-3 hover:border-brand/30 transition-all group">
                {p.image && (
                  <img src={p.image} alt={p.name}
                    className="w-14 h-14 object-contain rounded-lg bg-white/5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-white group-hover:text-brand transition-colors truncate">
                    {p.name}
                  </div>
                  {p.category_name && (
                    <div className="text-xs text-gray-steel mt-0.5">{p.category_name}</div>
                  )}
                  <div className="text-xs text-cyan mt-1">مشاهده محصول ←</div>
                </div>
              </Link>
            ))}
          </div>
          <p className="text-xs text-gray-steel mt-3">
            این قطعات با یکدیگر سازگار هستند و می‌توانند در کنار هم استفاده شوند.
          </p>
        </section>
      )}"""

if old in content:
    content = content.replace(old, new)
    print("✓ سکشن سازگاری بهبود یافت")
else:
    print("✗ متن پیدا نشد")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
