// Service Worker — CCTV Parts Shop
// Cache-first for static assets — درخواست‌های API اصلاً کش نمی‌شوند
// (کش شدن پاسخ‌های شخصی مثل سبد خرید باعث می‌شد کاربر سبد پر را خالی ببیند)

const CACHE_NAME = 'cctv-parts-v78';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      // فقط وقتی کش نسخه قبلی وجود دارد یعنی این یک «آپدیت» است، نه اولین نصب
      const hadOldCache = keys.some((k) => k !== CACHE_NAME);
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      ).then(() => self.clients.claim()).then(() => hadOldCache);
    }).then((hadOldCache) => {
      // رفرش فقط در آپدیت واقعی — در اولین بازدید (بدون SW قبلی) رفرش یعنی
      // لود دوباره کامل صفحه برای کاربر تازه‌وارد و خزنده‌ها
      if (!hadOldCache) return;
      return self.clients.matchAll({ type: 'window' })
        .then((clients) => clients.forEach((c) => c.postMessage('SW_ACTIVATED')));
    })
  );
});

// صفحه از ما خواست نسخه تازه بدون معطلی فعال شود
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

// Fetch: cache-first for static, network-first for API
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // درخواست‌های دامنه‌های دیگر (مثل لوگوی ای‌نماد) را سرویس‌ورکر اصلاً دخالت ندهد —
  // وگرنه اگر شبکه خطا داد، respondWith با undefined رفع می‌شد و تصویر کلاً لود نمی‌شد
  if (url.origin !== self.location.origin) {
    return;
  }

  // HTML navigations: همیشه network-first تا نسخه تازه سایت دیده شود
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put('/index.html', clone);
          });
          return response;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  // API calls: فقط شبکه — پاسخ‌های API شخصی‌اند (سبد خرید، حساب کاربری، قیمت همکاری)
  // و کش کردن/فالبک کش‌شده آن‌ها داده کهنه نشان می‌داد
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // آیکون‌ها: network-first (بدون هش هستند و ممکن است عوض شوند)
  if (url.pathname.startsWith('/icons/')) {
    event.respondWith(
      fetch(request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, clone);
        });
        return response;
      }).catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: cache-first (فقط فایل‌های هش‌دار /assets/)
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, clone);
          });
          return response;
        });
      })
    );
    return;
  }

  // بقیه: network-first — اگر هم شبکه خطا داد و کش هم نداشت، پاسخ خطای واقعی برگردد
  event.respondWith(
    fetch(request).catch(() =>
      caches.match(request).then((cached) => cached || Response.error())
    )
  );
});
