import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-white/5 bg-navy/50">
      <div className="container-main py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 bg-brand rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.889L15 14v-4zM3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/>
                </svg>
              </div>
              <span className="font-display font-bold text-white">فروشگاه قطعات دوربین</span>
            </div>
            <p className="text-sm text-gray-steel leading-relaxed">
              تأمین‌کننده تخصصی قطعات دوربین مداربسته — سنسور، لنز، برد، ISP و بیشتر
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-white mb-4">دسترسی سریع</h4>
            <ul className="space-y-2">
              {[
                ['محصولات', '/products'],
                ['ورود', '/auth/login'],
                ['ثبت‌نام همکار', '/auth/register'],
              ].map(([label, href]) => (
                <li key={href}>
                  <Link to={href} className="text-sm text-gray-steel hover:text-cyan transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-white mb-4">تماس با ما</h4>
            <ul className="space-y-2 text-sm text-gray-steel">
              <li>📞 ۰۲۱-XXXXXXXX</li>
              <li>📧 info@cctvparts.ir</li>
              <li>🕐 شنبه تا پنج‌شنبه، ۹–۱۸</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-white/5 flex items-center justify-between text-xs text-gray-steel">
          <span>© ۱۴۰۳ فروشگاه قطعات دوربین مداربسته — تمامی حقوق محفوظ است</span>
          <span className="font-mono text-brand">CCTV PARTS v1.0</span>
        </div>
      </div>
    </footer>
  )
}
