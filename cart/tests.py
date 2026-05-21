from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from orders.models import Order, OrderItem, DeliverySlot
from products.models import Product
from sellers.models import SellerProfile
from contact.models import ContactSettings
from cart.models import Cart, CartItem
from rest_framework.test import APITestCase
from rest_framework import status
import datetime

User = get_user_model()

class CartCheckoutSlotValidationTests(APITestCase):
    def setUp(self):
        # Create a user
        self.customer = User.objects.create_user(
            username="customer_cart@example.com",
            email="customer_cart@example.com",
            password="password123",
            role="CUSTOMER"
        )
        self.client.force_authenticate(user=self.customer)

        # Create Seller profile
        self.seller_user = User.objects.create_user(
            username="seller_cart@example.com",
            email="seller_cart@example.com",
            password="password123",
            role="SELLER"
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller_user,
            business_name="Seller Shop Cart",
            is_approved=True
        )

        # Create product
        self.product = Product.objects.create(
            name="Super Battery Cart",
            price=100.00,
            stock=10,
            seller=self.seller_profile
        )

        # Create contact settings
        self.contact_settings = ContactSettings.objects.create(
            company_name="Battery Inc Cart",
            support_email="support@batterycart.com",
            support_phone="1800-999-7777",
            address="123 Street",
            support_hours="9 AM - 6 PM"
        )

        # Setup cart
        self.cart = Cart.objects.create(user=self.customer)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )

    def test_cart_checkout_successful_booking(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560005"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=2
        )

        payload = {
            "delivery_date": str(slot_date),
            "delivery_time": slot_time,
            "shipping_address": f"Flat 101, Bangalore, Pincode: {pincode}",
            "billing_address": "Same"
        }

        response = self.client.post(f"/api/cart/carts/{self.cart.id}/checkout/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify slot current_bookings incremented
        slot.refresh_from_db()
        self.assertEqual(slot.current_bookings, 1)

    def test_cart_checkout_duplicate_booking_prevention(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560006"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=1
        )

        # Book first time by creating order directly
        order = Order.objects.create(
            user=self.customer,
            shipping_address=f"Flat 101, Bangalore, Pincode: {pincode}",
            billing_address="Same",
            delivery_date=slot_date,
            delivery_time=slot_time,
            subtotal=100.0,
            tax=18.0,
            discount=0.0,
            shipping_fee=0.0,
            grand_total=118.0
        )
        slot.current_bookings = 1
        slot.save()

        # Checkout the cart (should fail because max_bookings=1)
        payload = {
            "delivery_date": str(slot_date),
            "delivery_time": slot_time,
            "shipping_address": f"Flat 101, Bangalore, Pincode: {pincode}",
            "billing_address": "Same"
        }
        response = self.client.post(f"/api/cart/carts/{self.cart.id}/checkout/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This delivery/installation slot is already booked for your area", response.data['error'])
        self.assertEqual("1800-999-7777", response.data['support_phone'])
        self.assertEqual("For assistance or urgent bookings, please contact Customer Support.", response.data['support_message'])
