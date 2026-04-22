from .models import Order, OrderItem, OrderTracking
from products.serializers import ProductSerializer
from payments.models import Payment
from rest_framework import serializers

class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_detail', 'quantity', 'price']
        read_only_fields = ['order']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)
        if product and product.stock < quantity:
            raise serializers.ValidationError({"quantity": f"Only {product.stock} items left in stock for {product.name}."})
        return data

class CreateOrderSerializer(serializers.ModelSerializer):
    product = serializers.IntegerField(write_only=True, required=True)
    quantity = serializers.IntegerField(write_only=True, required=False, default=1)

    class Meta:
        model = Order
        fields = ['id', 'product', 'quantity', 'delivery_date', 'delivery_time', 'user', 'status', 'shipping_address', 'billing_address']
        read_only_fields = ['id', 'user', 'status']

    def create(self, validated_data):
        from products.models import Product
        from decimal import Decimal

        product_id = validated_data.pop('product')
        quantity = validated_data.pop('quantity', 1)
        user = validated_data.get('user')
        
        try:
            product_instance = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError({'product': 'Product not found'})

        shipping_address = validated_data.get('shipping_address')
        billing_address = validated_data.get('billing_address')

        price = product_instance.special_price if product_instance.special_price else product_instance.price
        subtotal = price * Decimal(quantity)
        tax = subtotal * Decimal('0.18')
        grand_total = subtotal + tax

        validated_data['subtotal'] = subtotal
        validated_data['tax'] = tax
        validated_data['grand_total'] = grand_total

        order = super().create(validated_data)

        OrderItem.objects.create(
            order=order,
            product=product_instance,
            seller=product_instance.seller,
            price=price,
            quantity=quantity
        )
        return order

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.ReadOnlyField(source='user.email')
    delivery_person_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields ='__all__'
        read_only_fields = [
            'user', 'status', 'subtotal', 'tax', 'discount', 
            'shipping_fee', 'grand_total', 'is_refunded', 
            'refunded_at', 'delivery_person',
            'shipping_address', 'billing_address'
        ]

    def get_delivery_person_name(self, obj):
        if not obj.delivery_person:
            return "Not Assigned"
        return f"{obj.delivery_person.first_name} {obj.delivery_person.last_name}".strip() or obj.delivery_person.email

class OrderDeliverySerializer(serializers.ModelSerializer):
    """
    Serializer for delivery personnel (Sellers) with limited customer data.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.ReadOnlyField(source='user.phone_number')

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'items', 'customer_name', 
            'customer_phone', 'shipping_address', 
            'delivery_date', 'delivery_time',
            'before_image', 'after_image'
        ]
        read_only_fields = ['id', 'items', 'customer_name', 'customer_phone', 'shipping_address']

    def get_customer_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

class OrderTrackingSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.ReadOnlyField(source='updated_by.get_full_name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderTracking
        fields = ['id', 'status', 'status_display', 'updated_by_name', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

# --- Specialized Serializers for Full Detail View ---

class OrderPaymentStatusSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = ['method', 'method_display', 'status', 'status_display', 'transaction_id', 'razorpay_payment_id']

class OrderCustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']

class OrderItemFullSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    seller_name = serializers.ReadOnlyField(source='seller.business_name')
    seller_id = serializers.ReadOnlyField(source='seller.id')

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'quantity', 'price', 'seller_name', 'seller_id']

class OrderFullDetailSerializer(serializers.ModelSerializer):
    items = OrderItemFullSerializer(many=True, read_only=True)
    customer = OrderCustomerDetailSerializer(source='user', read_only=True)
    payment_details = OrderPaymentStatusSerializer(source='payment', read_only=True)
    tracking_history = OrderTrackingSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Declare specialized method fields
    seller_earnings = serializers.SerializerMethodField()
    customer_payment_status = serializers.SerializerMethodField()
    delivery_payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display', 'customer', 'shipping_address',
            'billing_address', 'items', 'subtotal', 'tax', 'discount',
            'shipping_fee', 'grand_total', 'payment_details', 'tracking_history',
            'delivery_person', 'delivery_date', 'delivery_time', 'seller_earnings',
            'customer_payment_status', 'delivery_payment_status'
        ]

    def get_customer_payment_status(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.customer_payment_status
        return "PENDING"

    def get_delivery_payment_status(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.delivery_payment_status
        return "PENDING"

    def get_seller_earnings(self, obj):
        from sellers.models import WalletTransaction
        # Calculate earnings for each unique seller in the order
        earnings = []
        for item in obj.items.all():
            if not item.seller: continue
            
            # Simple calculation: price - commission (e.g. 10%) - delivery charges
            price = item.price * item.quantity
            commission = price * (item.seller.commission_rate / 100)
            delivery = obj.shipping_fee # Simplification
            net = price - commission - delivery
            
            # Check settlement status
            tx = WalletTransaction.objects.filter(
                wallet__seller=item.seller,
                reference=f"Order #{obj.id}"
            ).first()
            settlement_status = tx.status if tx else "PENDING"

            earnings.append({
                'seller_name': item.seller.business_name,
                'gross': price,
                'commission': commission,
                'delivery_charge': delivery,
                'net_earning': net,
                'settlement_status': settlement_status
            })

