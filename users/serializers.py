from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Address, Wishlist, State, City, ServiceableCity

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    # Seller specific fields (not in User model)
    gst_number = serializers.CharField(write_only=True, required=False)
    pan_number = serializers.CharField(write_only=True, required=False)
    aadhaar_number = serializers.CharField(write_only=True, required=False)
    shop_license_number = serializers.CharField(write_only=True, required=False)
    
    # Documents
    pan_card_copy = serializers.FileField(write_only=True, required=False)
    aadhaar_card_copy = serializers.FileField(write_only=True, required=False)
    shop_license_copy = serializers.FileField(write_only=True, required=False)
    
    # Bank Details
    bank_account_name = serializers.CharField(write_only=True, required=False)
    bank_account_number = serializers.CharField(write_only=True, required=False)
    bank_ifsc = serializers.CharField(write_only=True, required=False)
    bank_name = serializers.CharField(write_only=True, required=False)
    bank_passbook_copy = serializers.FileField(write_only=True, required=False)
    
    # Address
    business_address = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'role', 'phone_number', 'first_name', 'last_name',
            'business_name', 'gst_number', 'pan_number', 'aadhaar_number', 'shop_license_number',
            'pan_card_copy', 'aadhaar_card_copy', 'shop_license_copy',
            'bank_account_name', 'bank_account_number', 'bank_ifsc', 'bank_name', 'bank_passbook_copy',
            'business_address'
        ]

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError("Registration with ADMIN role is not allowed via the API.")
        if value not in [User.Role.CUSTOMER, User.Role.SELLER]:
            raise serializers.ValidationError("Invalid role provided.")
        return value

    def to_internal_value(self, data):
        from django.http import QueryDict
        if isinstance(data, QueryDict):
            clean_data = data.copy()
        elif isinstance(data, dict):
            clean_data = data.copy()
        else:
            clean_data = data

        role = clean_data.get('role', User.Role.CUSTOMER)
        
        seller_fields = [
            'business_name', 'gst_number', 'pan_number', 'aadhaar_number', 'shop_license_number',
            'pan_card_copy', 'aadhaar_card_copy', 'shop_license_copy',
            'bank_account_name', 'bank_account_number', 'bank_ifsc', 'bank_name', 'bank_passbook_copy',
            'business_address'
        ]
        
        file_fields = ['pan_card_copy', 'aadhaar_card_copy', 'shop_license_copy', 'bank_passbook_copy']

        if role != User.Role.SELLER:
            for field in seller_fields:
                if hasattr(clean_data, 'pop'):
                    clean_data.pop(field, None)
        else:
            for field in file_fields:
                if hasattr(clean_data, 'get'):
                    val = clean_data.get(field)
                    if val in ['', 'null', 'undefined', None]:
                        try:
                            clean_data.pop(field)
                        except KeyError:
                            pass
                        
        return super().to_internal_value(clean_data)

    def validate(self, data):
        role = data.get('role', User.Role.CUSTOMER)
        business_name = data.get('business_name')
        
        seller_fields = [
            'business_name', 'gst_number', 'pan_number', 'aadhaar_number', 'shop_license_number',
            'pan_card_copy', 'aadhaar_card_copy', 'shop_license_copy',
            'bank_account_name', 'bank_account_number', 'bank_ifsc', 'bank_name', 'bank_passbook_copy',
            'business_address'
        ]

        if role == User.Role.SELLER:
            if not business_name:
                raise serializers.ValidationError({'business_name': "This field is mandatory for seller registration."})
                
            required_seller_fields = seller_fields.copy()
            required_seller_fields.remove('business_name')
            required_seller_fields.append('phone_number')

            missing_fields = [field for field in required_seller_fields if not data.get(field)]
            if missing_fields:
                errors = {field: "This field is mandatory for seller registration." for field in missing_fields}
                raise serializers.ValidationError(errors)
        else:
            # Customer role: Only basic fields are accepted.
            for field in seller_fields:
                data.pop(field, None)
                
        return data

    def create(self, validated_data):
        # Extract seller-specific data
        seller_fields = [
            'gst_number', 'pan_number', 'aadhaar_number', 'shop_license_number',
            'pan_card_copy', 'aadhaar_card_copy', 'shop_license_copy',
            'bank_account_name', 'bank_account_number', 'bank_ifsc', 'bank_name', 'bank_passbook_copy',
            'business_address'
        ]
        seller_data = {field: validated_data.pop(field, None) for field in seller_fields}
        business_name = validated_data.get('business_name')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', User.Role.CUSTOMER),
            phone_number=validated_data.get('phone_number', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            business_name=business_name
        )

        if user.role == User.Role.SELLER:
            from django.apps import apps
            SellerProfile = apps.get_model('sellers', 'SellerProfile')
            SellerProfile.objects.create(
                user=user, 
                business_name=business_name,
                **seller_data
            )

        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone_number', 'first_name', 'last_name']
        read_only_fields = ['role']

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']

class WishlistSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'product', 'added_at', 'product_name', 'product_price']
        read_only_fields = ['user']

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name']

class CitySerializer(serializers.ModelSerializer):
    state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all())

    class Meta:
        model = City
        fields = ['id', 'name', 'state']

class ServiceableCitySerializer(serializers.ModelSerializer):
    city_name = serializers.ReadOnlyField(source='city.name')
    state_name = serializers.ReadOnlyField(source='city.state.name')
    state = serializers.CharField(write_only=True, required=False) # Accept name or ID
    state_id = serializers.IntegerField(write_only=True, required=False)
    city = serializers.CharField() # Accept name or ID

    class Meta:
        model = ServiceableCity
        fields = ['id', 'city', 'city_name', 'state', 'state_id', 'state_name', 'is_service_available']

    def validate(self, data):
        state_input = data.get('state') or data.get('state_id')
        city_input = data.get('city')
        
        # 1. Resolve State
        state_obj = None
        if state_input:
            if str(state_input).isdigit():
                state_obj = State.objects.filter(id=state_input).first()
            else:
                state_obj = State.objects.filter(name__iexact=state_input).first()
            
            if not state_obj:
                raise serializers.ValidationError({"state": f"State '{state_input}' not found."})

        # 2. Resolve City
        city_obj = None
        if str(city_input).isdigit():
            city_obj = City.objects.filter(id=city_input).first()
        elif state_obj:
            city_obj = City.objects.filter(name__iexact=city_input, state=state_obj).first()
        else:
            # If no state provided, try to find a unique city by name
            cities = City.objects.filter(name__iexact=city_input)
            if cities.count() > 1:
                raise serializers.ValidationError({"city": f"Multiple cities named '{city_input}' found. Please specify the state."})
            city_obj = cities.first()

        if not city_obj:
            raise serializers.ValidationError({"city": f"City '{city_input}' not found (context: {state_obj.name if state_obj else 'None'})."})

        # Update data with the resolved city object
        data['city'] = city_obj
        return data

    def create(self, validated_data):
        city = validated_data.get('city')
        # Use update_or_create to avoid IntegrityError on OneToOneField
        obj, created = ServiceableCity.objects.update_or_create(
            city=city,
            defaults={'is_service_available': validated_data.get('is_service_available', True)}
        )
        return obj

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Expose basic user data in login response
        user_data = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
        }

        # Include approval status for sellers
        if self.user.role == 'SELLER':
            try:
                user_data['is_approved'] = self.user.seller_profile.is_approved
                user_data['status'] = self.user.seller_profile.status
            except AttributeError:
                user_data['is_approved'] = False
                user_data['status'] = 'PENDING'

        data['user'] = user_data
        return data
