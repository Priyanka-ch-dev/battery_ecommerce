from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from products.models import Product, ProductReview
from sellers.models import SellerProfile

User = get_user_model()

class ProductReviewApprovalTests(APITestCase):
    def setUp(self):
        # Create users
        self.customer = User.objects.create_user(
            email="customer@example.com",
            username="customer@example.com",
            password="password123",
            role="CUSTOMER"
        )
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            username="other@example.com",
            password="password123",
            role="CUSTOMER"
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            username="admin@example.com",
            password="password123"
        )
        self.seller_user = User.objects.create_user(
            email="seller@example.com",
            username="seller@example.com",
            password="password123",
            role="SELLER"
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller_user,
            business_name="Seller Business",
            status="APPROVED"
        )

        # Create product
        self.product = Product.objects.create(
            name="Test Battery",
            price=200.00,
            stock=5,
            seller=self.seller_profile
        )

    def test_review_creation_status_defaults_to_pending(self):
        # Authenticate customer
        self.client.force_authenticate(user=self.customer)
        
        payload = {
            "product": self.product.id,
            "rating": 5,
            "comment": "Excellent quality battery!"
        }
        
        response = self.client.post("/api/products/reviews/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        review_id = response.data['id']
        review = ProductReview.objects.get(id=review_id)
        
        # Verify status is PENDING and is_approved is False
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertFalse(review.is_approved)

    def test_customer_cannot_set_approval_status_or_approved_flag(self):
        self.client.force_authenticate(user=self.customer)
        
        payload = {
            "product": self.product.id,
            "rating": 4,
            "comment": "Good product",
            "status": "APPROVED",
            "is_approved": True
        }
        
        response = self.client.post("/api/products/reviews/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        review_id = response.data['id']
        review = ProductReview.objects.get(id=review_id)
        
        # Verify status and is_approved fields were ignored and defaulted to PENDING/False
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertFalse(review.is_approved)

    def test_public_user_cannot_see_pending_or_rejected_reviews(self):
        # Create a pending review
        pending_review = ProductReview.objects.create(
            product=self.product,
            user=self.customer,
            rating=3,
            comment="Okayish product",
            status=ProductReview.Status.PENDING
        )
        # Create a rejected review
        rejected_review = ProductReview.objects.create(
            product=self.product,
            user=self.customer,
            rating=2,
            comment="Terrible!",
            status=ProductReview.Status.REJECTED
        )
        # Create an approved review
        approved_review = ProductReview.objects.create(
            product=self.product,
            user=self.customer,
            rating=5,
            comment="Superb!",
            status=ProductReview.Status.APPROVED
        )

        # Authenticate as other customer (non-admin)
        self.client.force_authenticate(user=self.other_customer)
        
        # 1. Check reviews list endpoint (registered under router /api/reviews/ or /api/products/reviews/)
        response = self.client.get("/api/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle possible pagination
        reviews_data = response.data.get("results", response.data)
        self.assertEqual(len(reviews_data), 1)
        self.assertEqual(reviews_data[0]['id'], approved_review.id)

        # 2. Check nested reviews in product retrieve endpoint
        prod_response = self.client.get(f"/api/products/{self.product.id}/")
        self.assertEqual(prod_response.status_code, status.HTTP_200_OK)
        prod_reviews = prod_response.data['reviews']
        self.assertEqual(len(prod_reviews), 1)
        self.assertEqual(prod_reviews[0]['id'], approved_review.id)

    def test_admin_can_see_all_reviews(self):
        # Create different reviews
        ProductReview.objects.create(
            product=self.product,
            user=self.customer,
            rating=3,
            comment="Pending review",
            status=ProductReview.Status.PENDING
        )
        ProductReview.objects.create(
            product=self.product,
            user=self.customer,
            rating=2,
            comment="Rejected review",
            status=ProductReview.Status.REJECTED
        )

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get("/api/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reviews_data = response.data.get("results", response.data)
        self.assertEqual(len(reviews_data), 2)

    def test_admin_approve_and_reject_actions(self):
        review = ProductReview.objects.create(
            product=self.product,
            user=self.customer,
            rating=4,
            comment="Pending review to moderate",
            status=ProductReview.Status.PENDING
        )

        self.client.force_authenticate(user=self.admin)
        
        # Approve review
        response = self.client.post(f"/api/products/reviews/{review.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, ProductReview.Status.APPROVED)
        self.assertTrue(review.is_approved)

        # Reject review
        response = self.client.post(f"/api/products/reviews/{review.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, ProductReview.Status.REJECTED)
        self.assertFalse(review.is_approved)
