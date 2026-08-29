import { useQuery } from '@tanstack/react-query'
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {packages.map(pkg => (
            <PackageCard key={pkg.id} pkg={pkg} />
          ))}
        </div>
      )}
    </div>
  )
}
