import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'
import Seo from '../components/Seo'
import { mediaUrl as imgUrl } from '../utils/media'
import { formatDate } from '../utils/date'

export default function BlogPage() {
  const { categorySlug } = useParams()
  const [search, setSearch] = useState('')

  const { data: articles = [] } = useQuery({
    queryKey: ['articles', categorySlug],
    queryFn: () => api.get('/education/articles/', {
      params: categorySlug ? { category: categorySlug } : {}
    }).then(r => r.data),
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['article-categories'],
    queryFn: () => api.get('/education/categories/').then(r => r.data),
  })

  const filtered = articles.filter(a =>
    !search || a.title.includes(search) || a.description.includes(search)
  )

  return (
    <div className="container-main py-12">
      <Seo
        title="مقالات تخصصی | دوربینکار"
        description="راهنماها و مقالات تخصصی دوربین مداربسته — آموزش، مقایسه و نکات فنی."
        canonical="/blog/"
      />
      <div className="text-center mb-10">
        <h1 className="font-display font-bold text-3xl text-white mb-3">📚 مقالات تخصصی</h1>
        <p className="text-gray-steel">راهنماها و مقالات تخصصی دوربین مداربسته</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6 md:gap-8">
        {/* سایدبار */}
        <div className="w-full md:w-48 md:flex-shrink-0">
          <div className="card p-4 mb-4">
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="جستجو..." className="input text-sm w-full" />
          </div>
          <div className="card p-4">
            <h3 className="text-xs font-semibold text-white mb-3">دسته‌بندی‌ها</h3>
            <div className="flex gap-1 overflow-x-auto md:flex-col md:gap-0 md:space-y-1 md:overflow-visible">
              <Link to="/blog" className={`whitespace-nowrap block text-xs px-2 py-1.5 rounded ${!categorySlug ? 'text-brand bg-brand/10' : 'text-gray-steel hover:text-white'}`}>
                همه مقالات
              </Link>
              {categories.map(c => (
                <Link key={c.id} to={`/blog/category/${c.slug}`}
                  className={`whitespace-nowrap block text-xs px-2 py-1.5 rounded ${categorySlug === c.slug ? 'text-brand bg-brand/10' : 'text-gray-steel hover:text-white'}`}>
                  {c.name}
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* مقالات */}
        <div className="flex-1">
          {filtered.length === 0 ? (
            <div className="text-center py-20 text-gray-steel">مقاله‌ای یافت نشد</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {filtered.map(a => (
                <Link key={a.id} to={`/blog/${a.slug}`}
                  className="card p-5 hover:border-brand/30 transition-all group">
                  {a.thumbnail && (
                    <img src={imgUrl(a.thumbnail)} alt={a.title}
                      className="w-full aspect-video object-cover rounded-xl mb-4" />
                  )}
                  <div className="flex items-center gap-2 mb-2">
                    {a.category && (
                      <span className="text-[10px] bg-brand/20 text-brand px-2 py-0.5 rounded-full">
                        {a.category}
                      </span>
                    )}
                    <span className="text-[10px] text-gray-steel">{formatDate(a.created_at)}</span>
                  </div>
                  <h2 className="font-bold text-white text-sm mb-2 group-hover:text-brand transition-colors line-clamp-2">
                    {a.title}
                  </h2>
                  <p className="text-xs text-gray-steel line-clamp-3">{a.description}</p>
                  <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-steel">
                    <span>👁 {a.views_count}</span>
                    <span>❤️ {a.likes_count}</span>
                    {a.author && <span>✍️ {a.author}</span>}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
