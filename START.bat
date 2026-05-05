@echo off
chcp 65001 > nul
title راه‌اندازی فروشگاه دوربین

echo.
echo ================================================
echo   راه‌اندازی و اجرای پروژه
echo ================================================
echo.

REM -- BACKEND --
cd cctv_shop

if not exist venv (
    echo [1/5] ساخت محیط مجازی Python...
    python -m venv venv
) else (
    echo [1/5] محیط مجازی موجود است
)

echo [2/5] فعال‌سازی محیط مجازی...
call venv\Scripts\activate.bat

echo [3/5] نصب پکیج‌های Python...
pip install -r requirements.txt -q --disable-pip-version-check

echo [4/5] آماده‌سازی دیتابیس...
python manage.py migrate --run-syncdb 2>nul
python manage.py migrate

echo [5/5] ساخت کاربر ادمین (اگر وجود نداشت)...
echo from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.filter(email='admin@cctv.ir').exists() or U.objects.create_superuser('admin@cctv.ir','admin1234') | python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); U.objects.filter(email='admin@cctv.ir').exists() or U.objects.create_superuser('admin@cctv.ir','admin1234')" 2>nul

cd ..

REM -- FRONTEND --
cd cctv_frontend

if not exist node_modules (
    echo.
    echo [6/6] نصب پکیج‌های React (چند دقیقه طول می‌کشد)...
    npm install --legacy-peer-deps
) else (
    echo [6/6] پکیج‌های React موجود هستند
)

cd ..

echo.
echo ================================================
echo   شروع سرورها...
echo ================================================
echo.

start "Django - Backend" cmd /k "cd cctv_shop && call venv\Scripts\activate && python manage.py runserver && pause"
timeout /t 3 /nobreak > nul
start "React - Frontend" cmd /k "cd cctv_frontend && npm run dev && pause"

echo.
echo ================================================
echo.
echo   فرانت‌اند:   http://localhost:3000
echo   پنل ادمین:  http://localhost:8000/admin
echo.
echo   ایمیل ادمین: admin@cctv.ir
echo   رمز ادمین:   admin1234
echo.
echo ================================================
echo.
timeout /t 5 /nobreak > nul
start http://localhost:3000
