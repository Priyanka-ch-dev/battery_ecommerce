from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    customer_email = serializers.ReadOnlyField(source='order.user.email')
    customer_id = serializers.ReadOnlyField(source='order.user.id')
    seller_name = serializers.SerializerMethodField()
    seller_id = serializers.SerializerMethodField()
    seller_settlement_status = serializers.SerializerMethodField()
    delivery_person_name = serializers.SerializerMethodField()
    payment_method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'method', 'payment_method_display',
            'customer_payment_status', 'delivery_payment_status', 
            'customer_email', 'customer_id', 'seller_name', 'seller_id', 
            'seller_settlement_status', 'delivery_person_name',
            'status', 'transaction_id', 'razorpay_payment_id', 'created_at'
        ]
        read_only_fields = ['order', 'transaction_id', 'razorpay_payment_id']

    def get_seller_name(self, obj):
        item = obj.order.items.first()
        if item and item.seller:
            return item.seller.business_name
        return "N/A"

    def get_seller_id(self, obj):
        item = obj.order.items.first()
        if item and item.seller:
            return item.seller.id
        return None

    def get_seller_settlement_status(self, obj):
        from sellers.models import WalletTransaction
        tx = WalletTransaction.objects.filter(
            reference=f"Order #{obj.order.id}"
        ).first()
        if tx:
            return tx.status
        return "N/A"

    def get_delivery_person_name(self, obj):
        dp = obj.order.delivery_person
        if dp:
            return f"{dp.first_name} {dp.last_name}".strip() or dp.email
        return "Not Assigned"
