from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import Role, StaffProfile, User, UserProfile


class PartnerRequestPermissionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            phone="09123000001", password="test-pass", is_staff=True,
        )
        self.role = Role.objects.create(
            name="Partner approver", permissions=["partner_approve"],
        )
        StaffProfile.objects.create(user=self.staff, role=self.role)
        self.client = APIClient()
        self.client.force_authenticate(self.staff)
        self.pending = User.objects.create_user(
            phone="09123000002", password="test-pass", first_name="Pending",
        )
        self.pending_profile = UserProfile.objects.create(
            user=self.pending, user_type=UserProfile.UserType.PARTNER,
        )

    def test_partner_approve_can_list_all_pending_requests(self):
        other_pending = User.objects.create_user(
            phone="09123000003", password="test-pass", first_name="Other",
        )
        UserProfile.objects.create(
            user=other_pending, user_type=UserProfile.UserType.PARTNER,
        )
        approved = User.objects.create_user(
            phone="09123000004", password="test-pass", first_name="Approved",
        )
        UserProfile.objects.create(
            user=approved, user_type=UserProfile.UserType.PARTNER, is_approved=True,
        )
        public = User.objects.create_user(
            phone="09123000005", password="test-pass", first_name="Public",
        )
        UserProfile.objects.create(user=public, user_type=UserProfile.UserType.PUBLIC)

        response = self.client.get("/api/users/admin/partners/?pending=true")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            {row["user_id"] for row in response.data},
            {self.pending.id, other_pending.id},
        )

    def test_partner_approve_can_approve_request(self):
        with patch("apps.notifications.services.notify_partner_approved_sms"), \
                patch("django.core.mail.send_mail"):
            response = self.client.post(
                f"/api/users/admin/partners/{self.pending.id}/approve/",
                {"is_approved": True, "partner_tier": "silver"},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.pending_profile.refresh_from_db()
        self.assertTrue(self.pending_profile.is_approved)
        self.assertEqual(self.pending_profile.partner_tier, "silver")
        self.assertIsNotNone(self.pending_profile.approved_at)

    def test_partner_approve_is_required(self):
        self.role.permissions = []
        self.role.save(update_fields=["permissions"])

        list_response = self.client.get("/api/users/admin/partners/?pending=true")
        approve_response = self.client.post(
            f"/api/users/admin/partners/{self.pending.id}/approve/",
            {"is_approved": True, "partner_tier": "silver"},
            format="json",
        )
        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(approve_response.status_code, 403)
        self.pending_profile.refresh_from_db()
        self.assertFalse(self.pending_profile.is_approved)
