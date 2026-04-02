from rest_framework import viewsets, permissions
from .models import SellerProfile, SellerWallet, WithdrawalRequest
from .serializers import SellerProfileSerializer, SellerWalletSerializer, WithdrawalRequestSerializer

class SellerProfileViewSet(viewsets.ModelViewSet):
    queryset = SellerProfile.objects.all()
    serializer_class = SellerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_approved']
    search_fields = ['business_name', 'gst_number']
    ordering_fields = ['commission_rate']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SellerWalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SellerWalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['balance', 'total_earned']

    def get_queryset(self):
        return SellerWallet.objects.filter(seller__user=self.request.user)

class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status']
    ordering_fields = ['requested_at', 'amount']

    def get_queryset(self):
        return WithdrawalRequest.objects.filter(seller__user=self.request.user)

    def perform_create(self, serializer):
        seller_profile = SellerProfile.objects.get(user=self.request.user)
        serializer.save(seller=seller_profile)
