with open('config/urls.py', encoding='utf-8') as f:
    content = f.read()

print("before:", 'education' in content)

if 'education' not in content:
    # اضافه کردن بعد از api/notifications
    content = content.replace(
        "path('api/notifications/",
        "path('api/education/', include('apps.education.urls')),\n    path('api/notifications/"
    )
    # اگر notifications نبود، بعد از accounting اضافه کن
    if 'education' not in content:
        content = content.replace(
            "path('api/accounting/",
            "path('api/education/', include('apps.education.urls')),\n    path('api/accounting/"
        )

with open('config/urls.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("after:", 'education' in content)
print("done — restart server")
