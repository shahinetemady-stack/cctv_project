# CCTV Shop Backend — راهنمای راه‌اندازی

## ساختار پروژه

```
cctv_shop/
├── config/                 # تنظیمات Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/               # مدل‌های پایه (abstract)
│   ├── users/              # کاربران، پروفایل، OTP
│   ├── catalog/            # محصولات، دسته‌بندی، نرخ ارز
│   ├── orders/             # سفارش، سبد خرید، رزرو موجودی
│   ├── inventory/          # حرکات موجودی، هشدار موجودی کم
│   └── notifications/      # لاگ پیامک و ایمیل
├── .env.example
├── requirements.txt
└── manage.py
```

## نصب و راه‌اندازی

```bash
# ۱. کلون و venv
git clone <repo>
cd cctv_shop
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# ۲. نصب پکیج‌ها
pip install -r requirements.txt

# ۳. تنظیم متغیرهای محیطی
cp .env.example .env
# .env را با مقادیر واقعی پر کنید

# ۴. ساخت دیتابیس PostgreSQL
createdb cctv_shop_db

# ۵. اجرای migrations
python manage.py migrate

# ۶. ساخت superuser
python manage.py createsuperuser

# ۷. اجرای سرور
python manage.py runserver
```

## تنظیم Cron (هر ۱۵ دقیقه)

```bash
# باز کردن crontab
crontab -e

# اضافه کردن این خط:
*/15 * * * * /path/to/venv/bin/python /path/to/cctv_shop/manage.py release_expired_reservations >> /var/log/cctv_shop_cron.log 2>&1
```

## بررسی دستی
```bash
# اجرای دستی (بدون تغییر دیتابیس)
python manage.py release_expired_reservations --dry-run

# اجرای واقعی
python manage.py release_expired_reservations
```

## API Endpoints

### Catalog (عمومی)
| Method | URL | توضیح |
|--------|-----|-------|
| GET | `/api/catalog/categories/` | لیست دسته‌بندی‌ها |
| GET | `/api/catalog/products/` | لیست محصولات + فیلتر |
| GET | `/api/catalog/products/search/?q=` | جستجوی هوشمند |
| GET | `/api/catalog/products/<slug>/` | جزئیات محصول |
| GET | `/api/catalog/exchange-rate/` | نرخ ارز |
| PUT | `/api/catalog/exchange-rate/` | بروزرسانی نرخ (ادمین) |
| POST | `/api/catalog/products/bulk-upload/` | آپلود اکسل (ادمین) |

### Orders (احراز هویت لازم)
| Method | URL | توضیح |
|--------|-----|-------|
| GET/POST/DELETE | `/api/orders/cart/` | سبد خرید |
| POST | `/api/orders/cart/checkout/` | پرداخت مستقیم |
| GET/POST/DELETE | `/api/orders/inquiry-cart/` | سبد استعلام |
| POST | `/api/orders/inquiry-cart/submit/` | ثبت استعلام |
| GET | `/api/orders/` | سفارش‌های من |
| GET | `/api/orders/<order_number>/` | جزئیات سفارش |
| POST | `/api/orders/<order_number>/cancel/` | کنسل سفارش |
| POST | `/api/orders/admin/orders/` | همه سفارش‌ها (ادمین) |
| POST | `/api/orders/admin/<order_number>/confirm/` | تأیید استعلام (ادمین) |
| POST | `/api/orders/payment/callback/` | callback درگاه |

### فیلترهای پیشرفته محصول
```
GET /api/catalog/products/?part_type=sensor&chipset=sony&voltage=12V&lens_mount=m12&in_stock=true
```

## فرمول قیمت
```
final_price = (purchase_price_usd × rate_usd_to_irt) + shipping_cost + profit_margin
```
نرخ ارز از پنل ادمین → ExchangeRateSetting (singleton)

## فرآیند استعلام همکار
```
مشتری: افزودن به سبد استعلام
  ↓
POST /api/orders/inquiry-cart/submit/
  ↓ پیامک به ادمین + کاربر (مرحله ۲)
ادمین: POST /api/orders/admin/<order>/confirm/ {confirmed_amount: ...}
  ↓ رزرو موجودی ۲ ساعته + پیامک لینک پرداخت به مشتری (مرحله ۴)
مشتری: پرداخت → callback → PAID → کسر موجودی
```
