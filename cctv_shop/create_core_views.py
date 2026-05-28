with open('apps/core/views.py', 'w', encoding='utf-8') as f:
    f.write("""from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import SiteSettings, StaticPage


class SiteSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        s = SiteSettings.get_instance()
        return Response({
            'site_name': s.site_name,
            'contact_phone': s.contact_phone,
            'contact_email': s.contact_email,
            'contact_address': s.contact_address,
            'working_hours': s.working_hours,
            'whatsapp_number': s.whatsapp_number,
            'bale_username': s.bale_username,
            'eitaa_username': s.eitaa_username,
            'telegram_username': s.telegram_username,
            'instagram_username': s.instagram_username,
            'about_us_text': s.about_us_text,
            'bank_accounts': s.bank_accounts,
            'site_logo': s.site_logo.url if s.site_logo else None,
        })


class StaticPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, key):
        try:
            page = StaticPage.objects.get(key=key)
            return Response({'title': page.title, 'content': page.content})
        except StaticPage.DoesNotExist:
            return Response({'title': '', 'content': ''})
""")
print("done")
