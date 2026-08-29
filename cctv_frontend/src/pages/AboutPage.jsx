import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { PageLoader } from '../components/ui'

export default function AboutPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['static-page-about'],
    queryFn: () => api.get('/core/pages/about/').then(r => r.data),
    staleTime: 600000,
  })

  if (isLoading) return <PageLoader />

  const images = data?.images || []

  return (
    <div className="container-main py-12 max-w-3xl">
      <h1 className="font-display font-bold text-3xl text-white mb-8">
        ℹ️ {data?.title || 'درباره ما'}
      </h1>
      <div className="card p-8 text-sm text-gray-300 leading-loose">
        <div dangerouslySetInnerHTML={{ __html: data?.content || '' }} />
        <div className="grid grid-cols-2 gap-3 my-6">
          {[0, 1, 2, 3].map(i => (
            images[i]
              ? <img key={i} src={images[i]} alt={`تصویر ${i + 1}`}
                  className="w-full rounded-xl aspect-[4/3] object-cover" />
              : <div key={i}
                  className="w-full rounded-xl aspect-[4/3] bg-slate-800 border border-dashed border-slate-600 flex items-center justify-center text-slate-500 text-xs">
                  تصویر {i + 1}
                </div>
          ))}
        </div>
      </div>
    </div>
  )
}
