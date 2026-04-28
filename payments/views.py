from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.conf import settings
import razorpay
from .models import Payment
from .serializers import PaymentSerializer
from core.permissions import IsAdminUser

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        order_id = self.request.data.get('order')
        if not order_id:
            raise ValidationError({'order': 'Order is required.'})

        from orders.models import Order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise ValidationError({'order': 'Order does not exist.'})

        # Check if payment already exists for this order
        if Payment.objects.filter(order=order).exists():
            existing_payment = Payment.objects.get(order=order)
            # Update the existing payment with new data if necessary
            serializer.instance = existing_payment
            serializer.save()
        else:
            serializer.save(order=order)

    def get_queryset(self):
        user = self.request.user
        payment_type = self.request.query_params.get('type')
        
        if user.role == 'ADMIN':
            queryset = Payment.objects.all()
            if payment_type:
                payment_type = payment_type.upper()
                if payment_type in [Payment.PaymentMethod.COD, Payment.PaymentMethod.ONLINE]:
                    queryset = queryset.filter(method=payment_type)
            return queryset
        elif user.role == 'CUSTOMER':
            return Payment.objects.filter(order__user=user)
        elif user.role == 'SELLER':
            # Sellers can see payments for their order items
            return Payment.objects.filter(order__items__seller__user=user).distinct()
        return Payment.objects.none()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify_payment(self, request, pk=None):
        payment = self.get_object()
        transaction_id = request.data.get('transaction_id')
        notes = request.data.get('notes')
        
        if not transaction_id:
            return Response({'error': 'transaction_id is required for verification'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment.status = Payment.CustomerStatus.SUCCESS
        payment.customer_payment_status = Payment.CustomerStatus.SUCCESS
        payment.transaction_id = transaction_id
        payment.verified_by = request.user
        payment.verification_notes = notes
        payment.save()
        
        return Response({'status': 'Payment verified and status updated to SUCCESS'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def create_razorpay_order(self, request, pk=None):
        payment = self.get_object()
        
        if not payment.amount or payment.amount <= 0:
            return Response({'error': 'Invalid payment amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Convert amount to paise
        amount_in_paise = int(payment.amount * 100)

        # Initialize Razorpay Client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_order_{payment.order.id}"
        }
        
        try:
            razorpay_order = client.order.create(data=data)
            
            payment.razorpay_order_id = razorpay_order['id']
            payment.save()
            
            return Response({
                'razorpay_order_id': payment.razorpay_order_id,
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def verify_razorpay_payment(self, request, pk=None):
        payment = self.get_object()
        
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({'error': 'Missing required Razorpay parameters'}, status=status.HTTP_400_BAD_REQUEST)
            
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        try:
            # Verify signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            client.utility.verify_payment_signature(params_dict)
            
            # On success
            payment.razorpay_order_id = razorpay_order_id
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.transaction_id = razorpay_payment_id # Map to transaction_id for consistency
            payment.status = Payment.CustomerStatus.SUCCESS
            payment.customer_payment_status = Payment.CustomerStatus.PAID
            payment.method = Payment.PaymentMethod.ONLINE
            payment.save()
            
            # Update order status
            order = payment.order
            if order.status in ['PENDING', 'ASSIGNED', 'IN_PROGRESS']:
                order.status = 'CONFIRMED'
                order.save()
            
            return Response({'status': 'Payment verified successfully'})
            
        except razorpay.errors.SignatureVerificationError:
            # On failure: Do NOT update status, just return error
            return Response({'error': 'Invalid payment signature'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def fail_payment(self, request, pk=None):
        payment = self.get_object()
        reason = request.data.get('reason', 'Payment failed')
        payment.status = Payment.CustomerStatus.FAILED
        payment.customer_payment_status = Payment.CustomerStatus.FAILED
        payment.verification_notes = reason
        payment.save()
        return Response({'status': 'Payment marked as FAILED'})
