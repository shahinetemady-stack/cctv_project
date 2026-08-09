# نقطه ادامه کار — ۹ آگوست ۲۰۲۶

## سئوی هوم‌پیج (دور موتور جستجو + خزنده‌های AI)
- **H1 کلیدی** شد: «قطعات دوربین مداربسته‌ات رو پیدا کن، یا از ربات مشاور بپرس»؛ متا دیسکریپشن هم ربات مشاور/جستجوی هوشمند را به‌عنوان نقطه برتری ذکر می‌کند.
- **fallbackهای جعلی حذف شدند**: سکشن‌های پکیج/مقاله/ویدیو در HomePage فقط با داده واقعی API رندر می‌شوند (قبلاً محتوای ساختگی با قیمت/لینک شکسته نمایش و ایندکس می‌شد). محصولات هوم به ۸ کارت محدود شد.
- **سکشن متن معرفی** («دوربینکار؛ مرجع تخصصی قطعات دوربین مداربسته در ایران») بعد از دسته‌بندی‌ها — متن قابل‌خزش کلیدی‌دار با تاکید بر جستجوی هوشمند و ربات مشاور + لینک‌های داخلی.
- **سکشن سوالات متداول در هوم**: از `GET /api/assistant/faqs/`، آکاردئون `details/summary` (محتوا در DOM = قابل‌خزش)، تا ۵ مورد + لینک `/china-order/faq`؛ اسکیمای `FAQPage` پویا وقتی FAQ هست.
- **index.html استاتیک برای خزنده‌های بدون JS** (GPTBot/ClaudeBot/… JS اجرا نمی‌کنند): title/description نهایی + OG کامل + canonical + سه JSON-LD استاتیک (Organization با تلفن‌ها، WebSite با `SearchAction` روی `/products?search=`، Store). اسکیمای Org/WebSite از HomePage به همین‌جا منتقل شد تا تکراری نشود. viewport بدون `user-scalable=no` (دسترسی‌پذیری).
- **سایت‌مپ**: `VideoSitemap` (`/videos/<slug>`، منتشرشده‌ها) + صفحه `/china-order/faq` به صفحات ثابت.
- **مانده (نیازمند تصمیم)**: prerender/SSR — مهم‌ترین قدم برای دیده‌شدن توسط AIها؛ sameAs شبکه‌های اجتماعی وقتی هندل‌ها معلوم شد؛ ثبت در Search Console.

# نقطه ادامه کار — ۷ آگوست ۲۰۲۶

## صفحه سوالات متداول + اتصال FAQ به چت‌بات
- مدل `FAQ` (پرسش/پاسخ/کلیدواژه‌ها/ترتیب) در `apps/assistant` از قبل بود ولی مایگریشن نداشت و هیچ‌جا استفاده نمی‌شد — `assistant/0001_initial` ساخته و روی لوکال و سرور migrate شد. مدیریت محتوا: پنل جنگو ← «پرسش‌های متداول (آموزش ربات)».
- **API عمومی**: `GET /api/assistant/faqs/` (فقط فعال‌ها، به ترتیب).
- **صفحه فرانت**: `src/pages/FAQPage.jsx` (آکاردئون، useQuery) روی روت `/china-order/faq` — لینک منو قبلاً به این مسیر می‌رفت و ۴۰۴ بود.
- **تزریق به AI**: `_find_faqs` (اسکور کلمات سؤال در question+keywords، سقف ۲ مورد) + `_faq_context` — هم به چت‌بات (`AssistantChatView`) هم به `AssistantAskView` (باکس سرچ) اضافه شد؛ پرامپت می‌گوید اگر پاسخ آماده مرتبط بود همان را بگو. تست زنده: «هزینه ارسال چقدره؟» → پاسخ از FAQ. یک ردیف نمونه (هزینه ارسال) روی سرور ساخته شد.

## فیکس چت‌بات دستیار هوشمند (سرور)
- **علت «نتوانستم پاسخ بدهم»**: تایم‌اوت، نه خرابی Ollama — تولید پاسخ روی CPU ۳۰–۱۲۰ثانیه طول می‌کشد ولی gunicorn با `--timeout 60` ورکر را می‌کشت (لاگ: `WORKER TIMEOUT`) و nginx هم `proxy_read_timeout` نداشت. فیکس سرور: `--timeout 150` در `/etc/systemd/system/cctv-backend.service` + `proxy_read_timeout 150s` در بلاک `location /api/` در `/etc/nginx/sites-enabled/cctv`.
- **بازنویسی جستجوی RAG چت‌بات** (`apps/assistant/views.py` → `_find_products`): نرمال‌سازی ارقام فارسی/عربی، تطابق عبارت «N مگاپیکسل» در هر سه شکل نام محصول («پنج مگاپیکسل»/«5 مگاپیکسل»/«5مگاپیکسل»)، استاپ‌وردها (چی/پیشنهاد/قیمت/…)، امتیازدهی به‌جای OR خالی (تعداد کلمات تطابق + ۳ برای مگاپیکسل دقیق + ۰٫۵ موجودی) و فیلتر امتیاز صفر. خروجی تاپل `(products, is_fallback)` شد — در fallback کانتکست به مدل می‌گوید این‌ها پیشنهاد کلی‌اند نه جواب درخواست.
- **کانتکست تمیزتر**: موجودی در همان خط محصول (قبلاً لیست جدا بدون نام بود)؛ پرامپت: فقط محصولات لیست، موجودی صادقانه، اگر دقیقاً همان مشخصات نبود بگو.
- **سرعت**: `num_predict` ۳۵۰→۲۲۰ + `keep_alive: 30m` (درخواست سرد ~۶۰ثانیه، گرم ~۴۰ثانیه). سقف سرعت = CPU سرور با qwen2.5:3b؛ برای سریع‌تر: مدل کوچک‌تر (qwen2.5:1.5b) یا CPU قوی‌تر.
- **یافته مهم دیتا**: انبار سرور کاملاً خالی است (۰ حرکت انبار، هر ۸۰ محصول `available_stock=0`) — به همین دلیل همه محصولات «ناموجود» نمایش داده می‌شوند (در چت و سایت).
- **مرحله ۲ — کانتکست غنی (RAG)**: `_spec_summary` خلاصه مشخصات فنی هر محصول (سیستم/رزولوشن/سنسور/پردازنده/ابعاد برد، لنز/فاصله کانونی/نوع/کاربرد، بدنه/جنس/میکروفون، مودم/سیم‌کارت + ۱۴۰ کاراکتر short_description) به خط کانتکست هر محصول اضافه شد؛ جستجو حالا `short_description` و `keywords` را هم پوشش می‌دهد (مثلاً «پارکینگ» برد LPR را پیدا می‌کند)؛ پرامپت قاعده مشاوره بر اساس مشخصات گرفت (فاصله کانونی/استارلایت). نتیجه: جواب‌های مشاوره‌ای grounded شدند. سقف کیفیت = مدل 3b (فارسی ضعیف) — مرحله بعد در صورت نارضایتی: API آنلاین (زیرساخت AI_API_* در settings آماده است).
- **مرحله ۳ — فیکس تایم‌اوت مجدد**: کانتکست غنی پرامپت را آن‌قدر حجیم کرد که نسل پاسخ از TIMEOUT=120 بک‌اند گذشت (Read timeout روی Ollama). فیکس: limit محصولات ۶→۴ (فرانت anyway فقط ۴ کارت نشان می‌دهد)، short_description در کانتکست ۱۴۰→۱۰۰ کاراکتر، `num_predict` ۲۲۰→۱۷۰، TIMEOUT ۱۲۰→۱۴۰ (زیر nginx/gunicorn 150). alias اصطلاحات فارسی اضافه شد («ای اچ دی»→AHD، «آی پی»→IP، «پی او ای»→POE) + شکل چسبیده «دومگاپیکسل» در mp_variants. تست زنده «برد ای اچ دی ۲ مگاپیکسل»: پاسخ در ۴۸ ثانیه با V21X در صدر.

## فیکس سرچ هوشمند (`ProductSearchView` در catalog/views)
- علت «برد دو مگاپیکسل چی داری نتیجه نمی‌داد»: مچ AND روی **همه** توکن‌ها و نبود استاپ‌ورد — توکن‌های «چی»/«داری» هیچ محصولی را مچ نمی‌کردند و نتیجه صفر می‌شد. `STOPWORDS` محاوره‌ای (چی/داری/پیشنهاد/قیمت/…) اضافه شد.
- علت شکست فرم حروفی «دو»: alias آن فرم خام {دو, 2, ۲} بود و «دو» داخل «دوربین» هم هست → همه محصولات مچ می‌شدند. حالا عدد حروفی هم به فرم‌های رزولوشنی `_mp_alias` نگاشت می‌شود (مثل رقم).
- alias چندکلمه‌ای قبل از توکن‌بندی: `PHRASE_ALIASES` («ای اچ دی»→AHD، «آی پی»→IP، «پی او ای»→POE) + گروه مترادف {ahd, آنالوگ}. تست زنده سرور: هر دو فرم «دو»/«۲» → ۱۲ نتیجه با V21X در صدر.
- **علائم نگارشی**: «؟» به توکن آخر می‌چسبید («داری؟» ≠ استاپ‌ورد «داری») و لینک «مشاهده همه نتایج» را صفر می‌کرد — در `_normalize` علائم به فاصله تبدیل می‌شوند (همین فیکس در assistant `_find_products` هم اعمال شد).

## فیکس پاسخ AI در باکس سرچ + چت‌بات (ادامه)
- **«رد بدن D21»**: `AssistantAskView` (پاسخ AI باکس سرچ هوم‌پیج) کانتکستش فقط خلاصه کلی کاتالوگ بود → مدل مدل غیرموجود می‌ساخت. حالا همان RAG چت‌بات (`_find_products`+`_spec_summary` از apps.assistant) به آن داده می‌شود + قاعده «از خودت مدل نساز» در پرامپت. نکته: `.env` سرور `AI_API_BASE=http://127.0.0.1:11434/v1` و `AI_API_MODEL=qwen2.5:3b` است (endpoint سازگار با OpenAIِ Ollama) — AI_API_KEY فقط برای فعال‌سازی مسیر AI لازم است، Ollama کلید را نادیده می‌گیرد.
- **چت‌بات، فرم حروفی «دو مگاپیکسل»**: در `_find_products` قبل از regex رقمی، اعداد حروفی به رقم تبدیل می‌شوند + pool-cut فیکس شد (تطابق دقیق مگاپیکسل حتماً وارد pool اسکورینگ می‌شود — قبلاً با limit*6 از ترتیب خام DB، بردهای 2MP بیرون می‌ماندند). تست زنده: «برد دو مگاپیکسل چی داری؟» → ۴ برد 2MP واقعی (V21X/IMX307/IMX290/F38).

# نقطه ادامه کار — ۲ آگوست ۲۰۲۶ (بخش دوم)

## مدیریت کامل پکیج‌ها (/admin/packages — منو زیر «مدیریت محصولات»، perm: products_edit)
- بک‌اند: فیلدهای SEO/GEO به `Package` (مایگریشن `catalog/0026`) + endpointهای CRUD: `GET|POST /api/catalog/packages/admin/`، `GET|PATCH|DELETE .../admin/<pk>/` (items به‌صورت `[{variant_id, quantity}]` جایگزینی اتمیک می‌شوند)، آپلود/حذف تصویر `.../admin/<pk>/image/`. slug خودکار از نام.
- فرانت: صفحه جدید با کارت پکیج (قیمت اصلی/نهایی/سود) + مودال ساخت/ویرایش: جستجوی محصول debounce (با انتخاب واریانت و تعداد)، پیش‌نمایش زنده قیمت، آپلود تصویر، بخش SEO/GEO با شمارنده کاراکتر (CharCount به `components/ui/` منتقل شد). صفحه عمومی PackageDetailPage حالا Seo با متافیلدها دارد.

## سرچ هوشمند دوزبانه (فارسی + English)
- **ناوبری صفحه محصول**: endpoint `GET /catalog/products/<slug>/neighbors/` (ترتیب همان لیست: -is_featured, -created_at) + ردیف بالای صفحه محصول: دکمه «→ محصولات» (بازگشت با navigate(-1)) + «قبلی/بعدی» برای مرور محصول‌ها بدون برگشت به لیست.
- `ProductSearchView` بازنویسی شد: توکن‌بندی کوئری + مچ AND روی همه توکن‌ها (هر توکن با یکی از مترادف‌ها در هر فیلد) به‌جای icontains تک‌رشته‌ای. گروه‌های مترادف دوزبانه (لنز/lens، برد/board/pcb/module، هولدر/holder، سنسور/sensor، دام/dome، بولت/bullet، استارلایت/starlight، دوربین/camera/cctv، سونی/sony، کیس/housing، میکروفون/mic، مودم/router، پلاک/lpr) + رزولوشن (5mp ⇔ «۵ مگاپیکسل» ⇔ «پنج مگاپیکسل» با نگاشت کلمات اعداد فارسی) + نرمال‌سازی ارقام فارسی/عربی و ك/ي. فیلدهای جستجو: name/brand/model/board_name/sensor/lens/ai_processor/keywords/category/sku.
- فرانت SmartSearch: تحلیل ورودی انگلیسی (lens/board/sensor/sony/vatilon/fullhan...)، کوئری خام به بک‌اند، placeholder دوزبانه، چیپ‌های انگلیسی.
- **نوار جستجوی هوشمند بالای صفحه محصولات** (`ProductsPage.jsx`): ورودی + دکمه «✕ حذف جستجو» — موقع فعال بودن، گرید از endpoint هوشمند (`/products/search/?q=`) پر می‌شود و صفحه‌بندی مخفی است. پارامتر `?search=` در URL هم حالا به جستجوی هوشمند می‌رود (نه فیلتر ساده) — جریان SmartSearch هوم‌پیج → صفحه محصولات یکدست شد. بخش سرچ قدیمی FilterPanel (غیرهوشمند) حذف شد.
- `NormalizingSearchFilter` در catalog/views: endpoint لیست محصولات هم ارقام فارسی/عربی را نرمال می‌کند («۸۰۰» = «800»).

## دیتاشیت PDF به‌صورت تصویر در صفحه محصول

## دیتاشیت PDF به‌صورت تصویر در صفحه محصول
- مدل `DatasheetPage` (مایگریشن `catalog/0025`) + `apps/catalog/datasheet.py`: هنگام آپلود PDF (multipart PATCH) با `pdftoppm -jpeg -r 110` (حداکثر ۲۰ صفحه) صفحات به تصویر تبدیل می‌شوند — poppler 26 فلگ `-webp` ندارد، JPEG q85. پاک کردن PDF = حذف ردیف‌ها و فایل‌ها. خطای تبدیل هرگز آپلود را نمی‌شکند.
- `datasheet_pages` در ProductDetailSerializer (عمومی) و ProductAdminSerializer. صفحه محصول: بخش «دیتاشیت فنی» با دکمه دانلود PDF + تصاویر صفحات (lazy).
- **فیکس باگ آپلود**: اینترسپتور `api.js` هدر `Content-Type: application/json` سراسری را برای FormData حذف می‌کند — خطای «دیتای ارسال شده فایل نیست» برای همه آپلودها رفع شد.

## پروژه محتوای ۸۰ محصول (مرجع CCTV ایران)
- هر ۸۰ محصول با تحقیق از سایت کارخانه‌ها (Vatilon/hsell.com, Ruision, cwlens.cn, fullhan.com, sony-semicon, anjvision.com, ytot.com) بازنویسی شد: توضیح ۳–۵ پاراگرافی انسانی برای مخاطب مونتاژکار/تعمیرکار + short/meta/keywords + فیلدهای مشخصات با داده تأییدشده (تأییدنشده = خالی).
- سری H = Vatilon/HS؛ سری MC = Anjvision (نه Vatilon)؛ 800S/800G = سنسور Sony IMX415 + SSC338Q (نه IMX800)؛ چند چیپ اصلاح شد (id17 FH8536H، id18 FH8537H).
- مغایرت‌های عنوان/واقعیت که در متن صادقانه ذکر شد: MC-F46 و A42P (4MP نه 5)، MC800S5 (8MP نه 5)، H4P (تضاد 4/5MP بازار)، H62 (6MP — در سلکت نیست)، V51 (ai_processor مشکوک)، id15 (سنسور 2MP با عنوان 5MP)، مودم onelink (CPF906 — ادعای 5G قبلی حذف شد).
- راهنمای تصمیم‌گیری: گزینه‌های سلکت برای 3MP/6MP/1.3MP/3.7mm/6-22mm وجود ندارد — مقادیر در description هستند ولی فیلد خالی.

## فیش‌های واریزی داخل سفارش + فیکس روتینگ
- **هماهنگی کاتالوگ فرانت/بک**: `ProductAdminSerializer` حالا `images` (خواندنی)، `datasheet_pdf` (آپلود با multipart PATCH، پاک کردن با JSON null)، `compatible_with` (لیست id) و `compatible_products` (نمایشی) دارد. اندپوینت‌های جدید: `POST products/admin/<pk>/images/`، `DELETE products/admin/images/<img_id>/`، `POST products/admin/images/<img_id>/primary/`. ویرایشگر محصول سه بخش جدید دارد: تصاویر (آپلود چندتایی/حذف/ستاره اصلی)، دیتاشیت PDF (آپلود/حذف)، محصولات سازگار (چیپ + جستجوی debounce). پیلود ذخیره اصلی فیلدهای read-only را strip می‌کند و `compatible_with` را اضافه می‌کند.
- **ویژگی‌های برد** (مایگریشن `catalog/0024`): `board_dimensions` سلکت شد (۳۲*۳۲ / ۳۸*۳۸ / ۳۸*۴۸)؛ `ai_processor` → «پردازنده»؛ فیلد جدید `board_tech_notes` (اطلاعات فنی بیشتر — textarea بزرگ آخر گروه برد)؛ گروه برد در ویرایشگر محصول += شرکت سازنده + قابلیت نصب میکروفون داخلی؛ `board_name` در save() اگر خالی بود از `model_number` پر می‌شود (فقط دسته board). specs عمومی: «پردازنده» + میکروفون داخلی + اطلاعات فنی بیشتر. `BUILTIN_SPEC_BY_TYPE` برد += brand/board_tech_notes. گروه «الکتریکی و متفرقه» و بخش «ویژگی‌های سفارشی» از ویرایشگر حذف شدند (دیتا در DB می‌ماند).
- **به‌روزرسانی شبه‌لحظه‌ای پنل (بدون WebSocket)**: کامپوننت `components/layout/OrderNotifier.jsx` — هر ۱۵ ثانیه admin-badges را پول می‌کند و با افزایش `orders_pending`/`receipts_pending` توست «سفارش/فیش جدید» با دکمه مشاهده نشان می‌دهد (در Layout برای همه صفحات پرسنل). پولینگ صفحه سفارشات ۱۰ثانیه، فیش‌ها و بج منو ۱۵ثانیه + `refetchOnWindowFocus: 'always'`. (تصمیم: Channels/Redis برای این مقیاس اضافه است.)
- **باگ مهم روتینگ**: مسیر پارامتری `admin/<str:order_number>/` (حذف سفارش) قبل از مسیرهای ثابت آمده بود و `admin/receipts/` و `admin/shortage-report/` را قورت می‌داد (۴۰۵). قانون: مسیرهای ثابت admin همیشه قبل از پارامتری.
- **فیش‌ها داخل مودال جزئیات سفارش**: پاسخ `admin/<num>/detail/` حالا `receipts` دارد؛ بخش «🧾 فیش‌های واریزی» در مودال با تامب‌نیل (کلیک = باز شدن تصویر)، مبلغ، تاریخ، پیگیری، وضعیت و دکمه‌های ✓ تأیید / ✗ رد (با مودال دلیل) — تأیید همان FIFO قبلی است و لیست/جزئیات invalidate می‌شود.
- **بج منو**: `receipts_pending` به admin-badges اضافه شد؛ آیتم «فیش‌های واریزی» بج قرمز تعداد فیش‌های در انتظار را نشان می‌دهد (badgeKey: receipts در MenuBadge).
- فیلتر وضعیت صفحه سفارشات: ۵ گزینه (در انتظار تایید/در انتظار پرداخت/در انتظار ارسال/ارسال شده/رد شده) + ۵ کارت آماری هم‌راستا (منبع مشترک STATUS_CARDS)؛ باکس «همه وضعیت ارسال» حذف شد. «ارسال شده» روی delivery_status فیلتر می‌شود. ستون نحوه تسویه (نقدی/اعتباری) هم به جدول برگشت.
- `updated_by` حالا هنگام تأیید سفارش و ویرایش/حذف قلم هم ثبت می‌شود (قبلاً فقط update/رد بود).

## جداسازی خودکار سفارش نقدی از اعتباری در checkout
- `create_direct_order` و `create_inquiry_order` حالا **لیست** سفارش برمی‌گردانند: اگر سبد هم قلم نقدی هم اعتباری (تو حسابی/یکماهه/دوماهه) داشته باشد، دو سفارش جدا ساخته می‌شود (روند تسویه/ارسال متفاوت است) — سفارش نقدی بعد از تأیید → `awaiting_payment`، سفارش فقط‌اعتباری → `ready_to_ship` (وضعیت جدید «منتظر ارسال»، مایگریشن `orders/0014`).
- پاسخ checkout/submit: فیلدهای سفارش اول + `orders` (لیست کامل) + `split` + `overdue_warning`. فرانت در صورت split توست اطلاع‌رسانی با شماره هر دو سفارش نشان می‌دهد.
- مهلت پرداخت فقط برای سفارش دارای قلم نقدی ست می‌شود؛ تأیید سفارش در ادمین حالا مودال را می‌بندد و به لیست برمی‌گردد.
- **صفحه «سفارش‌های من»**: بج «نقدی» (سبز) / «اعتباری» (کهربایی) جلوی شماره سفارش؛ شرایط تسویه هر قلم زیر نام کالا («تو حسابی · ۱۸ روزه» و...) از نقشه `SETTLEMENT_TERMS`؛ **دکمه «ثبت فیش واریزی» فقط برای سفارش‌های تمام‌نقدی** — گارد بک‌اند هم روی `POST /orders/<num>/receipts/` برای سفارش اعتباری ۴۰۰ می‌دهد.
- حذف‌ها: ستون عملیات و وضعیت ارسال از جدول مدیریت سفارشات؛ فلش‌های spinner ورودی عددی با CSS سراسری در index.css.
- مبلغ نهایی تأیید پیش‌فرض = جمع اقلام نقدی (قابل ویرایش)؛ نمایش موجودی هنگام فوکوس روی فیلد تعداد قلم (`available_stock` به detail ادمین اضافه شد).
- حادثه: services.py یک بار تصادفی truncate شد و با کمک ایجنت قبلی بازسازی شد — مراقب regexهای `.*\Z` در پچ‌های پایتونی باش.

## جدول مدیریت سفارشات
- ستون‌های «نحوه تسویه» و «موعد تسویه» از جدول حذف شد (سفارش می‌تواند چند نوع تسویه داشته باشد — جزئیات در مودال می‌ماند).
- بک‌اند لیست ادمین حالا `customer_is_partner` می‌دهد (`select_related('user','user__profile')`). منطق نمایش وضعیت: سفارش همکار در وضعیت‌های pending/confirmed/awaiting_payment → بج طلایی «پیش‌فاکتور» و وضعیت ارسال خالی («—»)؛ مشتری عمومی پرداخت‌کرده → «پرداخت شده».
- ستون «آخرین تغییر» (نام پرسنل — `updated_by` از قبل در پیلود بود) اضافه شد؛ ستون «عملیات» حذف شد (ویرایش از داخل مودال جزئیات).
- **مودال جزئیات**: کارت «نحوه تسویه» حالا انواع موجود در اقلام را نشان می‌دهد («نقدی، تو حسابی، یکماهه»). تقویم موعد از ردیف اقلام حذف شد — قبل از تأیید متن خودکار («همان روز تأیید» / «۱۸ روز پس از تأیید» / ...) و بعد از تأیید تاریخ واقعی نمایش داده می‌شود؛ بک‌اند هنگام تغییر `settlement_type` قلم، موعد را خودکار با `settlement_due_for` بازمحاسبه می‌کند. از فرم تأیید سفارش هم فیلدهای نحوه/موعد تسویه حذف شد (ردیف‌ها per-type ساخته می‌شوند) — فقط مبلغ نهایی + حساب صراف.
- لینک مستقیم به مودال یک سفارش: `/admin/orders-management?order=OR-1008`.

## رد پیش‌فاکتور + ابطال فاکتور + حذف محدود
- **پیش‌فاکتور (Order)**: حذف مستقیم ندارد. وضعیت جدید `rejected` + فیلدهای `reject_reason` و `rejected_at` (مایگریشن `orders/0013`). `POST /api/orders/admin/<num>/reject/` — فقط از PENDING، دلیل اجباری (۴۰۰)، رزروها آزاد، نوتیف به مشتری (`notify_order_rejected`). لیست ادمین پیش‌فرض ردشده‌ها را exclude می‌کند؛ `?status=rejected` فقط آن‌ها را می‌دهد (تب جدا در فرانت با بج قرمز + نمایش دلیل در مودال). **حذف کامل فقط superuser و فقط ردشده‌ها**: `DELETE /api/orders/admin/<num>/` (۴۰۳ غیرسوپریوزر، ۴۰۰ غیرردشده). گزارش: `GET /api/orders/admin/reject-report/?from=&to=` (perm `sale_view`) → تعداد + لیست با دلیل؛ صفحه `/admin/reject-report` (منو زیر «سفارشات»).
- **فاکتور فروش**: DELETE فقط برای draft (غیر draft → ۴۰۰ «از ابطال استفاده کنید»). `POST /api/accounting/sale-invoices/<pk>/void/` (perm `sale_edit`) → status=cancelled + **همه SettlementLineها `is_active=False`** (فیلد جدید، مایگریشن `accounting/0021`). ردیف‌های غیرفعال از FIFO، aging، overdue کاربر و `due_settlements_queryset` حذف می‌شوند. فرانت: دکمه «ابطال فاکتور» در SaleInvoicePage، برچسب وضعیت «باطل‌شده».
- **فیش‌ها**: هیچ endpoint حذفی ندارند (بررسی شد) — فقط رد با دلیل.
- `is_superuser` به UserSerializer (پاسخ login/me) اضافه شد — دکمه «حذف کامل» در فرانت فقط با آن ظاهر می‌شود.
- تست: رد بدون دلیل ۴۰۰، رد موفق + تب ردشده، حذف ۴۰۳/۴۰۰/۲۰۴، ابطال + غیرفعال شدن ردیف‌ها (overdue مشتری ۵۰۰هزار → صفر)، گزارش رد — همگی ✓ + اسکرین‌شات صفحه گزارش و تب ردشده.

# نقطه ادامه کار — ۲ آگوست ۲۰۲۶

## سیستم سفارش، سررسید و وصولی (فیش واریزی + FIFO + aging + مازاد تقاضا)

### تصمیم‌های کلیدی
- مدل‌های تسویه: cash (همان روز) / credit (۱۸ روز) / month1 (۳۰ روز) / month2 (۶۰ روز، فقط واریانت‌های بدون فلگ `month2_unavailable`) — **انتخاب غیرنقدی فقط همکار پلاتینیوم** (`allowed_settlements(user, variant)` در pricing.py — سیلور/گلد/عمومی فقط cash).
- سررسیدها از **تاریخ تایید پرسنل** محاسبه می‌شوند (نه ثبت سفارش).
- ثبت سفارش = پیش‌فاکتور بدون تعهد مالی؛ **فاکتور فروش (SaleInvoice) فقط لحظه تایید ادمین ساخته می‌شود**.

### مدل‌های جدید
- `orders.StockShortage` (مایگریشن `orders/0012`): order/variant/requested_qty/approved_qty/shortage_qty/reason/created_by — هنگام کم کردن یا حذف قلم توسط پرسنل در `AdminOrderItemUpdateView` (فقط سفارش‌های PENDING) ثبت می‌شود.
- `accounting.SettlementLine` (مایگریشن `accounting/0020`): به ازای هر settlement_type موجود در سفارش یک ردیف روی فاکتور (amount + due_date) — پراپرتی‌های paid_amount/remaining_amount/is_overdue/days_overdue.
- `accounting.PaymentReceipt`: فیش واریزی — **عکس اجباری** (در save با Pillow به WebP حداکثر عرض ۱۲۰۰px فشرده می‌شود)، مبلغ، تاریخ واریز، پیگیری اختیاری، وضعیت pending/approved/rejected + reject_reason، uploaded_by (پرسنل می‌تواند به نیابت ثبت کند)، sale_payment.
- `accounting.ReceiptAllocation`: تخصیص FIFO (receipt + settlement_line + amount).
- روی `Order`: `sarraf_account_number` + `sarraf_account_holder` — پرسنل لحظه تایید وارد می‌کند؛ برای سفارش دارای قلم نقدی **اجباری** است (۴۰۰ در غیر این صورت).
- روی `User`: `overdue_settlement_lines()` / `overdue_total()` / `overdue_count()` (import تنبل از accounting).

### جریان تایید (`confirm_inquiry_order` در orders/services.py)
علاوه بر رزرو/توزیع مبلغ قبلی: ساخت SaleInvoice (source=order, confirmed) + SaleItemها با قیمت تاییدشده + SettlementLine per نوع تسویه (due_date = تایید + ۰/۱۸/۳۰/۶۰) + ذخیره صراف. `deduct_from_inventory` صدا زده نمی‌شود (رزرو جدا مدیریت می‌شود).

### فیش و تخصیص FIFO
- مشتری: `POST /api/orders/<num>/receipts/` (multipart) + `GET /api/orders/my-receipts/`.
- پرسنل: `GET|POST /api/orders/admin/receipts/` (+ `?status=`)، `.../receipts/<id>/approve/` و `.../reject/` (دلیل اجباری).
- **تایید (اتمیک)**: تخصیص FIFO روی همه ردیف‌های باز مشتری (قدیمی‌ترین due_date اول) → یک SalePayment per فاکتورِ درگیر → فاکتورِ صفرشده paid → سفارش هم paid می‌شود. رد → نوتیف به مشتری با دلیل (`notify_receipt_approved/rejected` در notifications).
- `due_settlements_queryset()` حالا ردیف‌های SettlementLine سررسیدرسیده را هم پوشش می‌دهد.

### گزارش‌ها و هشدار
- `GET /api/accounting/reports/aging/` (perm `reports_view`): per مشتری سه سطل «سررسید نرسیده / ۱–۱۵ روز معوق / >۱۵ روز معوق».
- `GET /api/orders/admin/shortage-report/?from=&to=` (perm `kardex_view`): جمع مازاد تقاضا per کالا در بازه (پیش‌فرض ۳۰ روز).
- `GET /api/orders/my-overdue/` → `{count, total}`؛ پاسخ checkout/submit هم `overdue_warning` دارد (مسدود نمی‌کند).

### فرانت
- ProductDetailPage: دکمه‌های تسویه پلاتینیوم از `pricing.options` رندر می‌شوند (month2 خودکار ظاهر می‌شود وقتی واریانت اجازه دارد — بک‌اند در `variant_pricing_payload` شرطی اضافه‌اش می‌کند).
- سبد/استعلام: «موجودی: N» + بج کهربایی «⏳ در انتظار تایید موجودی» (available_stock/stock_short در سریالایزر) + بنر معوقه (`components/OverdueBanner.jsx`).
- صفحه سفارش‌های مشتری: کارت اطلاعات واریز صراف (کپی شماره حساب)، ردیف‌های تسویه (معوقه قرمز)، فرم ثبت فیش (عکس اجباری + `capture="environment"` برای دوربین موبایل)، لیست فیش‌ها با وضعیت/دلیل رد. واحدها ریال شد.
- ادمین: فیلدهای صراف در مودال تایید (اجباری برای سفارش نقدی)؛ ۳ صفحه جدید `/admin/receipts` (perm `sale_payment`)، `/admin/aging` (`reports_view`)، `/admin/shortage` (`kardex_view`) + آیتم منو.

### فیکس‌ها و نکات
- باگ NameError ایمپورت‌نشدن `StockMovement` در `orders/services.py` (پرداخت موفق) رفع شد.
- **سفارش‌های تاییدشده قدیمی فاکتور/SettlementLine ندارند** — فقط تاییدهای جدید. aging فقط بر اساس SettlementLine است.
- تست سرتاسری با smoke test در shell انجام شد (۱۳ assert — گیت پلاتینیوم، month2 per-variant، ساخت فاکتور+ردیف‌ها، FIFO، aging)؛ یوزرهای تست: `09999990001` (پلاتینیوم، رمز `test123456`)، `09999990002/3/4`.
- اسکرین‌شات‌های تأیید: صفحات ادمین فیش/aging/مازاد + صفحه سفارش‌های مشتری — همه با دیتای واقعی رندر شدند.

# نقطه ادامه کار — ۱ آگوست ۲۰۲۶

## انبارها + یکسان‌سازی قیمت + تسویه per-item + مدیریت کامل سفارش در ادمین

### اجرای پروژه (سرورها با بستن سشن می‌میرند)
```bash
cd Desktop/cctv_project/cctv_project/cctv_shop && venv/bin/python manage.py runserver 8000
cd Desktop/cctv_project/cctv_project/cctv_frontend && npm run dev   # پورت ۳۰۰۰
```
نکته: اگر صفحه سفید آمد، کش Vite خراب شده — `rm -rf node_modules/.vite` و ری‌استارت `npm run dev`.

### صفحه «انبارها» (/admin/warehouses — منو زیر «طرف حساب‌ها»، perm: kardex_view)
- کارت هر انبار: نام/کد/نوع/جمع موجودی + مودال اقلام. ساخت انبار جدید، حذف (فقط بدون موجودی و بدون سابقه حرکت — بک‌اند ۴۰۰ می‌دهد)، انتقال کالا بین انبارها با جستجوی محصول.
- بک‌اند `apps/inventory/views.py`: POST روی `warehouses/`، `WarehouseDetailView` (DELETE)، `WarehouseStockListView` (`warehouses/<pk>/stocks/`)، `TransferListCreateView` (`transfers/`) — انتقال اتمیک + ثبت کاردکس transfer_in/out با مرجع `TR-<id>`.
- **ثبت موجودی اولیه در مدیریت محصولات حالا `warehouse_id` اجباری می‌خواهد** (قبلاً بی‌سروصدا اولین انبار انتخاب می‌شد) — سلکت انبار در StockSection صفحه محصولات.

### یکسان‌سازی قیمت — قیمت فرمول همه‌جا (ریال)
- **قیمت نمایشی سایت = قیمت فرمول** (سود دسته‌بندی): `price_for_user`/`price_for_settlement` در `apps/catalog/pricing.py`. سبد، سفارش و مبلغ پرداخت همگی از همین استفاده می‌کنند — `final_price` قدیمی دیگر در نمایش/فروش استفاده نمی‌شود.
- **سیستم تخفیف قدیمی (`profile.discount_percent`) حذف شد** از API لیست/جزئیات و فرانت — فیلد در دیتابیس مانده ولی بلااستفاده است (۲ پروفایل هنوز مقدار دارند).
- واحد قیمت‌ها در سایت «ت/تومان» → «ریال» شد (`formatPrice`، ProductCard، HomePage).

### سبد خرید و همکار
- آیتم‌های سبد نام/عکس محصول دارند (`variant_name/variant_sku/variant_image` در سریالایزر — میکسین `_VariantInfoMixin`).
- **همکارها به سبد استعلام هدایت می‌شوند**: لینک سبد در Header و Layout برای `is_partner` به `/inquiry-cart` می‌رود و `/cart` خودکار ریدایرکت می‌کند.

### تسویه per-item (هر قلم تسویه و موعد خودش)
- مدل: `settlement_type` روی CartItem/InquiryCartItem/OrderItem + `settlement_due_date` روی OrderItem (مایگریشن `orders/0011`). چوائس مشترک `Settlement` ماژول‌لسطح در `orders/models.py` + `settlement_due_for()` — **credit: ۱۸ روز، month1: ۳۰، month2: ۶۰، cash: همان روز**.
- `allowed_settlements(user)` در pricing.py: عمومی فقط cash؛ سیلور +month1؛ گلد +credit؛ پلاتینیوم +credit/month1/month2. پلاتینیوم با گزینه انتخابی صفحه محصول به سبد اضافه می‌کند.
- قیمت هر قلم متناسب با تسویه خودش (نقدی همکار = قیمت cash، عمومی = retail).
- شماره سفارش: **`OR-1000`+ ترتیبی** (قبلی ORD-YYYYMMDD-XXXXXX بود).
- **خرید مستقیم هم PENDING (در انتظار تأیید) می‌شود** — پرداخت فقط بعد از تأیید ادمین. تأیید (`admin_confirm_inquiry`) برای هر دو نوع سفارش کار می‌کند.
- **ویرایش اقلام توسط ادمین**: `PATCH /api/orders/admin/<num>/items/<item_id>/` — تعداد واقعی قابل ارسال (۰=حذف قلم، آخرین قلم رد)، تسویه و موعد هر قلم؛ مبلغ کل خودکار بازمحاسبه می‌شود.
- **توزیع مبلغ تأیید روی اقلام به نسبت ارزش** (تقسیم مساوی قدیمی قیمت اقلام را خراب می‌کرد).
- تاریخ‌ها شمسی: `apps/core/utils.py` (`jalali_date`) در ایمیل‌ها؛ نمایش‌ها با fa-IR.

### هشدار سررسید تسویه
- ایمیل به مشتری+ادمین با فهرست اقلام سررسیدرسیده (روزی یک بار per سفارش) — `send_due_settlement_reminders()` هم به‌صورت تنبل از `admin-badges` و هم با کران‌کامند `python manage.py check_settlements`.
- بج `orders_due` در admin-badges + نوار هشدار قرمز در صفحه سفارشات ادمین (کلیک = فیلتر).
- مشتری در حساب کاربری موعد را با هایلایت قرمز می‌بیند.

### باگ‌های مهم رفع‌شده
- **تأیید سفارش rollback می‌شد**: کاربر بدون ایمیل → `recipient_address NOT NULL` در `_log` داخل تراکنش atomic می‌شکست و همه تغییرات پس می‌رفت (با پاسخ ۲۰۰!). حالا `send_user_email` بدون گیرنده رد می‌شود و `_log` مقدار خالی می‌گذارد.
- بلاک مرده `StockMovement` قدیمی در `_create_stock_reservation` (NameError) حذف شد.

### صفحه سفارشات ادمین
- کلیک روی سطر → مودال جزئیات (دکمه اقلام حذف شد). مودال: جدول اقلام قابل ویرایش (تعداد/تسویه/موعد)، کارت اطلاعات، تأیید سفارش pending با مبلغ+تسویه+موعد، مودال ویرایش کامل (وضعیت/ارسال/تسویه/مبلغ تأیید/یادداشت).

# نقطه ادامه کار — ۲۵ جولای ۲۰۲۶

## ریست سیستم از پنل بک‌اپ + حذف محصول + بهبودهای فرم طرف حساب

## ریست سیستم از پنل بک‌اپ + حذف محصول + بهبودهای فرم طرف حساب
- **ریست سیستم در صفحه «بک‌آپ سیستم»**: دکمه «🗑 ریست سیستم» → دو حالت: ۱) soft — حذف تراکنش‌ها (فاکتور خرید/فروش، دریافت/پرداخت، سفارش‌های سایت، کاردکس) و صفر شدن موجودی، با حفظ طرف حساب‌ها/کالاها/بانک/کاربران؛ ۲) hard — حذف همه اطلاعات ورودی (فقط superuserها، انبارها، نرخ یوان و SEO می‌مانند). سه تایید مرحله‌ای (دو چک‌باکس + تایپ RESET). بک‌اند: `POST /api/accounting/system-reset/` (backup_tools.SystemResetApiView) — فقط superuser، استفاده مجدد از `_soft_reset`/`_hard_reset` در admin_tools + safety backup خودکار قبل از ریست.
- **حذف محصول**: `DELETE /api/catalog/products/admin/<pk>/` (RetrieveUpdateDestroyAPIView) — محصول استفاده‌شده در سفارش/فاکتور با ۴۰۹ رد می‌شود. دکمه «🗑 حذف محصول» دو مرحله‌ای در مودال ویرایش.
- **فرم افزودن طرف حساب**: موبایل اجباری (فرانت+بک‌اند)؛ نوع ۴ گزینه‌ای (همکار/تامین کننده/حمل و ترخیص/پرسنل)؛ فیلد `partner_tier` (silver/gold/platinum — مایگریشن `accounting/0014`) که با انتخاب «همکار» ظاهر و اجباری می‌شود؛ ارز پیش‌فرض ریال.
- **فرمول قیمت**: ستون VIP حذف (فیلد Category هم حذف شد، `catalog/0023`)؛ فلگ `month2_unavailable` روی واریانت → ستون دوماهه «ندارد» با کلیک. سرچ مدیریت محصولات هوشمند شد (ارقام فارسی/عربی→لاتین در `_normalize` + جستجوی SKU با distinct). فیکس تداخل آیکون ذره‌بین در سرچ‌ها. بخش هزینه/سود دسته collapsible + سرچ زیر نرخ + ستون موجودی + رند به بالای هزار تومان. پرمیشن‌های `pricing_rate_view`/`pricing_costs_view` (بک‌فیل `users/0009`). هزینه‌های تمام‌شده (خرید/حمل یوان + ترخیص ریال) در ثبت موجودی اولیه → `unit_price` در کاردکس.
- **حذف محصول V50 (id 14) تصادفی در تست → بازیابی با import_doorbinkar** (id جدید ۱۵، همان slug/SKU/موجودی).

## صفحه «فرمول قیمت» (/admin/pricing — منو زیر «مدیریت محصولات»، perm: products_edit)
- **مدل**: روی `Category`: `shipping_cost_cny` + `clearance_cost_cny` (یوان) و ۶ درصد سود نوع فروش `profit_vip/cash/credit/month1/month2/retail_percent` — **همه سطح دسته** (درخواست کاربر: سود برای همه محصولات دسته یکی است، نه per-product؛ مایگریشن‌های `catalog/0021` و `0022` — ابتدا روی واریانت بود و به دسته منتقل شد). صفرِ هر فیلد در زیردسته یعنی ارث از دسته اصلی. `final_price` فعلی سایت دست‌نخورده (هنوز از `profit_percent` و `shipping_cost_cny` خود واریانت استفاده می‌کند).
- **API**: `GET /api/catalog/pricing/` (نرخ + دسته‌ها با ۸ فیلد هزینه/سود + همه محصولات با قیمت یوان)، `PATCH pricing/categories/<pk>/` (حمل/ترخیص/۶ سود)، `PATCH pricing/variants/<pk>/` (فقط قیمت یوان).
- **فرانت `PricingPage.jsx`**: نرخ یوان روز بالای صفحه (ویرایش با perm `exchange_rate_edit`)؛ بخش «هزینه و سود هر دسته» جمع‌شده (collapsible) با جدول درختی (والد + زیردسته با ↳)؛ سرچ هوشمند محصول زیر نرخ (نرمال‌سازی ارقام فارسی/عربی و ك/ي)؛ جدول محصولات با ستون موجودی — فقط قیمت یوان قابل ویرایش است و ۶ ستون قیمت نهایی فقط‌خواندنی با رند به بالا. نکته: قیمت‌های این صفحه فعلاً صرفاً محاسبه/نمایش است و به چک‌اوت سایت وصل نشده.
- **گیت نقش‌محور**: دو پرمیشن جدید `pricing_rate_view` («مشاهده نرخ یوان در فرمول قیمت») و `pricing_costs_view` («مشاهده/ویرایش هزینه و سود دسته‌ها») در `users/models.py` + بک‌فیل برای نقش‌های دارای `products_edit` (مایگریشن `users/0009`). کارت نرخ یوان و بخش «هزینه و سود هر دسته» در PricingPage فقط با این پرمیشن‌ها نمایش داده می‌شوند و `PATCH pricing/categories/<pk>/` هم در بک‌اند ۴۰۳ می‌دهد. گروه «فرمول قیمت» در RolesPage اضافه شد. نرخ یوان و قیمت یوان محصولات و جدول اصلی برای همه نقش‌های دارای products_edit باز است.

## کنترل دسترسی نقش‌محور طرف حساب‌ها + حذف تب لیست
- **تب «طرف حساب‌ها» (لیست) حذف شد** — صفحه حالا دو تب دارد: «کاردکس اشخاص» (پیش‌فرض، حالا با include_registered یعنی کاربران ثبت‌نامی هم در جستجو می‌آیند) و «تراز کلی». دکمه «+ افزودن طرف حساب» به هدر صفحه منتقل شد (فقط با پرمیشن `contacts_create`)؛ تأیید/لغو همکار و ویرایش مانده اول دوره به کارت جزئیات تب کاردکس منتقل شدند.
- **پرمیشن‌های جدید** در `users/models.py`: `contacts_create` («افزودن طرف حساب») و `partner_approve` («تأیید همکار») — بک‌فیل خودکار برای نقش‌های دارای `contacts_edit` (مایگریشن `users/0008`). گیت بک‌اند: POST contacts → `contacts_create`، PATCH تأیید همکار (u_*) → `partner_approve`، بقیه PATCH → `contacts_edit`.
- **محدودیت دید بر اساس نوع طرف حساب**: فیلد `Role.allowed_contact_types` (JSON — خالی = همه نوع‌ها). در `GET /accounting/contacts/` (هم Contact دستی هم کاربران ثبت‌نامی)، `GET/PATCH contacts/<pk>/` (۴۰۳ برای نوع غیرمجاز) و POST (رد ساخت نوع غیرمجاز) اعمال می‌شود. چیپ‌های انتخاب نوع در ویرایشگر نقش (RolesPage — داده از `contact_types` در پاسخ GET roles)؛ `my-permissions` هم `allowed_contact_types` را برمی‌گرداند و هوک `usePermissions` آن را expose می‌کند (سلکت نوع در فرم افزودن فقط نوع‌های مجاز را نشان می‌دهد).

## ادغام «تراز حساب‌ها» در «طرف حساب‌ها» + پنل محصولات + فیکس مودال
- **صفحه «طرف حساب‌ها» تب‌دار شد** (`ContactsPage.jsx`): سه تب «👥 طرف حساب‌ها» (محتوای قبلی، کامپوننت ContactsMain)، «👤 کاردکس اشخاص» و «📊 تراز کلی» — دو تب آخر از ReportsPage منتقل شدند و **ReportsPage.jsx حذف شد**. آیتم منوی «تراز حساب‌ها» از `config/adminMenu.jsx` برداشته شد و روت `/admin/reports` در App.jsx به `/admin/contacts` ریدایرکت می‌شود.
- **مدیریت محصولات**: لیست صفحه‌بندی‌شده API کامل خوانده می‌شود (قبلاً فقط ۲۴ تای صفحه اول)؛ ستون «#» (ردیف) و «موجودی» به جدول اضافه شد. `ProductAdminSerializer` حالا `variants` را هم برمی‌گرداند. اندپوینت جدید `POST /api/catalog/products/admin/<pk>/opening-stock/` — ثبت موجودی اولیه: هم `stock_quantity` واریانت زیاد می‌شود و هم حرکت `opening` در کاردکس (مثل الگوی فاکتور خرید). در مودال ویرایش محصول بخش «موجودی انبار» با موجودی فعلی هر واریانت + فیلد ثبت اضافه شد.
- **فیکس باز نشدن مجدد مودال ویرایش محصول**: `setForm` داخل `queryFn` بود و در cache hit (React Query v5) اجرا نمی‌شد ← به الگوی `useEffect(() => setForm(data), [data])` تغییر کرد.

# نقطه ادامه کار — ۲۵ جولای ۲۰۲۶

## اصلاح اسلاگ‌های غیراستاندارد + مکانیزم slug-history (ریدایرکت ۳۰۱)
- **مدل `SlugRedirect`** (`apps/catalog/models.py`، مایگریشن `catalog/0020`): نگاشت `old_slug → new_path`. هوک `save` مدل‌های `Product` و `education.Article` هنگام تغییر اسلاگ به‌صورت خودکار ریدایرکت ثبت می‌کند (با یکسری‌سازی زنجیره‌ها — ریدایرکتهای قبلی مستقیم به مقصد نهایی می‌روند). از این به بعد تغییر اسلاگ از پنل هم بی‌خطر است.
- **ریدایرکت ۳۰۱ در API**: `ProductDetailView` (`catalog/views.py`) و `ArticleDetailView` (`education/views.py`) هنگام ۴۰۴، اسلاگ را در SlugRedirect جستجو می‌کنند و در صورت وجود `HttpResponsePermanentRedirect` به URL جدید API برمی‌گردانند. فرانت (`ProductDetailPage`/`ArticleDetailPage`) بعد از لود، اگر اسلاگ پاسخ با پارامتر URL فرق داشت با `navigate(replace)` آدرس مرورگر را به اسلاگ جدید تغییر می‌دهد (canonical هم از همان ابتدا اسلاگ جدید است).
- **۲۰ اسلاگ اصلاح شد** (`scripts/fix_nonstandard_slugs.py` — یک‌بار اجرا، idempotent): ۱۷ محصول (اسلاگ فارسی، خراب `%2B...`، uppercase و نقطه‌دار) + ۳ مقاله تستی با اسلاگ فارسی. نمونه: `h43-ip-4mp-board`، `n664mwarm-metal-dome-housing`، `chin-omadi`. تست: اسلاگ قدیمی فارسی/خراب → ۳۰۱ → ۲۰۰، legacy redirect سایت قدیمی (`/products/<legacy_id>/x`) همچنان سالم و به اسلاگ جدید اشاره می‌کند، sitemap به‌روز است.
- **کشف مهم — محصولات تکراری**: محصولات تستی قدیمی (بدون legacy_id) ۱ (H55)، ۴ (H53) و ۳ (لنز+هولدر YT-10169) تکراریِ محصولات منتقل‌شده ۲۲، ۶۵ و ۶۱ هستند ← کاندیدای حذف/ادغام برای جلوگیری از duplicate content.

# نقطه ادامه کار — ۲۴ جولای ۲۰۲۶

## انتقال از doorbinkar.com: دسته‌بندی، SEO/GEO، ریدایرکت و ایمپورت محصولات
- **دسته‌بندی‌ها دقیقاً مطابق سایت قدیمی شدند** (۵ والد + ۱۴ زیردسته). فیلد `legacy_id` (unique، روی Category و Product) نگاشت id سایت قدیمی را نگه می‌دارد — مایگریشن `catalog/0019` فیلدها را ساخت، نام/اسلاگ دسته‌های موجود را با سایت قدیمی یکی کرد (مثل `cctv-camera-board`، `accessories-modem`)، ۶ زیردسته جدید ساخت (wifi-camera-board، cw/ytot-lens-holder، cctv-accessories، assembly-tools، cctv-led) و «لنز استارلایت» را حذف کرد (در سایت قدیمی نبود). متاهای SEO همه دسته‌ها هم پر شد.
- **ریدایرکت ۳۰۱ از URLهای قدیمی**: `apps/catalog/legacy_redirects.py` — `/cat/<legacy_id>/...` → `/categories/<slug>` و `/products/<legacy_id>/...` → `/products/<slug>` (mount در `config/urls.py`). **برای سرور**: بلاک‌های nginx در `deploy/nginx-legacy-redirects.conf` را هنگام انتقال دامنه به `/etc/nginx/sites-enabled/cctv` اضافه کن (مسیرهای `/cat/<عدد>` و `/products/<عدد>` و `/sitemap.xml` → گانیکورن).
- **SEO/GEO تکنیکال فرانت**: `react-helmet-async` + کامپوننت مشترک `src/components/Seo.jsx` (title، description، keywords، canonical، og:/twitter:، متاهای geo، JSON-LD). صفحات Home/Products/Category/ProductDetail/Blog/ArticleDetail وصل شدند؛ ProductDetail دو JSON-LD دارد (Product با offers به ریال IRR + BreadcrumbList) و Home دو JSON-LD (Organization با ۴ تلفن + WebSite). base URL از `VITE_SITE_URL` (پیش‌فرض https://www.doorbinkar.com). بک‌اند: `keywords` و `geo_tags` به `ProductDetailSerializer` اضافه شد.
- **sitemap و robots**: `config/sitemaps.py` (محصولات/دسته‌ها/پکیج‌ها/مقالات/استاتیک — ۵۷ URL) در `/sitemap.xml` (نیازمند `django.contrib.sitemaps` که به INSTALLED_APPS اضافه شد)؛ `cctv_frontend/public/robots.txt` با Disallow روی admin/api/account/cart.
- **انتقال محصولات (انجام شد — ۸۰ محصول، کامل)**: `cctv_shop/scripts/scrape_doorbinkar.py` محصولات را از endpoint آژاکس سایت قدیمی (`POST /ajax/CategoryController/categorySearch` با `is_buyable=false`) + صفحه هر محصول استخراج و تصاویر را در `media/products/migrated/<legacy_id>/` دانلود می‌کند؛ خروجی `scripts/output/doorbinkar_products.json`. کامند `python manage.py import_doorbinkar` ایمپورت می‌کند (slug لاتین قدیمی حفظ می‌شود → URL پایدار). **تکمیلی**: لیست دسته‌های AJAX فقط ۲۲ محصول را نشان می‌داد؛ با پروب مستقیم `/products/<id>/x` (۲۰۰=موجود، ۳۰۲ به /404=ناموجود) روی بازه ۱–۲۶۰ مشخص شد **۸۰ محصول** وجود دارد. ۵۸ محصول جامانده (مثل کیس‌های بولت/دام که دسته‌شان در AJAX خالی بود) با `scripts/scrape_missing_products.py` استخراج شد (دسته از breadcrumb صفحه، slug از canonical) → `scripts/output/doorbinkar_missing.json` → ایمپورت شد. جمع نهایی: **۸۰ محصول منتقل‌شده + ۵ محصول تستی قدیمی = ۸۵**. دو محصول (94، 188) قیمت نداشتند (۰ ثبت شد).
- **هشدارهای مهم بعد از ایمپورت**:
  - قیمت‌ها = قیمت سایت قدیمی با **سود ۰٪** (purchase_price_cny = قیمت تومانی ÷ نرخ روز) ← حاشیه سود variants را بازبینی کن.
  - موجودی **نمادین** است: ۱۰۰ برای محصولات قابل‌خرید سایت قدیمی، ۰ برای ناموجودها ← انبار واقعی را به‌روزرسانی کن.
  - قیمت برخی محصولات ممکن است قیمت قبل از تخفیف سایت قدیمی باشد (مثل V22: ۸۲۴,۸۸۰ به‌جای ۸۰۸,۵۰۰).
  - SKUها به‌صورت `DK-<legacy_id>` ساخته شدند.
- اجرای مجدد: `cd cctv_shop && venv/bin/python scripts/scrape_doorbinkar.py` سپس `venv/bin/python manage.py import_doorbinkar` (idempotent بر اساس legacy_id).
- **انتقال بلاگ (انجام شد — ۱۰ مقاله، کامل)**: فیلد `legacy_id` به `education.Article` اضافه شد (مایگریشن `education/0002`). `scripts/scrape_doorbinkar_blog.py` هر ۱۰ مقاله سایت قدیمی (id ۲ تا ۱۱) را با محتوای HTML کامل، تصویر شاخص (`media/education/articles/migrated/`)، تگ‌ها، نویسنده و **تاریخ انتشار اصلی** (تبدیل شمسی→میلادی با jdatetime) استخراج کرد؛ کامند `python manage.py import_doorbinkar_blog` ایمپورت می‌کند. ریدایرکت ۳۰۱: `/blog/<id قدیمی>/<slug>` → `/blog/<slug>` (`legacy_blog_redirect`). ۳ مقاله قبلی سایت جدید محتوای متفاوتی داشتند و دست‌نخورده ماندند.
- **ریدایرکت صفحات ثابت قدیمی** (در `deploy/nginx-legacy-redirects.conf`): `/about-us`→`/`، `/rules`→`/terms`، `/complaints`→`/`، `/search`→`/products`، `/login`→`/auth/login`، `/register`→`/auth/register` + `location ~ ^/blog/\d+` → گانیکورن.
- **چک کامل انتقال**: پروب id محصولات تا ۳۲۰ (۸۰ محصول = همه)، robots.txt قدیمی فقط مسیرهای CRM/dashboard را disallow می‌کرد (معادل‌ها در robots.txt جدید هست)، پوشش meta_title/description/keywords/geo_tags برای هر ۸۰ محصول ۱۰۰٪، sitemap.xml حالا ۱۲۵ URL دارد.
- **غنی‌سازی محصولات منتقل‌شده** (`python manage.py enrich_migrated_products` — فقط فیلدهای خالی، idempotent): ۲۸ نام مشکل‌دار اصلاح شد (فاصله اضافی، «مگاپیکسیل»، IPچهار، مدل:X) و ~۲۰۰ فیلد مشخصات ساختاری از نام/توضیحات استخراج شد: board_system (۵۰)، board_resolution (۳۸)، sensor_name (۳۳)، brand (۲۵)، lens_type/degree/resolution، housing_type/material، voltage... — حالا فیلترهای صفحه محصولات، جدول «مشخصات فنی» صفحه محصول و جستجوی هوشمند روی محصولات منتقل‌شده کار می‌کنند. محتوای مقالات/توضیحات لینک قدیمی به doorbinkar.com نداشت (بررسی شد).

# نقطه ادامه کار — ۲۲ جولای ۲۰۲۶

## جدید در ۲۲ جولای
- **شماره فاکتور فروش ساده و ترتیبی شد**: `generate_invoice_number` در `accounting/models.py` حالا به‌جای `INV-YYYYMMDD-XXXXXX` شماره عددی متوالی می‌دهد (بزرگ‌ترین شماره عددی موجود + ۱، کف ۱۰۰۰). مایگریشن داده `accounting/0011_renumber_sale_invoices` هر ۱۵ فاکتور قبلی را به ترتیب تاریخ از ۱۰۰۰ تا ۱۰۱۴ شماره‌گذاری مجدد کرد و `StockMovement.reference` (و شماره داخل note) را هم اصلاح کرد. روی سرور هم با اجرای `migrate` بعد از دیپلوی اعمال می‌شود.
- **واحد نرخ یوان ریال شد**: `ExchangeRateSetting.rate_cny_to_irt` حالا ریال است (لیبل/هلپ‌متن/`__str__` در ادمین جنگو «نرخ ارز (یوان)») — مایگریشن `catalog/0016_exchange_rate_rial` مقدار موجود را ×۱۰ کرد تا قیمت‌ها تغییر نکنند. `ProductVariant.final_price` همچنان **تومان** برمی‌گرداند (داخل پراپرتی ÷۱۰ با Decimal). گزارش سود و ترازنامه (`accounting/views.py`) دیگر ×۱۰ نمی‌کنند؛ صفحه تراز ادمین جنگو (`accounting/admin.py` + تمپلیت `balance_report.html`) ریال شد — باگ قدیمی ×۱۰ کم‌محاسبه CNY در آن گزارش هم با همین تغییر درست شد. فیکس جنبی: `ExchangeRateSerializer` فیلد ناموجود `updated_at` داشت و GET اندپوینت ۵۰۰ می‌شد ← حذف شد.
- **پرمیشن `exchange_rate_edit`** («ویرایش نرخ یوان روز») در `users/models.py` + بک‌فیل نقش‌های ادمین و حسابدار (مایگریشن `users/0007`). `PUT /api/catalog/exchange-rate/` حالا به‌جای `IsAdminUser` با `_has_staff_perm` (در `catalog/views.py`) چک می‌کند؛ GET همچنان عمومی است.
- **ویجت «نرخ یوان روز»** (`src/components/layout/ExchangeRateWidget.jsx`): در هدر سایدبار پنل پرسنل و دراور موبایل ادمین (Layout.jsx) — مشاهده برای همه پرسنل، دکمه ✏️ و مودال ویرایش (AmountInput) فقط با پرمیشن. برچسب نرخ در FinancialReportsPage هم «ریال» شد.
- **مشتریان و همکاران در طرف حساب‌ها** (رویکرد ادغام مجازی — بدون فیلد/سیگنال روی Contact):
  - `Contact.ContactType` += `customer` (مشتری) و `partner` (همکار) — مایگریشن `accounting/0012`. حالا «افزودن مشتری» سریع فرم فروش (`QuickAddCustomer`) که از قبل `contact_type:'customer'` می‌فرستاد معتبر است.
  - `GET /accounting/contacts/?include_registered=1` — لیست ادغامی: Contactهای دستی با id پیشونددار `c_<id>` + کاربران ثبت‌نامی سایت (غیرپرسنل) با `u_<id>`. دسته‌بندی ثبت‌نامی‌ها با همان منطق `User.is_partner`: تأیید همکار → «همکار»، وگرنه «مشتری». **بدون پارامتر، خروجی دقیقاً مثل قبل (id عددی، فقط Contact)** تا مصرف‌کننده‌های قدیمی (PaymentsPage، PurchaseInvoicePage، ReportsPage، SaleInvoicePage) نشکنند. POST حالا contact_type را اعتبارسنجی می‌کند (پاسخش هنوز id عددی است).
  - `ContactDetailView` دوحالته شد (URL از `<int:pk>` به `<pk>`): `c_` → همان رفتار قبلی + فیلدهای یکدست‌سازی؛ `u_` → پروفایل کاربر (شرکت/ایمیل/تاریخ عضویت)، `sale_invoices` (۲۰ تای آخر با مانده هر فاکتور)، `sale_debt` (جمع مانده فاکتورهای confirmed/paid — فقط نمایشی، وارد `balance_irr` نمی‌شود تا ترازنامه دوباره‌شماری نشود)، `partner_approved`. PATCH روی `u_` فقط `partner_approved` می‌پذیرد (ساخت/به‌روزرسانی UserProfile و تغییر خودکار دسته در لیست) — گیت `contacts_edit`.
  - فرانت `ContactsPage.jsx`: چیپ‌های فیلتر مشتری/همکار (خودکار از TYPE_LABELS)، بج «🌐 سایت» برای ثبت‌نامی‌ها، کارت جزئیات ویژه کاربر (بدهی فاکتور به‌جای مانده، دکمه «تأیید/لغو تأیید همکار»، لیست فاکتورهای فروش، بدون ردیف مانده اول دوره).
  - باگ قدیمی `QuickAddCustomer` **اصلاح شد**: قبلاً رکورد Contact می‌ساخت و id آن را به‌جای `customer_id` (User) در فاکتور می‌فرستاد (خطای ۴۰۰ یا لینک به کاربر اشتباه). حالا اندپوینت جدید `POST /api/accounting/customers/` (`CustomerQuickCreateView`، پرمیشن `sale_create`) کاربر واقعی با پروفایل PUBLIC و رمز unusable می‌سازد؛ شماره تکراری → همان کاربر با `existing:true` برمی‌گردد؛ موبایل نامعتبر → ۴۰۰. فرم QuickAddCustomer به همین اندپوینت وصل شد (سلکت «نوع طرف حساب» حذف، موبایل اجباری) و مشتری سریع‌ساخته‌شده هم در customer-search و هم در دسته «مشتری» طرف حساب‌ها ظاهر می‌شود.
- **فیکس لاگ‌اوت خودکار / خالی شدن پنل** (`src/services/api.js`): بک‌اند `ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION` دارد ولی فرانت ۱) توکن رفرش جدید را ذخیره نمی‌کرد (رفرش بعدی همیشه با توکن blacklist‌شده می‌رفت و ۴۰۱ می‌گرفت) و ۲) چند درخواست موازی ۴۰۱ هرکدام جداگانه رفرش می‌زدند و با rotate، همدیگر را blacklist می‌کردند ← توفان ۴۰۱ و لاگ‌اوت کاربر وسط کار. حالا رفرش‌ها روی یک Promise مشترک سوار می‌شوند و `data.refresh` جدید ذخیره می‌شود. تست: رفرش قدیمی بعد از rotation → ۴۰۱، جدید → ۲۰۰.
- **زیردسته (دسته‌بندی دو سطحی)**: مدل `Category.parent` از قبل بود؛ حالا از پنل قابل ساخت است:
  - بک: `Category.save` حالا slug یکتا می‌سازد (نام تکراری زیر والدهای مختلف → `-۲`، `-۳`)؛ `CategoryAdminSerializer.validate` فقط دو سطح اجازه می‌دهد («والد باید دسته اصلی باشد») و حلقه والد را رد می‌کند. POST/PATCH `/catalog/categories/admin/` فیلد `parent` می‌پذیرد. `category_name` در لیست محصولات مسیر کامل «والد / زیردسته» را نشان می‌دهد (از `__str__` مدل).
  - فیلتر محصول (`ProductFilter.filter_category`) و API عمومی دسته‌ها (`/catalog/categories/` با children تو در تو) از قبل زیردسته را پوشش می‌دادند — دست نخورده.
  - فرانت `AdminCategoriesPage`: سلکت «دسته والد» در فرم ساخت (با به‌ارث‌رسیدن نوع دسته از والد) و فرم ویرایش، لیست درختی با تورفتگی و بج «زیردستهٔ X». فرانت `AdminProductsPage`: سلکت دسته در ویرایشگر محصول گزینه‌ها را به‌صورت «والد / زیردسته» مرتب می‌کند.
  - **نوع زیردسته کاملاً از والد به ارث می‌رسد**: `CategoryAdminSerializer.validate` مقدار `category_type` زیردسته را اجباری برابر والد می‌کند (هر مقداری بفرستی نادیده گرفته می‌شود)؛ تغییر نوع دسته اصلی در PATCH به همه زیردسته‌هایش سرایت می‌کند (`cat.children.update`). سلکت «نوع دسته» در فرم ساخت/ویرایش وقتی والد انتخاب شده حذف و با نمایش فقط‌خواندنی «از والد» جایگزین می‌شود.
- **صفحه جدید «ویژگی‌های دسته‌ها»** (`/admin/category-fields` — آیتم منو زیر «مدیریت دسته‌بندی» با پرمیشن `products_edit`): مدیریت متمرکز اینکه هر دسته چه ویژگی‌هایی داشته باشد (همان فیلدهایی که در ویرایشگر محصول پر می‌شوند) — چیپ انتخاب دسته به‌صورت درختی + پنل کامل ویژگی‌های پایه (مخفی/بازنویسی لیبل و گزینه) و سفارشی (افزودن/حذف). منطق پنل از AdminCategoriesPage به کامپوننت مشترک `src/components/admin/CategoryFieldsManager.jsx` استخراج شد و در هر دو صفحه استفاده می‌شود؛ هیچ تغییر بک‌اندی لازم نبود (همان endpointهای `categories/admin/<id>/fields/` و PATCH دسته).
- **زیردسته‌ها ویژگی مستقل ندارند — همه‌چیز از دسته اصلی**: قانون نهایی رفتار ویژگی‌ها (جایگزین ارث‌بری ادغامی قبلی):
  - بک: `POST /catalog/categories/admin/<pk>/fields/` برای زیردسته ۴۰۰ می‌دهد («ویژگی را به دسته اصلی اضافه کنید»)؛ مایگریشن `catalog/0017` ویژگی‌های احتمالی زیردسته‌ها را به والد منتقل (با dedupe روی key) و `hidden_fields`/`field_overrides` زیردسته‌ها را پاک می‌کند.
  - فرانت: `CategoryFieldsManager` برای زیردسته فقط یک راهنمای متنی نشان می‌دهد («این زیردسته ویژگی مستقل ندارد و همه ویژگی‌هایش را از «X» به ارث می‌برد — برای افزودن یا ویرایش ویژگی، دسته اصلی را انتخاب کنید») — بدون هیچ لیست ویژگی یا فرم. ویرایشگر محصول (`AdminProductsPage`) برای محصولِ زیردسته، ویژگی‌های سفارشی/مخفی/بازنویسی را از `effectiveCat` (والد) می‌خواند. صفحه «ویژگی‌های دسته‌ها» پارامتر `?cat=<id>` برای لینک مستقیم به یک دسته دارد.
- **ارث‌بری ویژگی‌های سفارشی از دسته والد** (نمایشی): تعریف ویژگی روی دسته اصلی برای محصولات همه زیردسته‌هایش کافی است — نمایش عمومی (`ProductDetailSerializer.get_specs`) لیست ادغام‌شده «والد اول، بعد خود دسته» را با dedupe روی key برمی‌گرداند. تست: ویژگی روی دسته اصلی لنز برای محصولِ داخل زیردسته در specs عمومی نمایش داده شد ✓

# نقطه ادامه کار — ۲۱ جولای ۲۰۲۶

## جدید در ۲۱ جولای
- **موجودی/مانده اول دوره**:
  - محصولات: نوع حرکت جدید `opening` («موجودی اول دوره») در `StockMovement.MovementType` (inventory، migration 0004) — در مودال «ثبت ورود/خروج موجودی» صفحه کاردکس قابل انتخاب است (همیشه ورودی/مثبت) و در کاردکس با رنگ طلایی نمایش داده می‌شود
  - اشخاص: فیلدهای `opening_balance_irr` (BigInt) و `opening_balance_cny` (Decimal) روی مدل `Contact` (accounting، migration 0010) — مثبت = طرف حساب به ما بدهکار، منفی = ما بدهکاریم؛ در `balance_irr`/`balance_cny` لحاظ می‌شوند
  - API: ساخت طرف حساب با مانده اول دوره + `PATCH /api/accounting/contacts/<pk>/` (ویرایش فیلدها و مانده اول دوره، perm کد `contacts_edit`)؛ لیست/جزئیات contact حالا فیلدهای opening را برمی‌گردانند
  - فرانت: فرم ساخت طرف حساب + ردیف «مانده اول دوره» در کارت جزئیات با مودال ویرایش (`ContactsPage.jsx`)
- **کامپوننت `AmountInput`** (`src/components/ui/AmountInput.jsx`): جداکننده سه‌رقمی هنگام تایپ + تبدیل خودکار ارقام فارسی/عربی به لاتین (فیکس باگ صفر ثبت شدن موجودی اولیه بانک با کیبورد فارسی — `Number('۵۰۰۰')=NaN` می‌شد). مقدار همیشه رشته خام لاتین در state می‌ماند و `onChange({target:{value}})` می‌دهد. اعمال در: بانک (موجودی اولیه)، طرف حساب (مانده اول دوره)، دریافت/پرداخت (مبلغ/نرخ)، کاردکس (قیمت واحد)، فاکتور فروش (قیمت واحد/تخفیف/ارسال/مالیات/مبالغ دریافتی)، فاکتور خرید (نرخ‌ها/هزینه‌ها/قیمت یوان/هزینه‌های جانبی)
- **منوی ادمین**: ترتیب = داشبورد، سفارشات، فاکتور فروش، فاکتور خرید، بانک، کاردکس، طرف حساب‌ها، ...
- **ادغام «دریافت و پرداخت» در «بانک» + هاب جدید**: بخش‌های نمایشی صفحه پرداخت (کارت‌های خلاصه موجودی، لیست حساب‌های بانکی و صندوق، آخرین تراکنش‌ها با ویرایش/حذف) به ابتدای صفحه بانک منتقل شد. صفحه `/admin/payments` حالا **هاب ثبت تراکنش** با ۴ اکشن است: ثبت دریافت / ثبت پرداخت (همان `PaymentForm`)، **سند حسابداری** (`VoucherForm` — انتقال بدهی/طلب بین دو طرف حساب با دو رکورد متقابل out/in، بدون گردش بانکی)، **جابجایی پول درون بانک** (`TransferForm` — هم‌ارز: یک رکورد from+to؛ بین‌ارزی: دو رکورد با نرخ تبدیل و محاسبه زنده مبلغ مقصد، فقط ریال↔ارز). آیتم منو «دریافت و پرداخت» زیر «فاکتور خرید». بک‌اند: `contact_id` در `POST /accounting/payments/` اختیاری شد و **پرداخت‌های `direction='in'` حالا در `balance_irr`/`balance_cny` طرف حساب اثر می‌گذارند** (قبلاً نادیده گرفته می‌شدند — روی مانده‌های قبلی هم اصلاح اعمال می‌شود)
- **کارت بانک** (`AdminBanksPage.jsx`): نام حساب بزرگ بالا + نام بانک کوچک‌تر زیر آن

# نقطه ادامه کار — ۱۹ جولای ۲۰۲۶

## دیپلوی (انجام‌شده ۲۶ جولای — دوم)
- **بازنشانی کامل سرور به نسخه لوکال**: دیتابیس سرور با `db.sqlite3` لوکال جایگزین شد (دیتاهای قبلی سرور پاک شد)، پوشه `media/` با `--delete` همگام شد، کد بک‌اند + بیلد فرانت منتقل شد. بکاپ کامل قبلی در `/opt/backups/20260726b/`
- مایگریشن `education.0003_alter_article_legacy_id` هم ساخته و روی هر دو اعمال شد
- فیچرهای این نسخه: ویرایش کامل طرف حساب (+استان با جستجو، مانده اول دوره برای همه)، حذف طرف حساب برای همه انواع، لیست کاردکس فقط همکارهای تأییدشده + تب «مشتریان سایت»، باکس جستجوی حرفه‌ای طرف حساب، **پنل مشتری: تب داشبورد (نمودار recharts) + تب کاردکس مشتری** (`/api/accounting/my/dashboard/` و `/my/kardex/`)
- توجه: یوزرهای دیتابیس سرور هم جایگزین شدند — ورود ادمین با یوزر/رمز لوکال است

## دیپلوی (انجام‌شده ۲۶ جولای)
- آپدیت کامل از نسخه توسعه (`Desktop/cctv_project/cctv_project`): بک‌اند (apps catalog + core، ۱۵ مایگریشن شامل `core.0002` فیلدهای عکس صفحات استاتیک)، بیلد جدید فرانت، بلاک‌های ریدایرکت ۳۰۱ قدیمی (`deploy/nginx-legacy-redirects.conf`) به `/etc/nginx/sites-enabled/cctv` اضافه و nginx ریلود شد
- ردیف «درباره ما» (`StaticPage` با key=about) در DB سرور ساخته شد؛ آپلود ۴ عکس از پنل جنگو ← صفحات استاتیک ← درباره ما
- `BEHPARDAKHT_CALLBACK_URL=http://185.116.162.244/api/orders/payment/callback/` به `.env` سرور اضافه شد
- بکاپ قبل از تغییرات در `/opt/backups/20260726/` (کد بک‌اند، db.sqlite3، فرانت، کانفیگ nginx)

## دیپلوی (انجام‌شده ۱۹ جولای)
- **سرور**: `ssh -p 3031 root@185.116.162.244` — سایت: http://185.116.162.244
- معماری: بک‌اند `/opt/cctv/backend` (gunicorn, سرویس `cctv-backend.service`)، فرانت بیلدشده `/opt/cctv/frontend` (nginx، کانفیگ `/etc/nginx/sites-enabled/cctv`)، SQLite همان سرور
- `.env` سرور: DEBUG=False و SECRET_KEY تنظیم‌شده ✓
- آپدیت امروز: ۵ فایل بک‌اند (accounting/users/inventory/dashboard views+urls)، بیلد جدید فرانت، backfill نقش‌ها روی DB سرور، لوگوی جدید (`site/logo-header.png`) — بکاپ‌ها در `/opt/backups/20260719/`
- مسیر آپدیت بعدی: تغییرات لوکال → scp فایل‌های بک‌اند → `npm run build` و آپلود dist → `systemctl restart cctv-backend`

## جدید در ۱۹ جولای
- **تاریخ شمسی در کل سایت**: یوتیلیتی `src/utils/date.js` (`formatDate` با Intl فارسی — بدون وابستگی). اعمال در همه صفحات ادمین (خرید/فروش/پرداخت/بانک/کاردکس/طرف حساب/گزارش‌ها + قالب‌های چاپ فاکتور) و عمومی (بلاگ، مقاله، پیگیری، نمودار قیمت محصول). داشبورد: بک‌اند `dashboard/views.py` حالا `day`/`month` را ISO می‌فرستد و فرانت با `dailyChart`+`label` شمسی رندر می‌کند. inputهای `type=date` میلادی می‌مانند (native picker)
- **اجبار دسترسی نقش‌ها (RBAC واقعی)**: ۴ کد جدید (`sale_edit`، `purchase_edit`، `payment_edit`، `accounts_edit`) در `users/models.py`؛ helper `_has_perm` در `accounting/views.py` + چک روی ۲۹ متد ویو (view/create/edit جدا)؛ backfill نقش‌های موجود با shell (ادمین ۲۰، فروشنده/حسابدار/مدیر فروش به‌روز شدند). فرانت: هوک `usePermissions`، فیلتر منو بر اساس `perm` در Header/Layout، مخفی‌سازی دکمه‌های ویرایش/حذف/ایجاد در PaymentsPage/Purchase/Sale/Banks. تست ۴۰۳ با نقش محدود ✓
- **ویرایش اسناد (بک‌اند+فرانت)**: فاکتور خرید (PATCH کامل: سرفاکتور همیشه، آیتم‌ها فقط در ordered با برگشت/اعمال موجودی و کاردکس ADJUSTMENT)، فاکتور فروش (سرفاکتور در draft/confirmed، آیتم‌ها فقط manual با چک موجودی)، دریافت/پرداخت (`payments/` GET list + `payments/<pk>/` و `sale-payments/<pk>/` GET/PATCH/DELETE + بازمحاسبه وضعیت فاکتور). فرانت: دکمه «ویرایش فاکتور» در جزئیات خرید/فروش (reuse فرم New با prop `editing`)، ویرایش/حذف تراکنش در PaymentsPage و دریافت‌های فروش در SaleInvoicePage
- **مدیریت بانک** (`/admin/banks` + `AdminBanksPage.jsx`): ساخت/ویرایش/حذف حساب (روی مدل Account موجود)، حذف فقط بدون تراکنش، مودال تراکنش‌های هر حساب (`accounts/<pk>/transactions/` — ترکیب Payment + SalePayment + خلاصه). آیتم «بانک» در adminMenu
- **واحد پول**: «تومان»/«ت» → «ریال» در صفحات خرید/فروش/پرداخت (¥ دست‌نخورده)
- **فیکس‌ها**: `/accounting/customer-search/` (قبلاً ۴۰۴)، منوی موبایل بعد از ناوبری باز می‌ماند ← `<AnimatePresence key={location.pathname}>` + کلید exit در واریانت‌ها، حذف FAB زرد و نوار راهنمای ادمین در موبایل، حذف صفحه راهنمای انتخاب و آیتم‌های لنز/برد/سنسور از منو، ریسپانسیو بلاگ موبایل، safe-area هدر PWA (`pt-safe`/`pb-safe`)، دکمه چشم رمز (`PasswordInput`)، حذف `SessionAuthentication` از DRF (لاگین با سشن ادمین ۴۰۳ می‌شد)، آیکون‌های PWA با لوگوی جدید DOORBINKAR
- **هشدار تکراری**: کش Vite چندبار خراب شد (صفحه سفید/ماژول خالی) ← `rm -rf node_modules/.vite` + ری‌استارت

## وضعیت فعلی (انجام‌شده)
- **دیزاین‌سیستم «SENTINEL»** — مشکی/زرد با زبان بصری اتاق مانیتورینگ CCTV:
  - رنگ برند: طلایی (#FBC02D دارک / #A16207 لایت) روی مشکی (#0A0A0B) یا سفید گرم (#FAF8F3)
  - **تم دارک + لایت**: توکن‌ها در `index.css` زیر `:root` (دارک) و `[data-theme="light"]`؛ موتور تعویض `data-theme` روی `<html>` است
  - `useThemeStore` (zustand persist، کلید `site-theme`) + `applyTheme` + بوت اسکریپت در `index.html` (ضد FOUC) + پارامتر `?theme=light|dark` برای تست
  - دکمه تعویض تم در هدر: `components/layout/header/ThemeToggle.jsx`
  - **نام کلاس‌ها عوض نشده** (`btn-gold`, `gold-text`, `--gradient-gold`, `text-gold`...)؛ tailwind.config رنگ‌ها را var-driven کرده (`rgb(var(--color-brand-rgb) / <alpha-value>)`) پس `bg-brand/20` و... در هر دو تم درست کار می‌کند
  - افکت‌های CCTV در index.css: `.hud-frame`/`.hud-corners` (براکت ویوفایندر)، `.scanline` (جاروی دوربین)، `.rec-dot` (REC چشمک‌زن)، `.lens-rings`، `.grid-bg`
- **HomePage بازنویسی کامل**: هیروی «هاب هوشمند» — تیتر متمرکز + **SmartSearch** (`components/home/SmartSearch.jsx`): باکس دو حالته «جستجوی قطعه / پرسش از ربات مشاور» با چیپ‌های پیشنهادی؛ ربات سوال را تحلیل (قطعه/برند/مگاپیکسل/کاربرد، تبدیل اعداد فارسی) و با endpoint جستجوی هوشمند محصولات مچ + نکته فنی فارسی برمی‌گرداند. کارت‌های معرفی ۳ ویژگی (سرچ پیشرفته، ربات مشاور، مچ قطعات) زیر باکس. **سرچ از هدر حذف شد** (SearchBox/MobileMenu sheet/⌘K حذف — فایل SearchBox.jsx بلااستفاده).
- **فیکس بک‌اند**: `ProductListView.search_fields` و `ProductSearchView` به فیلد ناموجود `chipset` ارجاع می‌دادند و کل سرچ ۵۰۰ می‌شد ← با `board_name`/`sensor_name`/`lens_name`/`keywords` درست شد (سرچ صفحه محصولات هم تعمیر شد).
- **ربات دو لایه**: اول پاسخ محلی rule-based؛ اگر مطمئن نبود → `POST /api/catalog/assistant/ask/` (catalog/views.py `AssistantAskView`) که با LLM سازگار-OpenAI جواب می‌ده + کانتکست کاتالوگ. تنظیمات: `AI_API_KEY`/`AI_API_BASE`/`AI_API_MODEL` در .env (پیش‌فرض Moonshot: `https://api.moonshot.cn/v1` + `moonshot-v1-8k`). بدون کلید یا خطای سرویس → fallback امن فارسی. پاسخ AI در فرانت با بج «AI» مشخص می‌شود.
- **داشبورد Power BI** (`DashboardPage.jsx` بازنویسی): KPI با آیکون و درصد تغییر ماه، روند فروش ۳۰ روز (Area)، دونات وضعیت سفارش‌ها، فروش دسته‌ای (Bar)، ۵ محصول برتر (Bar افقی)، وضعیت مالی (میله‌های مقایسه‌ای)، سلامت انبار، آخرین سفارشات. بک‌اند stats گسترش یافت: `daily_sales`, `prev_month_sales`, `orders_by_status`, `top_products`, `sales_by_category`. **نکته recharts v3**: نمودارها نباید پشت لودینگ‌گیت مونت شوند (گرافیک رندر نمی‌شود) و `isAnimationActive={false}` لازم است — دیتا با مقادیر پیش‌فرض خالی شروع و با رسیدن کوئری پر می‌شود.
- **مدیریت پرسنل**: کلیک روی نام → مودال ویرایش کامل (نام/موبایل/نقش/رمز...) — بک‌اند `StaffDetailView.patch` همه را پشتیبانی می‌کند
- **مدیریت محصولات از فرانت**: endpoint ادمین `GET/PATCH /api/catalog/products/admin/<pk>/` (`ProductAdminDetailView`) + صفحه `/admin/products` (`AdminProductsPage.jsx`) — جدول با جستجو، کلیک روی نام → مودال ویرایش گروه‌بندی‌شده (اصلی/برد/سنسور/لنز/مودم/بدنه/SEO/وضعیت). فیلدهای choice مدل به‌صورت select با همان گزینه‌های بک‌اند. گروه‌ها بر اساس `category_type` فیلتر می‌شوند (`SPEC_GROUPS_BY_TYPE`).
- **مدیریت دسته‌بندی + ویژگی داینامیک**: صفحه `/admin/categories` (`AdminCategoriesPage.jsx`) — ساخت/حذف دسته (حذف دسته دارای محصول رد می‌شود) + افزودن/حذف «ویژگی سفارشی» (متن/select/تیک) برای هر دسته. بک‌اند: مدل `CategorySpecField` + فیلد `Product.dynamic_specs` (JSONField، migration 0013) + endpointهای `categories/admin/` و `spec-fields/`. مقدارها در مودال ویرایش محصول (گروه «ویژگی‌های سفارشی») پر و در `get_specs` صفحه محصول برای مشتری نمایش داده می‌شوند.
- لاگین ادمین: `09000000001` / `admin123456` (موقت — عوضش کنید)

## ران کردن
```bash
cd cctv_shop && venv/bin/python manage.py runserver 8000        # بک‌اند
cd cctv_frontend && npm run dev                                  # فرانت → http://localhost:3000
```
صفحه سفید دیدی؟ → ری‌استارت Vite + `rm -rf node_modules/.vite`
اسکرین‌شات تست: `google-chrome --headless=new ... "http://localhost:3000/?theme=light"` (skill: visual-check)

## قدم‌های بعدی (به ترتیب اولویت)
1. **دیپلوی امن**: `.env` پروداکشن — DEBUG=False، SECRET_KEY قوی، PostgreSQL (`USE_POSTGRES=True`)، ALLOWED_HOSTS واقعی؛ سپس build نهایی و سرو dist
2. **پولیش صفحه جزئیات محصول** (`pages/ProductDetailPage.jsx`)
3. گسترش toast/آیکون‌ها به بقیه صفحات ادمین (فاکتورها، کاردکس)

## نکات مهم بک‌اند (دست نخورده)
- JWT access token یک‌روزه؛ لاگین با موبایل (فیلد `username` در API)
- `core/0002_initial` در DB اعمال ولی فایلش حذف شده (drift — مواظب makemigrations روی core باش)
- ابزارهای خطرناک: `apps/accounting/admin_tools.py` (system reset) — فقط با درخواست صریح
