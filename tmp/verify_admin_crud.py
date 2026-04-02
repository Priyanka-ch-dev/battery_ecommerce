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
from products.views import ProductViewSet

def run_tests():
    factory = APIRequestFactory()
    
    # Use existing or create test users
    admin, _ = User.objects.get_or_create(username='admin_crud_test', email='admin_c@example.com')
    admin.role = 'ADMIN'
    admin.save()
    
    seller_user, _ = User.objects.get_or_create(username='seller_crud_test', email='seller_c@example.com')
    seller_user.role = 'SELLER'
    seller_user.save()
    
    s_profile, _ = SellerProfile.objects.get_or_create(user=seller_user, defaults={'business_name': "Seller CRUD store"})
    
    cat, _ = Category.objects.get_or_create(name="CRUD Test Cat", slug="crud-test-cat")
    
    # Pre-test cleanup
    Product.objects.filter(sku__in=['ADMIN-001', 'SELLER-001', 'ADMIN-002']).delete()
    
    # Test 1: Admin creates product (no profile)
    print("Test 1: Admin creates product (no profile)")
    view = ProductViewSet.as_view({'post': 'create'})
    data = {
        'name': 'Admin Product',
        'slug': 'admin-product',
        'sku': 'ADMIN-001',
        'description': 'Created by admin',
        'price': '99.99',
        'category': cat.id
    }
    request = factory.post('/api/products/', data)
    force_authenticate(request, user=admin)
    response = view(request)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print(f"Product created with seller: {response.data.get('seller')}")
        p = Product.objects.get(id=response.data['id'])
        if p.seller is None:
            print("SUCCESS: Product correctly has no seller assigned.")
        else:
            print(f"FAILURE: Product has seller {p.seller}")
    else:
        print(f"FAILURE: {response.data}")

    # Test 2: Seller creates product
    print("\nTest 2: Seller creates product")
    data = {
        'name': 'Seller Product',
        'slug': 'seller-product',
        'sku': 'SELLER-001',
        'description': 'Created by seller',
        'price': '88.88',
        'category': cat.id
    }
    request = factory.post('/api/products/', data)
    force_authenticate(request, user=seller_user)
    response = view(request)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print(f"Product created with seller: {response.data.get('seller')}")
        p = Product.objects.get(id=response.data['id'])
        if p.seller == s_profile:
            print("SUCCESS: Product correctly assigned to seller profile.")
        else:
            print(f"FAILURE: Product has seller {p.seller}")
    else:
        print(f"FAILURE: {response.data}")

    # Test 3: Admin creates product for a specific seller
    print("\nTest 3: Admin creates product for a specific seller")
    data = {
        'name': 'Admin Managed Product',
        'slug': 'admin-managed-product',
        'sku': 'ADMIN-002',
        'description': 'Created by admin for seller',
        'price': '77.77',
        'category': cat.id,
        'seller': s_profile.id
    }
    request = factory.post('/api/products/', data)
    force_authenticate(request, user=admin)
    response = view(request)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print(f"Product created with seller: {response.data.get('seller')}")
        if response.data.get('seller') == s_profile.id:
            print("SUCCESS: Admin correctly assigned product to specific seller.")
        else:
            print(f"FAILURE: Product has seller {response.data.get('seller')}")
    else:
        print(f"FAILURE: {response.data}")

if __name__ == '__main__':
    try:
        run_tests()
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
