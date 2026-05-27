from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from products.models import Product, ProductImage
from users.models import Wishlist

User = get_user_model()

class WishlistProductImageTests(APITestCase):
    def setUp(self):
        # Create user
        self.customer = User.objects.create_user(
            email="customer@example.com",
            username="customer@example.com",
            password="password123",
            role="CUSTOMER"
        )
        self.client.force_authenticate(user=self.customer)

        # Create a product
        self.product = Product.objects.create(
            name="Test Battery",
            sku="BATT-TEST-001",
            description="A test battery for unit testing.",
            price=150.00,
            stock=10
        )

    def test_wishlist_image_fallback_placeholder(self):
        """If the product has no images, the wishlist API should return the placeholder URL."""
        wishlist_item = Wishlist.objects.create(user=self.customer, product=self.product)
        
        response = self.client.get("/api/users/wishlists/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["product_image"], "https://via.placeholder.com/150")

    def test_wishlist_image_primary(self):
        """If the product has a primary image, it should be returned."""
        # Create a non-primary image
        ProductImage.objects.create(
            product=self.product,
            image="products/non_primary.jpg",
            is_primary=False
        )
        # Create a primary image
        ProductImage.objects.create(
            product=self.product,
            image="products/primary.jpg",
            is_primary=True
        )

        Wishlist.objects.create(user=self.customer, product=self.product)
        
        response = self.client.get("/api/users/wishlists/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        # Check that the primary image URL is in the response
        self.assertIn("products/primary.jpg", results[0]["product_image"])

    def test_wishlist_image_first_if_no_primary(self):
        """If the product has no primary image, but has other images, the first one should be returned."""
        # Create a non-primary image
        ProductImage.objects.create(
            product=self.product,
            image="products/first.jpg",
            is_primary=False
        )

        Wishlist.objects.create(user=self.customer, product=self.product)
        
        response = self.client.get("/api/users/wishlists/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertIn("products/first.jpg", results[0]["product_image"])
