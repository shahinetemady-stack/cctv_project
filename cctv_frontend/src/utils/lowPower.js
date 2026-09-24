// تشخیص دستگاه کم‌توان — روی این دستگاه‌ها انیمیشن‌های زنده (WebGL/کنواس)
// اجرا نمی‌شوند تا main-thread برای رندر و تعامل آزاد بماند:
//   prefers-reduced-motion یا تک‌هسته‌ای یا دوهسته‌ایِ موبایل
// نکته ۱: آستانه هسته پایین است — Safari روی iOS مقدار hardwareConcurrency را
// برای جلوگیری از fingerprinting همیشه روی ۴ قفل می‌کند (از آیفون ۱۱ به بعد)،
// پس آستانه ۴ همه آیفون‌ها را اشتباهی «کم‌توان» تشخیص می‌داد.
// نکته ۲: دسکتاپ‌های دوهسته‌ای قدیمی (مثل Win7 با کروم ۱۰۹) اگر GPU سالم داشته
// باشند از عهده این افکت‌ها برمی‌آیند (لوپ‌ها fps-cap و res پایین دارند و وقتی
// صفحه دیده نمی‌شود متوقف می‌شوند) — پس فقط دوهسته‌ایِ صفحه‌کوچک استاتیک می‌شود.
// نکته ۳: deviceMemory عمداً حذف شده — کروم اندروید آن را به توان‌های دو گرد و
// در ۸ سقف می‌زند، پس گوشی‌های ۶/۸GB هم «۴» گزارش می‌دهند و اشتباهی استاتیک
// می‌شدند.
export function isLowPower() {
  if (typeof window === 'undefined') return true
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return true
  const cores = navigator.hardwareConcurrency || 4
  if (cores <= 1) return true
  if (cores <= 2 && window.matchMedia('(max-width: 768px)').matches) return true
  return false
}
