from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Address, Wishlist

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    business_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'phone_number', 'first_name', 'last_name', 'business_name']

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError("Registration with ADMIN role is not allowed via the API.")
        if value not in [User.Role.CUSTOMER, User.Role.SELLER]:
            raise serializers.ValidationError("Invalid role provided.")
        return value

    def create(self, validated_data):
        business_name = validated_data.pop('business_name', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', User.Role.CUSTOMER),
            phone_number=validated_data.get('phone_number', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )

        if user.role == User.Role.SELLER:
            from django.apps import apps
            SellerProfile = apps.get_model('sellers', 'SellerProfile')
            SellerProfile.objects.create(
                user=user, 
                business_name=business_name or f"{user.username}'s Store"
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
    class Meta:
        model = Wishlist
        fields = '__all__'
        read_only_fields = ['user']

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
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
        }
        return data
