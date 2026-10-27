from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders.models import Cart
from apps.users.models import User


class CheckoutShippingMethodTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09124000001", password="test-pass")
        Cart.objects.create(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_post_shipping_is_rejected(self):
        response = self.client.post(
            "/api/orders/cart/checkout/", {"shipping_method": "post"}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("غیرفعال", response.data["error"])

    def test_courier_and_freight_pass_shipping_validation(self):
        for method in ("courier", "freight"):
            with self.subTest(method=method):
                response = self.client.post(
                    "/api/orders/cart/checkout/", {"shipping_method": method}, format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("غیرفعال", response.data["error"])
