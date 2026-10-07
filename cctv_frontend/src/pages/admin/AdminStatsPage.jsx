// ─── آمار سایت — داشبورد اشتراکی Umami (فقط سوپریوزر از منو می‌بیند) ───
// لینک اشتراکی فقط‌خواندنی است؛ داده روی سرور خودمان (‌/umami) میزبانی می‌شود
const SHARE_URL = '/umami/share/MgYNUG8ZOwoHynBn/doorbinkar'

export default function AdminStatsPage() {
  return (
    <div className="container-main py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-2xl text-white">آمار سایت</h1>
        <a href="/umami" target="_blank" rel="noreferrer" className="text-xs text-brand hover:text-brand/80">
          ورود به داشبورد کامل Umami ↗
        </a>
      </div>
      <div className="card overflow-hidden" style={{ height: 'calc(100vh - 200px)', minHeight: 480 }}>
        <iframe src={SHARE_URL} className="w-full h-full border-0" title="آمار سایت" />
      </div>
    </div>
  )
}
