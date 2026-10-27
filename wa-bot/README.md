# wa-bot — ربات پاسخگوی واتساپ (Baileys + Gemini)

## ساختار
```
wa-bot/
├── package.json
├── .env                  # GEMINI_API_KEY و تنظیمات (از .env.example کپی کن)
├── src/
│   ├── index.js          # نقطه شروع؛ اکانت‌های فعال را از دیتابیس می‌خواند
│   ├── igWebhook.js      # وب‌هوک اینستاگرام (Messaging API): پاسخ خودکار دایرکت با Gemini،
│   │                     # دروازه فالو (ig_gate.json) و کامنت→دایرکت با کلیدواژه (ig_keywords.json)؛
│   │                     # سرویس ig-bot روی 127.0.0.1:3100 — از طریق ig-link (تونل SSH معکوس) و
│   │                     # nginx روی VPS میانی با دامنه sslip.io به اینترنت منتشر می‌شود
│   ├── sessionManager.js # اتصال Baileys، QR، صف پاسخ، تأخیر شبه‌انسانی ۳-۷ ثانیه
│   ├── gemini.js         # فراخوانی Gemini 2.5 Flash با پرامپت + حافظه مکالمه
│   └── db.js             # SQLite: اکانت‌ها + تاریخچه مکالمات (data/bot.db)
├── scripts/
│   ├── add-account.js    # افزودن اکانت
│   ├── list-accounts.js  # لیست اکانت‌ها
│   └── set-prompt.js     # تنظیم پرامپت اختصاصی هر اکانت
├── prompts/doorbinkar.txt# پرامپت نمونه فروشگاه
├── sessions/<id>/        # نشست هر اکانت (خودکار ساخته می‌شود)
└── data/bot.db           # دیتابیس (خودکار)
```

## راه‌اندازی
```bash
cd ~/wa-bot
cp .env.example .env && nano .env     # کلید جمینای را بگذار
npm install
npm run add-account -- acc1 "فروشگاه دوربینکار"
npm run set-prompt -- acc1 prompts/doorbinkar.txt
sudo cp wa-bot.service /etc/systemd/system/ && sudo systemctl enable --now wa-bot
journalctl -u wa-bot -f               # QR را ببین و با واتساپ اسکن کن
```

## نکات
- QR هر اکانت در لاگ چاپ می‌شود؛ در واتساپ: «دستگاه‌های متصل ← اتصال دستگاه».
- برای اکانت دوم/سوم همان add-account با id جدید (acc2, acc3) و `systemctl restart wa-bot`.
- اگر اکانتی logout شد: `rm -rf sessions/<id>` و ری‌استارت سرویس تا QR تازه بدهد.
- گروه‌ها پیش‌فرض نادیده گرفته می‌شوند (REPLY_GROUPS=true برای فعال‌سازی).
- هر مکالمه فقط ۲۰ پیام آخر را به Gemini می‌فرستد (data/bot.db).
