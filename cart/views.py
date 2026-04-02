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

        # Lock products to prevent race conditions
        from products.models import Product
        product_ids = items.values_list('product_id', flat=True)
        locked_products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)}

        subtotal = Decimal('0.00')
        for item in items:
            product = locked_products[item.product_id]
            if product.stock < item.quantity:
                return Response({"error": f"Not enough stock for {product.name}. Only {product.stock} left."}, status=400)
                
            price = product.special_price if product.special_price else product.price
            subtotal += price * item.quantity

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

        from sellers.models import SellerWallet
        for item in items:
            product = locked_products[item.product_id]

            price = product.special_price if product.special_price else product.price
            OrderItem.objects.create(
                order=order,
                product=product,
                seller=product.seller,
                price=price,
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

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CartItem.objects.filter(cart__user=self.request.user)
        return CartItem.objects.none()

class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Coupon.objects.filter(active=True)
    serializer_class = CouponSerializer
    search_fields = ['code']
    ordering_fields = ['valid_to', 'valid_from']
