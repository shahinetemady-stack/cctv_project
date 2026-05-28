import os

FRONTEND = os.path.join('..', 'cctv_frontend', 'src')

# ─── TermsPage ────────────────────────────────────────────────
terms = '''import { useQuery } from '@tanstack/react-query'
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
'''

# ─── PrivacyPage ─────────────────────────────────────────────
privacy = '''import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { PageLoader } from '../components/ui'

export default function PrivacyPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['static-page-privacy'],
    queryFn: () => api.get('/core/pages/privacy/').then(r => r.data),
    staleTime: 600000,
  })

  if (isLoading) return <PageLoader />

  return (
    <div className="container-main py-12 max-w-3xl">
      <h1 className="font-display font-bold text-3xl text-white mb-8">
        🔒 {data?.title || 'حریم خصوصی'}
      </h1>
      <div className="card p-8 text-sm text-gray-300 leading-loose"
        dangerouslySetInnerHTML={{ __html: data?.content || '' }} />
    </div>
  )
}
'''

with open(os.path.join(FRONTEND, 'pages', 'TermsPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(terms)
with open(os.path.join(FRONTEND, 'pages', 'PrivacyPage.jsx'), 'w', encoding='utf-8') as f:
    f.write(privacy)

print("✓ TermsPage و PrivacyPage آپدیت شدند")
print("\nبرای ویرایش متن صفحات:")
print("http://127.0.0.1:8000/admin/core/staticpage/")
print("\nصفحات:")
print("  /terms — قوانین")
print("  /privacy — حریم خصوصی")
