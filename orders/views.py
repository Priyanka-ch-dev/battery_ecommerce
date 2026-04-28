from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Order, OrderTracking
from .serializers import OrderSerializer, OrderDeliverySerializer, OrderTrackingSerializer, CreateOrderSerializer, OrderFullDetailSerializer
from core.permissions import IsAdminUser, IsDeliveryPerson, IsCustomer, IsAdminOrDeliveryPerson
from decimal import Decimal
from products.models import Product
from .models import OrderItem
from sellers.models import SellerWallet, WalletTransaction
from payments.models import Payment

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user', 'status', 'delivery_date']
    search_fields = ['id', 'user__email', 'shipping_address', 'billing_address']
    ordering_fields = ['created_at', 'grand_total']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user
        
        # Safety check for unauthenticated users (e.g. Swagger generation)
        if not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
            return Order.objects.none()
            
        role = getattr(user, 'role', None)
        is_admin = role == 'ADMIN' or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)

        if is_admin:
            return Order.objects.all()
        
        if role == 'SELLER':
            # Priority 1: Orders assigned to this seller for delivery/installation
            # Priority 2: Orders containing items sold by this seller (if any)
            try:
                assigned_orders = Order.objects.filter(delivery_person=user)
                item_orders = Order.objects.filter(items__seller=user.seller_profile) if hasattr(user, 'seller_profile') else Order.objects.none()
                return (assigned_orders | item_orders).distinct()
            except Exception:
                return Order.objects.none()
        
        if role == 'CUSTOMER':
            return Order.objects.filter(user=user)
            
        return Order.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            # Import locally to avoid circular dependency issues if any
            return CreateOrderSerializer
            
        # Gracefully handle unauthenticated Mock Requests from Swagger
        if getattr(self.request.user, 'role', None) == 'SELLER' and self.action in ['list', 'retrieve', 'partial_update', 'update_status']:
            return OrderDeliverySerializer
        
        if self.action == 'retrieve' and self.request.user.role == 'ADMIN':
            return OrderFullDetailSerializer
            
        return OrderSerializer

    def perform_create(self, serializer):
        user = self.request.user
        # Prevent admins & sellers from creating orders on behalf of someone else
        if user.role != 'CUSTOMER':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only authenticated customers can create orders.")

        order = serializer.save(user=user)
        # Record initial tracking status
        OrderTracking.objects.create(
            order=order,
            status=Order.Status.PENDING,
            updated_by=user,
            notes="Order placed successfully."
        )

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        old_status = instance.status
        
        # Handle payment status update if passed in request data
        payment_status = self.request.data.get('payment_status')
        if payment_status and hasattr(instance, 'payment') and user.role == 'ADMIN':
            payment = instance.payment
            payment.status = payment_status
            payment.save()

        order = serializer.save()
        new_status = order.status

        # Automatically record tracking if status changed
        if old_status != new_status:
            OrderTracking.objects.create(
                order=order,
                status=new_status,
                updated_by=user,
                notes=f"Status updated to {new_status} via dashboard."
            )
            
            # TRIGGER WALLET CREDIT IF DELIVERED
            if new_status == Order.Status.DELIVERED:
                self.process_seller_earnings(order)

    def process_seller_earnings(self, order):
        """
        Calculates and stores seller earnings when an order is delivered.
        The assigned delivery_person (Seller) receives the shipping fee.
        """
        seller_profits = {} # seller_id -> profit

        for item in order.items.all():
            if not item.seller: continue
            
            # Profit = item price - commission
            price = item.price * item.quantity
            commission = price * (item.seller.commission_rate / 100)
            profit = price - commission
            
            seller_id = item.seller.id
            seller_profits[seller_id] = seller_profits.get(seller_id, 0) + profit

        # The assigned delivery person (must be a seller) gets the shipping fee
        delivery_seller_profile = getattr(order.delivery_person, 'seller_profile', None) if order.delivery_person else None
        if delivery_seller_profile and order.shipping_fee > 0:
            ds_id = delivery_seller_profile.id
            seller_profits[ds_id] = seller_profits.get(ds_id, 0) + order.shipping_fee

        # Create wallet transactions
        from sellers.models import SellerProfile
        for seller_id, amount in seller_profits.items():
            seller_profile = SellerProfile.objects.get(id=seller_id)
            wallet, _ = SellerWallet.objects.get_or_create(seller=seller_profile)
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.Type.CREDIT,
                amount=amount,
                reference=f"Order #{order.id}",
                status=WalletTransaction.Status.PENDING
            )

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_payment_status(self, request, pk=None):
        order = self.get_object()
        if not hasattr(order, 'payment'):
            return Response({'error': 'No payment record found'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment = order.payment
        update_type = request.data.get('update_type') # 'customer' or 'delivery'
        new_val = request.data.get('status')
        
        if update_type == 'customer':
            payment.customer_payment_status = new_val
            payment.status = new_val # Sync legacy
        elif update_type == 'delivery':
            payment.delivery_payment_status = new_val
        else:
            # Backward compatibility
            payment.status = new_val 
            payment.customer_payment_status = new_val
            
        payment.save()
        return Response({'status': 'Tracking updated successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_seller(self, request, pk=None):
        order = self.get_object()
        seller_id = request.data.get('seller_id')
        if not seller_id:
            return Response({'error': 'seller_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            seller = User.objects.get(id=seller_id, role='SELLER')
            # Check if seller is approved
            if not getattr(seller, 'seller_profile', None) or seller.seller_profile.status != 'APPROVED':
                return Response({'error': 'Seller must be approved by admin before receiving orders'}, status=status.HTTP_400_BAD_REQUEST)
            
            order.delivery_person = seller
            order.status = Order.Status.ASSIGNED
            order.save()
            
            # Record tracking
            OrderTracking.objects.create(
                order=order,
                status=Order.Status.ASSIGNED,
                updated_by=request.user,
                notes=f"Order assigned to delivery person: {seller.email}"
            )
            
            return Response({'status': f'Order assigned to {seller.email}'})
        except User.DoesNotExist:
            return Response({'error': 'Invalid seller ID or user is not a seller'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrDeliveryPerson])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        # Role-based status restrictions for Sellers
        if self.request.user.role == 'SELLER':
            # User requested flow: Pending -> In Progress -> Completed
            # Mapping to model: PENDING -> IN_PROGRESS -> COMPLETED
            allowed_seller_statuses = [
                Order.Status.IN_PROGRESS, 
                Order.Status.COMPLETED,
                Order.Status.SHIPPED, 
                Order.Status.OUT_FOR_DELIVERY, 
                Order.Status.DELIVERED
            ]
            if new_status not in allowed_seller_statuses:
                return Response({
                    'error': f'Sellers can only update status to: {allowed_seller_statuses}'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Installation Image Uploads
            if 'before_image' in request.FILES:
                order.before_image = request.FILES['before_image']
            if 'after_image' in request.FILES:
                order.after_image = request.FILES['after_image']
        
        # Check if status is valid
        if new_status not in [choice[0] for choice in Order.Status.choices]:
            return Response({'error': 'Invalid status choice'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save()
        
        # Record tracking entry
        OrderTracking.objects.create(
            order=order,
            status=new_status,
            updated_by=request.user,
            notes=notes
        )
        
        return Response({'status': f'Order status updated to {new_status}'})

    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        order = self.get_object()
        history = order.tracking_history.all()
        serializer = OrderTrackingSerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsCustomer])
    def request_refund(self, request, pk=None):
        order = self.get_object()
        if order.status == Order.Status.DELIVERED:
            return Response({'error': 'Refund cannot be requested after delivery'}, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'No reason provided')
        order.status = Order.Status.REFUND_REQUESTED
        order.refund_reason = reason
        order.save()
        
        # Record tracking
        OrderTracking.objects.create(
            order=order,
            status=Order.Status.REFUND_REQUESTED,
            updated_by=request.user,
            notes=f"Refund requested. Reason: {reason}"
        )
        
        return Response({'status': 'Refund requested'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def process_refund(self, request, pk=None):
        order = self.get_object()
        if order.status == Order.Status.DELIVERED:
            return Response({'error': 'Refund not allowed after delivery'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.status = Order.Status.REFUNDED
        order.is_refunded = True
        order.refunded_at = timezone.now()
        order.save()

        # Record tracking
        OrderTracking.objects.create(
            order=order,
            status=Order.Status.REFUNDED,
            updated_by=request.user,
            notes="Refund processed by Admin."
        )

        # Sync with Payment model
        if hasattr(order, 'payment'):
            payment = order.payment
            payment.status = 'REFUNDED'
            payment.save()

        return Response({'status': 'Order and Payment refunded successfully'})
