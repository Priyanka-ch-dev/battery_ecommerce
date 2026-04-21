from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Payment
from .serializers import PaymentSerializer
from core.permissions import IsAdminUser

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        payment_type = self.request.query_params.get('type')
        
        if user.role == 'ADMIN':
            queryset = Payment.objects.all()
            if payment_type == 'cod':
                queryset = queryset.filter(method=Payment.PaymentMethod.COD)
            elif payment_type == 'online':
                queryset = queryset.filter(method=Payment.PaymentMethod.ONLINE)
            return queryset
        elif user.role == 'CUSTOMER':
            return Payment.objects.filter(order__user=user)
        # Sellers should have no access to payments
        return Payment.objects.none()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify_payment(self, request, pk=None):
        payment = self.get_object()
        transaction_id = request.data.get('transaction_id')
        notes = request.data.get('notes')
        
        if not transaction_id:
            return Response({'error': 'transaction_id is required for verification'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment.status = Payment.Status.PAID
        payment.transaction_id = transaction_id
        payment.verified_by = request.user
        payment.verification_notes = notes
        payment.save()
        
        return Response({'status': 'Payment verified and status updated to PAID'})
