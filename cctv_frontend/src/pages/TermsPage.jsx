import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { PageLoader } from '../components/ui'

export default function TermsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['static-page-terms'],
    queryFn: () => api.get('/core/pages/terms/').then(r => r.data),
    staleTime: 600000,
  })

  if (isLoading) return <PageLoader />

  return (
    <div className="container-main py-12 max-w-3xl">
      <h1 className="font-display font-bold text-3xl text-white mb-8">
        📋 {data?.title || 'قوانین و مقررات'}
      </h1>
      <div className="card p-8 text-sm text-gray-300 leading-loose"
        dangerouslySetInnerHTML={{ __html: data?.content || '' }} />
    </div>
  )
}
