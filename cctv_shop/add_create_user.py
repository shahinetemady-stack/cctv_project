import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

new_view = '''

class StaffCreateUserView(APIView):
    """POST /api/accounting/staff/create-user/ — ساخت کاربر جدید برای پرسنل"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.users.models import User
        d = request.data
        phone = d.get('phone', '').strip()
        password = d.get('password', '').strip()

        if not phone:
            return Response({'error': 'شماره موبایل الزامی است'}, status=400)
        if not password or len(password) < 6:
            return Response({'error': 'رمز عبور باید حداقل ۶ کاراکتر باشد'}, status=400)
        if User.objects.filter(phone=phone).exists():
            return Response({'error': 'این شماره موبایل قبلاً ثبت شده'}, status=400)

        try:
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=d.get('first_name', ''),
                last_name=d.get('last_name', ''),
                is_staff=True,
            )
            full_name = user.get_full_name() or phone
            return Response({
                'user_id': user.id,
                'name': full_name,
                'phone': phone,
                'message': f'کاربر {full_name} ساخته شد',
            }, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
'''

if 'StaffCreateUserView' not in content:
    content += new_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ StaffCreateUserView اضافه شد")
else:
    print("قبلاً موجود بود")

# اضافه کردن URL
urls_path = os.path.join('apps', 'accounting', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'create-user' not in urls:
    urls = urls.replace(
        "path('staff/<int:pk>/', views.StaffDetailView.as_view()),",
        "path('staff/<int:pk>/', views.StaffDetailView.as_view()),\n    path('staff/create-user/', views.StaffCreateUserView.as_view()),"
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL create-user اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
