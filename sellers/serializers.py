from rest_framework import serializers
from .models import SellerProfile, SellerWallet, WithdrawalRequest, WalletTransaction, Settlement

class SellerProfileSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source='user.username')
    seller_name = serializers.SerializerMethodField()
    email = serializers.ReadOnlyField(source='user.email')
    gst = serializers.CharField(source='gst_number', required=False, allow_null=True)
    commission = serializers.DecimalField(source='commission_rate', max_digits=5, decimal_places=2, required=False)

    def get_seller_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    class Meta:
        model = SellerProfile
        fields = [
            "id", "user", "name", "seller_name", "email", "business_name", "status", "commission", 
            "gst", "gst_number", "pan_number", "aadhaar_number", "shop_license_number",

            "pan_card_copy", "aadhaar_card_copy", "shop_license_copy", "authorized_letter",
            "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", "bank_passbook_copy",
            "shop_image", "owner_image"
        ]
        read_only_fields = ['user', 'status', 'commission', 'is_approved']


class WalletTransactionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = WalletTransaction
        fields = '__all__'

class SettlementSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Settlement
        fields = '__all__'

class SellerWalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = SellerWallet
        fields = ['id', 'seller', 'balance', 'total_earned', 'transactions']

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = '__all__'
        read_only_fields = ['seller', 'status', 'processed_at']

class AdminSellerCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    business_name = serializers.CharField(max_length=255)
    gst_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user_data = {
            'username': validated_data['username'],
            'email': validated_data['email'],
            'password': validated_data['password'],
            'phone_number': validated_data.get('phone_number', ''),
            'role': 'SELLER'
        }
        
        user = User.objects.create_user(**user_data)
        
        seller_profile = SellerProfile.objects.create(
            user=user,
            business_name=validated_data['business_name'],
            gst_number=validated_data.get('gst_number', ''),
            commission_rate=validated_data.get('commission_rate', 0.00),
            status=SellerProfile.Status.APPROVED # Auto-approve when created by admin
        )
        
        return seller_profile
