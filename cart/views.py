from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal
from .models import Cart, CartItem, Coupon
from orders.models import Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, CouponSerializer
from core.permissions import IsCustomer

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user)
        return Cart.objects.none()

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def checkout(self, request, pk=None):
        cart = self.get_object()
        user = request.user
        
        shipping_address = request.data.get('shipping_address')
        billing_address = request.data.get('billing_address')
        
        if not shipping_address or not billing_address:
            return Response({"error": "Shipping and billing addresses are required."}, status=400)
            
        items = cart.items.all()
        if not items.exists():
            return Response({"error": "Cart is empty."}, status=400)

        # Collect all products that need stock checking/locking
        from products.models import Product, ComboProduct
        product_ids = set()
        for item in items:
            if item.product:
                product_ids.add(item.product.id)
            elif item.combo_product:
                product_ids.add(item.combo_product.inverter.id)
                product_ids.add(item.combo_product.battery.id)
        
        # Lock products to prevent race conditions
        locked_products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)}

        subtotal = Decimal('0.00')
        for item in items:
            if item.product:
                product = locked_products[item.product.id]
                if product.stock < item.quantity:
                    return Response({"error": f"Not enough stock for {product.name}. Only {product.stock} left."}, status=400)
                price = product.special_price if product.special_price else product.price
                subtotal += price * item.quantity
            elif item.combo_product:
                # Check both components
                inv = locked_products[item.combo_product.inverter.id]
                bat = locked_products[item.combo_product.battery.id]
                if inv.stock < item.quantity or bat.stock < item.quantity:
                    return Response({"error": f"Not enough component stock for {item.combo_product.name}."}, status=400)
                subtotal += item.combo_product.price * item.quantity

        discount = Decimal('0.00')
        if cart.coupon and cart.coupon.active:
            if cart.coupon.discount_percent:
                discount = (subtotal * cart.coupon.discount_percent) / Decimal('100.00')
            elif cart.coupon.discount_amount:
                discount = cart.coupon.discount_amount
                
        # 18% GST (Tax) Calculation India
        tax = (subtotal - discount) * Decimal('0.18')
        shipping_fee = Decimal('50.00') if subtotal < Decimal('500.00') else Decimal('0.00')
        grand_total = subtotal - discount + tax + shipping_fee

        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            billing_address=billing_address,
            subtotal=round(subtotal, 2),
            tax=round(tax, 2),
            discount=round(discount, 2),
            shipping_fee=round(shipping_fee, 2),
            grand_total=round(grand_total, 2)
        )

        for item in items:
            if item.product:
                product = locked_products[item.product.id]
                product.stock -= item.quantity
                product.save()
                
                price = product.special_price if product.special_price else product.price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    seller=product.seller,
                    price=price,
                    quantity=item.quantity
                )
            elif item.combo_product:
                # Deduct from both components
                inv = locked_products[item.combo_product.inverter.id]
                bat = locked_products[item.combo_product.battery.id]
                inv.stock -= item.quantity
                bat.stock -= item.quantity
                inv.save()
                bat.save()
                
                OrderItem.objects.create(
                    order=order,
                    combo_product=item.combo_product,
                    seller=item.combo_product.inverter.seller,
                    price=item.combo_product.price,
                    quantity=item.quantity
                )
            
        # Clear Cart
        items.delete()
        cart.coupon = None
        cart.save()

        return Response({
            "message": "Checkout successful. Order placed.",
            "order_id": order.id,
            "grand_total": order.grand_total,
            "tax": order.tax
        })

from rest_framework.exceptions import ValidationError

from core.permissions import IsCustomer, IsOwnerOrAdmin, IsAdminUser
from django.shortcuts import get_object_or_404
from rest_framework import status

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsCustomer()]

    def destroy(self, request, *args, **kwargs):
        # Using get_object_or_404 as requested to avoid AttributeError (NoneType)
        instance = get_object_or_404(self.get_queryset(), pk=kwargs.get('pk'))
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CartItem.objects.filter(cart__user=self.request.user)
        return CartItem.objects.none()

    def perform_create(self, serializer):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class CouponViewSet(viewsets.ModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ['code']
    ordering_fields = ['valid_to', 'valid_from']
    filterset_fields = ['active', 'discount_percent', 'discount_amount']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'apply', 'validate']:
            return [permissions.IsAuthenticated()]
        return [IsAdminUser()]

    def get_queryset(self):
        # Admin can see all, customers only active ones
        if not self.request.user.is_authenticated:
            return Coupon.objects.none()
            
        if self.request.user.role == 'ADMIN':
            return Coupon.objects.all()
            
        from django.utils import timezone
        return Coupon.objects.filter(
            active=True,
            valid_from__lte=timezone.now(),
            valid_to__gte=timezone.now()
        )

    @action(detail=False, methods=['post'])
    def apply(self, request):
        code = request.data.get('code')
        if not code:
            return Response({'error': 'Coupon code is required'}, status=400)
            
        from django.utils import timezone
        try:
            coupon = Coupon.objects.get(
                code=code, 
                active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
        except Coupon.DoesNotExist:
            return Response({'error': 'Invalid or expired coupon code'}, status=400)
            
        # Associate with user's cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart.coupon = coupon
        cart.save()
        
        return Response({
            'message': f'Coupon "{code}" applied successfully',
            'discount': {
                'percent': coupon.discount_percent,
                'amount': coupon.discount_amount
            }
        })

    @action(detail=False, methods=['post'])
    def validate(self, request):
        code = request.data.get('code')
        try:
            coupon = Coupon.objects.get(code=code, active=True)
            from django.utils import timezone
            if coupon.valid_from <= timezone.now() <= coupon.valid_to:
                return Response(CouponSerializer(coupon).data)
            return Response({'error': 'Coupon is expired or not yet valid'}, status=400)
        except Coupon.DoesNotExist:
            return Response({'error': 'Invalid coupon code'}, status=400)
