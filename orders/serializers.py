from .models import Order, OrderItem, OrderTracking, DeliverySlot
from products.serializers import ProductSerializer
from payments.models import Payment
from rest_framework import serializers

class DeliverySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverySlot
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    combo_product_detail = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_detail', 'combo_product', 'combo_product_detail',
            'quantity', 'price', 'is_exchange', 'exchange_discount',
            'total_amount', 'commission_percentage', 'admin_commission_amount', 'seller_earning'
        ]
        read_only_fields = ['order', 'exchange_discount']

    def get_combo_product_detail(self, obj):
        if obj.combo_product:
            from products.serializers import ComboProductSerializer
            return ComboProductSerializer(obj.combo_product, context=self.context).data
        return None

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)
        if product and product.stock < quantity:
            raise serializers.ValidationError({"message": f"{product.name} is not available."})
        return data

class CreateOrderSerializer(serializers.ModelSerializer):
    product = serializers.IntegerField(write_only=True, required=False)
    combo_product = serializers.IntegerField(write_only=True, required=False)
    quantity = serializers.IntegerField(write_only=True, required=False, default=1)
    is_exchange = serializers.BooleanField(write_only=True, required=False, default=False)
    pincode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = ['id', 'product', 'combo_product', 'quantity', 'is_exchange', 'delivery_date', 'delivery_time', 'user', 'status', 'shipping_address', 'billing_address', 'pincode']
        read_only_fields = ['id', 'user', 'status']

    def create(self, validated_data):
        from products.models import Product, ComboProduct
        from decimal import Decimal

        product_id = validated_data.pop('product', None)
        combo_product_id = validated_data.pop('combo_product', None)
        quantity = validated_data.pop('quantity', 1)
        is_exchange = validated_data.pop('is_exchange', False)
        user = validated_data.get('user')
        
        if not product_id and not combo_product_id:
            raise serializers.ValidationError({'error': 'Either product or combo_product is required'})

        shipping_address = validated_data.get('shipping_address')
        billing_address = validated_data.get('billing_address')
        delivery_date = validated_data.get('delivery_date')
        delivery_time = validated_data.get('delivery_time')
        pincode = validated_data.pop('pincode', None)

        import re
        from orders.models import DeliverySlot
        from contact.models import ContactSettings
        
        if not pincode and shipping_address:
            match = re.search(r'\b\d{3}[\s-]*\d{3}\b', shipping_address)
            if match:
                pincode = re.sub(r'[\s-]', '', match.group(0))

        slot = None
        if delivery_date and delivery_time:
            if not pincode:
                raise serializers.ValidationError({"error": "A valid 6-digit pincode is required in the shipping address to book a delivery slot."})
            
            slot, created = DeliverySlot.objects.get_or_create(
                date=delivery_date,
                time_slot=delivery_time,
                pincode=pincode,
                defaults={'max_bookings': 1, 'is_active': True}
            )
            if not slot.is_active or slot.current_bookings >= slot.max_bookings:
                contact_setting = ContactSettings.objects.first()
                support_phone = contact_setting.support_phone if contact_setting and contact_setting.support_phone else "Support"
                raise serializers.ValidationError({
                    "error": "This delivery/installation slot is already booked for your area. Please select another available time slot or contact Customer Support.",
                    "support_message": "For assistance or urgent bookings, please contact Customer Support.",
                    "support_phone": support_phone
                })

        product_instance = None
        combo_instance = None
        price = Decimal('0.00')
        seller = None

        if product_id:
            try:
                product_instance = Product.objects.get(id=product_id)
                price = product_instance.special_price if product_instance.special_price else product_instance.price
                seller = product_instance.seller
            except Product.DoesNotExist:
                raise serializers.ValidationError({'product': 'Product not found'})
        else:
            try:
                combo_instance = ComboProduct.objects.get(id=combo_product_id)
                price = combo_instance.price
                seller = combo_instance.inverter.seller # Use inverter's seller as primary
            except ComboProduct.DoesNotExist:
                raise serializers.ValidationError({'combo_product': 'Combo Product not found'})
        
        exchange_discount = Decimal('0.00')
        if is_exchange and product_instance and product_instance.exchange_available:
            exchange_discount = product_instance.exchange_discount
        
        # Apply discount to unit price for total calculation
        effective_price = max(price - exchange_discount, Decimal('0.00'))
        
        subtotal = effective_price * Decimal(quantity)
        tax = subtotal * Decimal('0.18')
        grand_total = subtotal + tax

        validated_data['is_exchange'] = is_exchange # Store summary in Order
        validated_data['subtotal'] = subtotal
        validated_data['tax'] = tax
        validated_data['grand_total'] = grand_total

        order = super().create(validated_data)
        
        if slot:
            slot.current_bookings += 1
            slot.save()

        # Commission Calculations
        commission_rate = Decimal('7.00')
        if seller and seller.commission_rate > 0:
            commission_rate = seller.commission_rate
            
        total_amount = effective_price * Decimal(quantity)
        admin_commission_amount = (total_amount * commission_rate) / Decimal('100.00')
        seller_earning = total_amount - admin_commission_amount

        OrderItem.objects.create(
            order=order,
            product=product_instance,
            combo_product=combo_instance,
            seller=seller,
            price=price,
            quantity=quantity,
            is_exchange=is_exchange,
            exchange_discount=exchange_discount,
            total_amount=total_amount,
            commission_percentage=commission_rate,
            admin_commission_amount=admin_commission_amount,
            seller_earning=seller_earning
        )

        # Create Payment record automatically
        from payments.models import Payment
        Payment.objects.create(
            order=order,
            amount=grand_total,
            method=Payment.PaymentMethod.COD, # Default to COD, can be updated via Razorpay flow
            status=Payment.CustomerStatus.PENDING
        )
        
        return order

class OrderTrackingSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.ReadOnlyField(source='updated_by.get_full_name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderTracking
        fields = ['id', 'status', 'status_display', 'updated_by_name', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.ReadOnlyField(source='user.email')
    customer_name = serializers.SerializerMethodField()
    delivery_person_name = serializers.SerializerMethodField()
    payment_method = serializers.ReadOnlyField(source='payment.method')
    payment_status = serializers.SerializerMethodField()
    tracking_history = OrderTrackingSerializer(many=True, read_only=True)

    def get_customer_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def get_payment_status(self, obj):
        if hasattr(obj, 'payment') and obj.payment:
            return obj.payment.status
        return "N/A"

    class Meta:
        model = Order
        fields = [
            'id', 'items', 'user_email', 'customer_name', 'delivery_person_name', 
            'payment_method', 'payment_status', 'status', 'subtotal', 'tax', 'discount', 
            'shipping_fee', 'grand_total', 'is_refunded', 'refunded_at', 
            'delivery_person', 'shipping_address', 'billing_address', 'created_at',
            'delivery_date', 'delivery_time', 'tracking_history'
        ]
        read_only_fields = [
            'user', 'status', 'subtotal', 'tax', 'discount', 
            'shipping_fee', 'grand_total', 'is_refunded', 
            'refunded_at', 'delivery_person',
            'shipping_address', 'billing_address'
        ]

    def get_delivery_person_name(self, obj):
        # Prefer assigned delivery person full name
        if obj.delivery_person:
            return f"{obj.delivery_person.first_name} {obj.delivery_person.last_name}".strip() or obj.delivery_person.email
            
        # Fallback to the first item's seller's personal name
        item = obj.items.first()
        if item and item.seller:
            user = item.seller.user
            return f"{user.first_name} {user.last_name}".strip() or user.email
            
        return "Not Assigned"



class OrderPaymentStatusSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = ['method', 'method_display', 'status', 'status_display', 'transaction_id', 'razorpay_order_id', 'razorpay_payment_id']

class OrderDeliverySerializer(serializers.ModelSerializer):
    """
    Serializer for delivery personnel (Sellers) with limited customer data.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.ReadOnlyField(source='user.phone_number')
    tracking_history = OrderTrackingSerializer(many=True, read_only=True)
    delivery_otp = serializers.SerializerMethodField()
    payment_details = OrderPaymentStatusSerializer(source='payment', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'items', 'customer_name', 
            'customer_phone', 'shipping_address', 
            'delivery_date', 'delivery_time',
            'before_image', 'after_image', 'grand_total',
            'tracking_history', 'delivery_otp', 'payment_details'
        ]
        read_only_fields = ['id', 'items', 'customer_name', 'customer_phone', 'shipping_address']

    def get_customer_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def get_delivery_otp(self, obj):
        from otp_service.models import OTPRecord
        if not obj.user or not obj.user.phone_number:
            return None
        otp_rec = OTPRecord.objects.filter(
            phone_number=obj.user.phone_number,
            purpose=OTPRecord.Purpose.DELIVERY,
            is_verified=False
        ).order_by('-created_at').first()
        
        if otp_rec and not otp_rec.is_expired:
            return otp_rec.otp_code
        return None

# --- Specialized Serializers for Full Detail View ---

class OrderCustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']

class OrderItemFullSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    seller_id = serializers.ReadOnlyField(source='seller.id')

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_image', 'quantity', 'price', 'seller_name', 'seller_id', 'is_exchange', 'exchange_discount']

    def get_product_name(self, obj):
        if obj.combo_product:
            return f"Combo: {obj.combo_product.name}"
        return obj.product.name if obj.product else "Deleted Product"

    def get_product_image(self, obj):
        request = self.context.get('request')
        if obj.combo_product:
            # First try images related set for absolute URL
            primary_img = obj.combo_product.images.filter(is_primary=True).first()
            if not primary_img:
                primary_img = obj.combo_product.images.first()
            if primary_img and primary_img.image:
                return request.build_absolute_uri(primary_img.image.url) if request else primary_img.image.url
            # Fallback to model image field
            if obj.combo_product.image:
                return request.build_absolute_uri(obj.combo_product.image.url) if request else obj.combo_product.image.url
            return None
        if obj.product:
            primary_img = obj.product.images.filter(is_primary=True).first()
            if not primary_img:
                primary_img = obj.product.images.first()
            if primary_img:
                return request.build_absolute_uri(primary_img.image.url) if request else primary_img.image.url
        return None

    def get_seller_name(self, obj):
        if not obj.seller: return "N/A"
        user = obj.seller.user
        return f"{user.first_name} {user.last_name}".strip() or user.email

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
    delivery_person_name = serializers.SerializerMethodField()
    before_image = serializers.SerializerMethodField()
    after_image = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display', 'customer', 'shipping_address',
            'billing_address', 'items', 'subtotal', 'tax', 'discount',
            'shipping_fee', 'grand_total', 'payment_details', 'tracking_history',
            'delivery_person', 'delivery_date', 'delivery_time', 'seller_earnings',
            'customer_payment_status', 'delivery_payment_status', 'is_exchange',
            'delivery_person_name', 'created_at','before_image','after_image'
        ]

    def get_delivery_person_name(self, obj):
        # Prefer assigned delivery person full name
        if obj.delivery_person:
            return f"{obj.delivery_person.first_name} {obj.delivery_person.last_name}".strip() or obj.delivery_person.email
            
        # Fallback to the first item's seller's personal name
        item = obj.items.first()
        if item and item.seller:
            user = item.seller.user
            return f"{user.first_name} {user.last_name}".strip() or user.email
            
        return "Not Assigned"

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
        seller_profits = {} # business_name -> {gross, commission, delivery, net, status}
        
        for item in obj.items.all():
            if not item.seller: continue
            
            price = item.total_amount
            commission = item.admin_commission_amount
            net = item.seller_earning
            
            name = item.seller.business_name
            if name not in seller_profits:
                seller_profits[name] = {'gross': 0, 'commission': 0, 'delivery': 0, 'net': 0, 'seller_id': item.seller.id}
            
            seller_profits[name]['gross'] += price
            seller_profits[name]['commission'] += commission
            seller_profits[name]['net'] += net

        # Add shipping fee to the assigned delivery person
        delivery_seller = getattr(obj.delivery_person, 'seller_profile', None) if obj.delivery_person else None
        if delivery_seller and obj.shipping_fee > 0:
            name = delivery_seller.business_name
            if name in seller_profits:
                seller_profits[name]['delivery'] += obj.shipping_fee
                seller_profits[name]['net'] += obj.shipping_fee
            else:
                seller_profits[name] = {
                    'gross': 0, 'commission': 0, 'delivery': obj.shipping_fee, 
                    'net': obj.shipping_fee, 'seller_id': delivery_seller.id
                }

        # Format for output and check settlement status
        results = []
        for name, data in seller_profits.items():
            tx = WalletTransaction.objects.filter(
                wallet__seller_id=data['seller_id'],
                reference=f"Order #{obj.id}"
            ).first()
            data['settlement_status'] = tx.status if tx else "PENDING"
            data['seller_name'] = name
            results.append(data)
            
        return results
    def get_before_image(self, obj):
        request = self.context.get('request')
        if obj.before_image:
            return request.build_absolute_uri(obj.before_image.url)
        return None

    def get_after_image(self, obj):
        request = self.context.get('request')
        if obj.after_image:
            return request.build_absolute_uri(obj.after_image.url)
        return None
