"""
apps/chat/views.py
──────────────────
API چت مشتری ↔ پرسنل:
  مشتری:  GET/POST /api/chat/mine/          — گفتگو و پیام‌های خودش + ارسال
          GET      /api/chat/mine/unread/   — تعداد خوانده‌نشده (بج ویدجت)
  پرسنل:  GET      /api/chat/conversations/ — لیست گفتگوها با بج
          GET/POST /api/chat/conversations/<id>/messages/ — رشته + پاسخ
          POST     /api/chat/conversations/<id>/close/    — بستن/باز کردن
"""
import os

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.views import _has_staff_perm

from .models import ChatMessage, Conversation

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # ۱۰ مگابایت
ALLOWED_EXTS = {
    "jpg", "jpeg", "png", "webp", "gif",
    "pdf", "zip", "rar", "txt", "doc", "docx", "xls", "xlsx",
}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}


def _forbidden():
    return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)


def _chat_staff_users():
    """کاربران واجد دریافت چت — سوپریوزرها + پرسنل فعال با پرمیشن chat_reply."""
    from django.contrib.auth import get_user_model
    from apps.users.models import StaffProfile
    U = get_user_model()
    ids = set(U.objects.filter(is_superuser=True, is_active=True).values_list("id", flat=True))
    for sp in StaffProfile.objects.filter(is_active=True).select_related("role", "user"):
        if sp.user.is_active and sp.has_perm("chat_reply"):
            ids.add(sp.user_id)
    return U.objects.filter(id__in=ids)


def _visible_conversations(user):
    """گفتگوهای قابل‌مشاهده — سوپریوزر همه را (نظارت)؛ پرسنل فقط اختصاص‌یافته به خودش + عمومی."""
    qs = Conversation.objects.all()
    if user.is_superuser:
        return qs
    return qs.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))


def _message_payload(m, request):
    att_url = None
    is_image = False
    if m.attachment:
        att_url = request.build_absolute_uri(m.attachment.url)
        ext = (m.attachment_name or m.attachment.name).rsplit(".", 1)[-1].lower()
        is_image = ext in IMAGE_EXTS
    return {
        "id": m.id,
        "from_staff": m.from_staff,
        "text": m.text,
        "attachment_url": att_url,
        "attachment_name": m.attachment_name,
        "is_image": is_image,
        "sender_name": (m.sender.get_full_name() or str(m.sender.phone)) if m.sender else "-",
        "created_at": timezone.localtime(m.created_at).isoformat(),
    }


def _validate_upload(request):
    """متن و/یا فایل — حداقل یکی؛ فایل: پسوند و حجم مجاز. در خطا Response برمی‌گرداند."""
    text = (request.data.get("text") or "").strip()
    f = request.FILES.get("attachment")
    if not text and not f:
        return None, None, Response({"error": "متن یا فایل پیام خالی است"}, status=400)
    if f:
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ALLOWED_EXTS:
            return None, None, Response({"error": f"فرمت «{ext or 'نامشخص'}» مجاز نیست"}, status=400)
        if f.size > MAX_UPLOAD_BYTES:
            return None, None, Response({"error": "حجم فایل بیشتر از ۱۰ مگابایت است"}, status=400)
    return text, f, None


def _create_message(conversation, sender, from_staff, text, f):
    msg = ChatMessage.objects.create(
        conversation=conversation, sender=sender, from_staff=from_staff,
        text=text or "",
        attachment=f or None,
        attachment_name=f.name if f else "",
    )
    Conversation.objects.filter(pk=conversation.pk).update(
        updated_at=timezone.now(),
        is_closed=False if not from_staff else conversation.is_closed,
    )
    return msg


# ─── سمت مشتری ─────────────────────────────────────────────────

class StaffListView(APIView):
    """GET /api/chat/staff-list/ — پرسنلی که مشتری می‌تواند برای گفتگو انتخاب کند."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        out = []
        for u in _chat_staff_users():
            sp = getattr(u, "staff_profile", None)
            out.append({
                "id": u.id,
                "name": u.get_full_name() or str(u.phone),
                "role": (sp.role.name if sp and sp.role else ("مدیر سیستم" if u.is_superuser else "")),
            })
        out.sort(key=lambda x: (not x["name"]))
        return Response(out)


class MyChatAssignView(APIView):
    """POST /api/chat/mine/assign/ — انتخاب/تغییر پرسنل گفتگو: {"assigned_to": id یا null}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conv, _ = Conversation.objects.get_or_create(customer=request.user)
        target = request.data.get("assigned_to")
        if target in (None, "", 0):
            conv.assigned_to = None
        else:
            user = _chat_staff_users().filter(pk=target).first()
            if user is None:
                return Response({"error": "پرسنل انتخاب‌شده معتبر نیست"}, status=400)
            conv.assigned_to = user
        conv.save(update_fields=["assigned_to", "updated_at"])
        name = conv.assigned_to.get_full_name() if conv.assigned_to else None
        return Response({"assigned_to": conv.assigned_to_id, "assigned_to_name": name})


class MyChatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conv, _ = Conversation.objects.get_or_create(customer=request.user)
        qs = conv.messages.select_related("sender")
        after = request.query_params.get("after_id")
        if after and after.isdigit():
            qs = qs.filter(id__gt=int(after))
            msgs = list(qs[:200])
        else:
            msgs = list(qs.order_by("-id")[:50])[::-1]
        # پیام‌های پرسنل خوانده شد
        conv.messages.filter(from_staff=True, is_read=False).update(is_read=True)
        return Response({
            "conversation_id": conv.id,
            "is_closed": conv.is_closed,
            "assigned_to": conv.assigned_to_id,
            "assigned_to_name": (conv.assigned_to.get_full_name() or str(conv.assigned_to.phone)) if conv.assigned_to else None,
            "messages": [_message_payload(m, request) for m in msgs],
        })

    def post(self, request):
        conv, _ = Conversation.objects.get_or_create(customer=request.user)
        text, f, err = _validate_upload(request)
        if err:
            return err
        with transaction.atomic():
            msg = _create_message(conv, request.user, from_staff=False, text=text, f=f)
        return Response(_message_payload(msg, request), status=201)


class MyChatUnreadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conv = Conversation.objects.filter(customer=request.user).first()
        n = conv.messages.filter(from_staff=True, is_read=False).count() if conv else 0
        return Response({"unread": n})


# ─── سمت پرسنل ─────────────────────────────────────────────────

class ChatUserSearchView(APIView):
    """GET /api/chat/user-search/?q= — جستجوی مشتری برای شروع گفتگو توسط پرسنل."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_staff_perm(request.user, "chat_view"):
            return _forbidden()
        from django.contrib.auth import get_user_model
        q = request.query_params.get("q", "")
        q = q.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        q = q.replace("ك", "ک").replace("ي", "ی").strip()
        if len(q) < 2:
            return Response([])
        U = get_user_model()
        # همه کاربران فعال — هم مشتری هم پرسنل (چت پرسنل‌به‌پرسنل هم پشتیبانی می‌شود)
        users = (U.objects.filter(is_active=True)
                 .filter(Q(phone__icontains=q) | Q(first_name__icontains=q)
                         | Q(last_name__icontains=q) | Q(profile__company_name__icontains=q))
                 .select_related("profile", "staff_profile", "staff_profile__role")[:10])
        out = []
        for u in users:
            sp = getattr(u, "staff_profile", None)
            is_personnel = u.is_staff or u.is_superuser or bool(sp)
            out.append({
                "id": u.id,
                "name": u.get_full_name() or str(u.phone),
                "phone": str(u.phone),
                "is_staff": is_personnel,
                "role": (sp.role.name if sp and sp.role else ("مدیر سیستم" if u.is_superuser else "")) if is_personnel else "",
            })
        return Response(out)


class ConversationStartView(APIView):
    """POST /api/chat/conversations/start/ — شروع گفتگو با یک کاربر (مشتری یا پرسنل) توسط پرسنل.
    بدنه: user_id + متن و/یا فایل. اگر مقصد پرسنل باشد یا آغازکننده سوپریوزر نباشد، گفتگو به
    آغازکننده اختصاص می‌یابد تا خصوصی بماند؛ مقصد پرسنل از تب «پرسنل» چت‌باکس خودش پاسخ می‌دهد."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not _has_staff_perm(request.user, "chat_reply"):
            return _forbidden()
        from django.contrib.auth import get_user_model
        customer = get_user_model().objects.filter(pk=request.data.get("user_id")).first()
        if customer is None:
            return Response({"error": "کاربر یافت نشد"}, status=404)
        target_is_staff = (customer.is_staff or customer.is_superuser
                           or hasattr(customer, "staff_profile"))
        text, f, err = _validate_upload(request)
        if err:
            return err
        with transaction.atomic():
            conv, created = Conversation.objects.get_or_create(customer=customer)
            if conv.assigned_to_id is None and (target_is_staff or not request.user.is_superuser):
                conv.assigned_to = request.user
                conv.save(update_fields=["assigned_to", "updated_at"])
            msg = _create_message(conv, request.user, from_staff=True, text=text, f=f)
        name = customer.get_full_name() or str(customer.phone)
        return Response({
            "conversation_id": conv.id,
            "customer_name": name,
            "is_closed": conv.is_closed,
            "assigned_to": conv.assigned_to_id,
            "created": created,
            "message": _message_payload(msg, request),
        }, status=201)


class ConversationListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_staff_perm(request.user, "chat_view"):
            return _forbidden()
        convs = (_visible_conversations(request.user)
                 .select_related("customer", "customer__profile", "customer__profile__linked_contact", "assigned_to")
                 .annotate(unread=Count("messages", filter=Q(messages__from_staff=False, messages__is_read=False)))
                 .order_by("-unread", "-updated_at")[:100])
        out = []
        for c in convs:
            last = c.messages.order_by("-id").first()
            cust = c.customer
            prof = getattr(cust, "profile", None)
            name = cust.get_full_name() or (prof.linked_contact.name if prof and prof.linked_contact_id else "") or str(cust.phone)
            out.append({
                "id": c.id,
                "customer_name": name,
                "customer_phone": str(cust.phone),
                "is_closed": c.is_closed,
                "unread": c.unread,
                "assigned_to": c.assigned_to_id,
                "assigned_to_name": (c.assigned_to.get_full_name() or str(c.assigned_to.phone)) if c.assigned_to else None,
                "last_text": (last.text[:60] or f"📎 {last.attachment_name}") if last else "",
                "last_from_staff": last.from_staff if last else None,
                "last_at": timezone.localtime(last.created_at).isoformat() if last else None,
            })
        return Response(out)


class ConversationMessagesView(APIView):
    permission_classes = [IsAdminUser]

    def _get_visible(self, request, pk):
        return _visible_conversations(request.user).filter(pk=pk).first()

    def get(self, request, pk):
        if not _has_staff_perm(request.user, "chat_view"):
            return _forbidden()
        conv = self._get_visible(request, pk)
        if conv is None:
            return Response({"error": "گفتگو یافت نشد"}, status=404)
        msgs = list(conv.messages.select_related("sender").order_by("-id")[:100])[::-1]
        conv.messages.filter(from_staff=False, is_read=False).update(is_read=True)
        return Response({
            "conversation_id": conv.id,
            "is_closed": conv.is_closed,
            "assigned_to": conv.assigned_to_id,
            "assigned_to_name": (conv.assigned_to.get_full_name() or str(conv.assigned_to.phone)) if conv.assigned_to else None,
            "messages": [_message_payload(m, request) for m in msgs],
        })

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "chat_reply"):
            return _forbidden()
        conv = self._get_visible(request, pk)
        if conv is None:
            return Response({"error": "گفتگو یافت نشد"}, status=404)
        text, f, err = _validate_upload(request)
        if err:
            return err
        with transaction.atomic():
            msg = _create_message(conv, request.user, from_staff=True, text=text, f=f)
            # پاسخ به گفتگوی عمومی = گرفتن مالکیت آن (سوپریوزر فقط نظارت می‌کند و مالکیت نمی‌گیرد)
            if conv.assigned_to_id is None and not request.user.is_superuser:
                Conversation.objects.filter(pk=conv.pk).update(assigned_to=request.user)
        return Response(_message_payload(msg, request), status=201)


class ConversationCloseView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "chat_reply"):
            return _forbidden()
        conv = _visible_conversations(request.user).filter(pk=pk).first()
        if conv is None:
            return Response({"error": "گفتگو یافت نشد"}, status=404)
        conv.is_closed = not conv.is_closed
        conv.save(update_fields=["is_closed", "updated_at"])
        return Response({"id": conv.id, "is_closed": conv.is_closed})
