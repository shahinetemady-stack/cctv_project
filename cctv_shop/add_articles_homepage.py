import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')
home_path = os.path.join(FRONTEND, 'pages', 'HomePage.jsx')

with open(home_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن import
if 'useQuery' not in content:
    content = content.replace(
        "import { Link }",
        "import { useQuery } from '@tanstack/react-query'\nimport api from '../services/api'\nimport { Link }"
    )
elif 'api' not in content:
    content = content.replace(
        "import { useQuery }",
        "import { useQuery } from '@tanstack/react-query'\nimport api from '../services/api'\n"
    )

# اضافه کردن کامپوننت FeaturedArticles قبل از export default
featured_articles = """
// ─── مقالات برتر ─────────────────────────────────────────────
function FeaturedArticles() {
  const { data: articles = [] } = useQuery({
    queryKey: ['featured-articles'],
    queryFn: () => api.get('/education/articles/').then(r => r.data),
    staleTime: 300000,
  })

  if (!articles.length) return null

  function imgUrl(url) {
    if (!url) return null
    if (url.startsWith('http')) return url
    return `http://localhost:8000${url}`
  }

  return (
    <section className="py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">📚 مقالات تخصصی</h2>
          <p className="text-sm text-gray-steel mt-1">راهنماها و آموزش‌های دوربین مداربسته</p>
        </div>
        <Link to="/blog" className="text-sm text-brand hover:text-brand/80 flex items-center gap-1">
          همه مقالات ←
        </Link>
      </div>
      <div className="grid grid-cols-3 gap-5">
        {articles.slice(0, 3).map(a => (
          <Link key={a.id} to={`/blog/${a.slug}`}
            className="card hover:border-brand/30 transition-all group overflow-hidden">
            {a.thumbnail ? (
              <img src={imgUrl(a.thumbnail)} alt={a.title}
                className="w-full h-36 object-cover" />
            ) : (
              <div className="w-full h-36 bg-gradient-to-br from-brand/20 to-navy flex items-center justify-center">
                <span className="text-4xl">📄</span>
              </div>
            )}
            <div className="p-4">
              {a.category && (
                <span className="text-[10px] bg-brand/20 text-brand px-2 py-0.5 rounded-full">
                  {a.category}
                </span>
              )}
              <h3 className="font-semibold text-white text-sm mt-2 mb-1 group-hover:text-brand transition-colors line-clamp-2">
                {a.title}
              </h3>
              <p className="text-xs text-gray-steel line-clamp-2">{a.description}</p>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-steel">
                <span>👁 {a.views_count}</span>
                <span>{a.created_at}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}

"""

if 'FeaturedArticles' not in content:
    content = content.replace(
        'export default function HomePage',
        featured_articles + 'export default function HomePage'
    )
    print("✓ FeaturedArticles کامپوننت اضافه شد")

# اضافه کردن به JSX قبل از بنر سفارش از چین
if '<FeaturedArticles' not in content:
    content = content.replace(
        '        {/* بنر سفارش از چین */}',
        '        <FeaturedArticles />\n\n        {/* بنر سفارش از چین */}'
    )
    print("✓ FeaturedArticles به HomePage اضافه شد")

with open(home_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
