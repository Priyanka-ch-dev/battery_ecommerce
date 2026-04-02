import os
import sys
import django

# Add current directory to path
sys.path.append('c:\\Users\\admin\\OneDrive\\Documents\\Desktop\\CT\\battery_ecommerce_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from users.models import User
from sellers.models import SellerProfile
from products.models import Product, Category
from products.views import ProductViewSet, CategoryViewSet

def run_tests():
    factory = APIRequestFactory()
    
    # Use existing or create test users
    admin, _ = User.objects.get_or_create(username='admin_perm_test', email='admin_p@example.com')
    admin.role = 'ADMIN'
    admin.save()
    
    seller1_user, _ = User.objects.get_or_create(username='seller1_perm', email='s1_p@example.com')
    seller1_user.role = 'SELLER'
    seller1_user.save()
    
    seller2_user, _ = User.objects.get_or_create(username='seller2_perm', email='s2_p@example.com')
    seller2_user.role = 'SELLER'
    seller2_user.save()
    
    customer, _ = User.objects.get_or_create(username='customer1_perm', email='c1_p@example.com')
    customer.role = 'CUSTOMER'
    customer.save()
    
    # Create profiles
    s1_profile, _ = SellerProfile.objects.get_or_create(user=seller1_user, defaults={'business_name': "S1 store"})
    s2_profile, _ = SellerProfile.objects.get_or_create(user=seller2_user, defaults={'business_name': "S2 store"})
    
    # Create Category
    cat, _ = Category.objects.get_or_create(name="Test Cat Permissions", slug="test-cat-perm")
    
    # Create a product owned by seller 1
    p1, _ = Product.objects.get_or_create(
        name="P1 Perm Test", 
        slug="p1-perm-test", 
        defaults={'seller': s1_profile, 'category': cat, 'price': 100}
    )
    
    # Test 1: Customer trying to delete category (should fail)
    print("Test 1: Customer vs Category (Destroy)")
    view = CategoryViewSet.as_view({'delete': 'destroy'})
    request = factory.delete(f'/api/categories/{cat.id}/')
    force_authenticate(request, user=customer)
    response = view(request, pk=cat.id)
    print(f"Status: {response.status_code} (Expected 403)")
    
    # Test 2: Seller 2 trying to update P1 (should fail)
    print("\nTest 2: Seller 2 vs P1 (Update)")
    view = ProductViewSet.as_view({'put': 'update', 'patch': 'partial_update'})
    request = factory.patch(f'/api/products/{p1.id}/', {'name': 'P1 updated by S2'})
    force_authenticate(request, user=seller2_user)
    response = view(request, pk=p1.id)
    print(f"Status: {response.status_code} (Expected 403)")
    
    # Test 3: Seller 1 trying to update P1 (should pass)
    print("\nTest 3: Seller 1 vs P1 (Update)")
    request = factory.patch(f'/api/products/{p1.id}/', {'name': 'P1 updated by S1'})
    force_authenticate(request, user=seller1_user)
    response = view(request, pk=p1.id)
    print(f"Status: {response.status_code} (Expected 200 or 400 data error)")
    
    # Test 4: Admin trying to update P1 (should pass)
    print("\nTest 4: Admin vs P1 (Update)")
    request = factory.patch(f'/api/products/{p1.id}/', {'name': 'P1 updated by Admin'})
    force_authenticate(request, user=admin)
    response = view(request, pk=p1.id)
    print(f"Status: {response.status_code} (Expected 200)")

if __name__ == '__main__':
    try:
        run_tests()
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
