import os
import django
import sys

# Add current directory to path
sys.path.append('c:\\Users\\admin\\OneDrive\\Documents\\Desktop\\CT\\battery_ecommerce_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.models import User
from users.serializers import RegisterSerializer
from rest_framework import serializers

def run_tests():
    # Test 1: Register CUSTOMER (should pass)
    print("Testing CUSTOMER registration...")
    data = {
        'username': 'test_customer_unique',
        'email': 'customer_unique@example.com',
        'password': 'Password123!',
        'role': 'CUSTOMER',
        'phone_number': '1234567890',
        'first_name': 'Test',
        'last_name': 'User'
    }
    serializer = RegisterSerializer(data=data)
    if serializer.is_valid():
        print("CUSTOMER registration data is valid.")
    else:
        print(f"CUSTOMER registration data is invalid: {serializer.errors}")

    # Test 2: Register ADMIN (should fail)
    print("\nTesting ADMIN registration...")
    data = {
        'username': 'test_admin_unique',
        'email': 'admin_unique@example.com',
        'password': 'Password123!',
        'role': 'ADMIN'
    }
    serializer = RegisterSerializer(data=data)
    if not serializer.is_valid():
        print(f"ADMIN registration correctly failed: {serializer.errors.get('role', ['No error'])[0]}")
    else:
        print("ADMIN registration incorrectly passed!")

    # Test 3: Create superuser via manager (should have ADMIN role)
    print("\nTesting superuser creation role...")
    try:
        # Create superuser using the manager
        # Note: we use our custom manager's method
        u = User.objects.create_superuser(
            username='superadmin_test_unique', 
            email='superadmin_unique@example.com', 
            password='SuperPassword123!'
        )
        print(f"Superuser {u.username} created with role: {u.role}")
        if u.role == 'ADMIN':
            print("SUCCESS: Superuser correctly assigned ADMIN role.")
        else:
            print(f"FAILURE: Superuser assigned WRONG role: {u.role}")
        
        # Cleanup
        u.delete()
    except Exception as e:
        print(f"Superuser creation failed: {e}")

if __name__ == '__main__':
    run_tests()
