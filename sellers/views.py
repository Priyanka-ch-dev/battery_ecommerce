from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import SellerProfile, SellerWallet, WithdrawalRequest, Settlement, WalletTransaction
from .serializers import SellerProfileSerializer, SellerWalletSerializer, WithdrawalRequestSerializer, SettlementSerializer
from rest_framework.decorators import action
from core.permissions import IsAdminUser, IsApprovedSeller

class SellerProfileViewSet(viewsets.ModelViewSet):
    queryset = SellerProfile.objects.select_related('user').all()
    serializer_class = SellerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status']
    search_fields = ['business_name', 'gst_number', 'user__email']
    ordering_fields = ['commission_rate']

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        try:
            seller = self.request.user.seller_profile
        except SellerProfile.DoesNotExist:
            return Response({'error': 'Seller profile not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if request.method == 'GET':
            serializer = self.get_serializer(seller)
            return Response(serializer.data)
        
        # PATCH - Update details
        serializer = self.get_serializer(seller, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def manually_create_seller(self, request):
        from .serializers import AdminSellerCreateSerializer
        serializer = AdminSellerCreateSerializer(data=request.data)
        if serializer.is_valid():
            seller_profile = serializer.save()
            return Response(SellerProfileSerializer(seller_profile).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_status(self, request, pk=None):
        seller = self.get_object()
        new_status = request.data.get('status')
        if new_status not in [SellerProfile.Status.APPROVED, SellerProfile.Status.REJECTED]:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        seller.status = new_status
        seller.save()
        return Response({'message': f'Seller status updated to {new_status}'})

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        seller = self.get_object()
        seller.status = SellerProfile.Status.APPROVED
        seller.save()
        return Response({'status': 'Seller approved successfully', 'is_approved': True})

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        seller = self.get_object()
        seller.status = SellerProfile.Status.REJECTED
        seller.save()
        return Response({'status': 'Seller rejected/suspended', 'is_approved': False})

class SellerWalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SellerWalletSerializer
    permission_classes = [IsApprovedSeller]
    ordering_fields = ['balance', 'total_earned']

    def get_queryset(self):
        return SellerWallet.objects.filter(seller__user=self.request.user)

class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsApprovedSeller]
    filterset_fields = ['status']
    ordering_fields = ['requested_at', 'amount']

    def get_queryset(self):
        return WithdrawalRequest.objects.filter(seller__user=self.request.user)

    def perform_create(self, serializer):
        seller_profile = SellerProfile.objects.get(user=self.request.user)
        serializer.save(seller=seller_profile)

class SettlementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Admin to process weekly settlements.
    POST /api/settlements/ {seller: ID}
    """
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        seller = serializer.validated_data['seller']
        # Find all PENDING CREDIT transactions for this seller
        pending_txs = WalletTransaction.objects.filter(
            wallet__seller=seller,
            status=WalletTransaction.Status.PENDING,
            transaction_type=WalletTransaction.Type.CREDIT
        )
        
        if not pending_txs.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No pending earnings for this seller.")
            
        total_amount = sum(tx.amount for tx in pending_txs)
        
        # Create Settlement
        settlement = serializer.save(amount=total_amount, status=Settlement.Status.COMPLETED)
        settlement.transactions.set(pending_txs)
        
        # Update wallet balance and mark transactions as SETTLED
        wallet = seller.wallet
        for tx in pending_txs:
            tx.status = WalletTransaction.Status.SETTLED
            tx.save()
            wallet.balance += tx.amount
            wallet.total_earned += tx.amount
        
        wallet.save()
        
        # Add timestamp
        from django.utils import timezone
        settlement.settled_at = timezone.now()
        settlement.save()
