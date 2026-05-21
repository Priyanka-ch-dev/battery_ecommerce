from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Order, OrderItem, DeliverySlot, OrderTracking
from products.models import Product
from sellers.models import SellerProfile
from contact.models import ContactSettings
from rest_framework.test import APITestCase
from rest_framework import status
import datetime

User = get_user_model()

class DeliverySlotValidationTests(APITestCase):
    def setUp(self):
        # Create a user
        self.customer = User.objects.create_user(
            username="customer@example.com",
            email="customer@example.com",
            password="password123",
            role="CUSTOMER",
            phone_number="9988776655"
        )
        self.client.force_authenticate(user=self.customer)

        # Create Seller profile
        self.seller_user = User.objects.create_user(
            username="seller@example.com",
            email="seller@example.com",
            password="password123",
            role="SELLER"
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller_user,
            business_name="Seller Shop",
            status="APPROVED"
        )

        # Create product
        self.product = Product.objects.create(
            name="Super Battery",
            price=100.00,
            stock=10,
            seller=self.seller_profile
        )

        # Create contact settings
        self.contact_settings = ContactSettings.objects.create(
            company_name="Battery Inc",
            support_email="support@battery.com",
            support_phone="1800-999-8888",
            address="123 Street",
            support_hours="9 AM - 6 PM"
        )

    def test_successful_booking_increments_current_bookings(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560001"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=2
        )

        payload = {
            "product": self.product.id,
            "quantity": 1,
            "delivery_date": str(slot_date),
            "delivery_time": slot_time,
            "shipping_address": f"Flat 101, Bangalore, Pincode: {pincode}",
            "billing_address": "Same"
        }

        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify slot current_bookings incremented
        slot.refresh_from_db()
        self.assertEqual(slot.current_bookings, 1)

    def test_duplicate_booking_prevention(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560002"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=1
        )

        # Book first time
        payload = {
            "product": self.product.id,
            "quantity": 1,
            "delivery_date": str(slot_date),
            "delivery_time": slot_time,
            "shipping_address": f"Flat 101, Bangalore, Pincode: {pincode}",
            "billing_address": "Same"
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Book second time (should fail because max_bookings=1)
        response2 = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        error_msg = response2.data['error'][0] if isinstance(response2.data['error'], list) else response2.data['error']
        support_msg = response2.data['support_message'][0] if isinstance(response2.data['support_message'], list) else response2.data['support_message']
        support_phone = response2.data['support_phone'][0] if isinstance(response2.data['support_phone'], list) else response2.data['support_phone']
        self.assertIn("This delivery/installation slot is already booked for your area", error_msg)
        self.assertIn("For assistance or urgent bookings, please contact Customer Support.", support_msg)
        self.assertEqual("1800-999-8888", support_phone)

    def test_inactive_slot_booking_prevention(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560003"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=5,
            is_active=False
        )

        payload = {
            "product": self.product.id,
            "quantity": 1,
            "delivery_date": str(slot_date),
            "delivery_time": slot_time,
            "shipping_address": f"Flat 101, Bangalore, Pincode: {pincode}",
            "billing_address": "Same"
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_cancellation_decrements_bookings(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560004"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=1
        )

        payload = {
            "product": self.product.id,
            "quantity": 1,
            "delivery_date": str(slot_date),
            "delivery_time": slot_time,
            "shipping_address": f"Flat 101, Bangalore, Pincode: {pincode}",
            "billing_address": "Same"
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data['id']

        slot.refresh_from_db()
        self.assertEqual(slot.current_bookings, 1)

        # Cancel order
        order = Order.objects.get(id=order_id)
        order.status = Order.Status.CANCELLED
        order.save()

        slot.refresh_from_db()
        self.assertEqual(slot.current_bookings, 0)

    def test_check_availability_endpoint_unauthenticated(self):
        payload = {
            "pincode": "560099",
            "date": str(datetime.date.today() + datetime.timedelta(days=2)),
            "time_slot": "02:00 PM - 04:00 PM"
        }
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/orders/delivery-slots/check-availability/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_check_availability_endpoint_available(self):
        # By default, a non-existent slot is available
        payload = {
            "pincode": "560099",
            "date": str(datetime.date.today() + datetime.timedelta(days=2)),
            "time_slot": "02:00 PM - 04:00 PM"
        }
        # Authenticated customer user should be able to call this check endpoint
        self.client.force_authenticate(user=self.customer)
        response = self.client.post("/api/orders/delivery-slots/check-availability/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["available"])

    def test_check_availability_endpoint_unavailable_when_booked(self):
        slot_date = datetime.date.today() + datetime.timedelta(days=1)
        slot_time = "10:00 AM - 12:00 PM"
        pincode = "560005"

        slot = DeliverySlot.objects.create(
            date=slot_date,
            time_slot=slot_time,
            pincode=pincode,
            max_bookings=1,
            current_bookings=1
        )

        payload = {
            "pincode": pincode,
            "date": str(slot_date),
            "time_slot": slot_time
        }
        
        response = self.client.post("/api/orders/delivery-slots/check-availability/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["available"])
        self.assertEqual(response.data["error"], "This delivery/installation slot is already booked for your area. Please select another available time slot or contact Customer Support.")
        self.assertEqual(response.data["support_message"], "For assistance or urgent bookings, please contact Customer Support.")
        self.assertEqual(response.data["support_phone"], self.contact_settings.support_phone)

    def test_check_availability_endpoint_invalid_payload(self):
        payload = {
            "pincode": "560005",
            # Missing date and time_slot
        }
        response = self.client.post("/api/orders/delivery-slots/check-availability/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delivery_otp_workflow(self):
        # Authenticate as seller_user
        self.client.force_authenticate(user=self.seller_user)
        self.seller_user.phone_number = "9988776655"
        self.seller_user.save()

        # Create order
        order = Order.objects.create(
            user=self.customer,
            shipping_address="123 Road, 560001",
            billing_address="Same",
            status=Order.Status.IN_PROGRESS,
            delivery_person=self.seller_user,
            subtotal=100.00,
            tax=18.00,
            discount=0.00,
            grand_total=118.00
        )

        # Upload dummy files to progress to COMPLETED
        from django.core.files.uploadedfile import SimpleUploadedFile
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9'
            b'\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02\x4c\x01\x00\x3b'
        )
        before_file = SimpleUploadedFile("before.gif", small_gif, content_type="image/gif")
        after_file = SimpleUploadedFile("after.gif", small_gif, content_type="image/gif")

        # Step 1: Transition to COMPLETED
        response = self.client.post(
            f"/api/orders/{order.id}/update_status/",
            {
                "status": "COMPLETED",
                "before_image": before_file,
                "after_image": after_file
            },
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dummy_otp = response.data.get("dummy_otp")
        self.assertIsNotNone(dummy_otp)

        # Step 2: Verify the OTP in the serializer field
        response_detail = self.client.get(f"/api/orders/{order.id}/")
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(response_detail.data.get("delivery_otp"), dummy_otp)

        # Step 3: Verify OTP check fails with invalid OTP
        response_verify_fail = self.client.post(
            f"/api/orders/{order.id}/verify_delivery_otp/",
            {"otp_code": "000000"},
            format="json"
        )
        self.assertEqual(response_verify_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # Step 4: Verify OTP check succeeds with valid OTP
        response_verify_success = self.client.post(
            f"/api/orders/{order.id}/verify_delivery_otp/",
            {"otp_code": dummy_otp},
            format="json"
        )
        self.assertEqual(response_verify_success.status_code, status.HTTP_200_OK)

        # Step 5: Check status is now CLOSED
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CLOSED)

    def test_customer_can_retrieve_order_tracking_history(self):
        # Create order
        order = Order.objects.create(
            user=self.customer,
            shipping_address="123 Road, 560001",
            billing_address="Same",
            status=Order.Status.PENDING,
            subtotal=100.00,
            tax=18.00,
            discount=0.00,
            grand_total=118.00
        )
        
        # Create a tracking record
        OrderTracking.objects.create(
            order=order,
            status=Order.Status.PENDING,
            updated_by=self.customer,
            notes="Order placed."
        )

        # Authenticate as customer
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(f"/api/orders/{order.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tracking_history", response.data)
        self.assertEqual(len(response.data["tracking_history"]), 1)
        self.assertEqual(response.data["tracking_history"][0]["status"], "PENDING")
