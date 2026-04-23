from rest_framework.routers import DefaultRouter
from .views import SellerProfileViewSet, SellerWalletViewSet, WithdrawalRequestViewSet, SettlementViewSet

router = DefaultRouter()
router.register(r'profiles', SellerProfileViewSet, basename='seller-profile')
router.register(r'wallet', SellerWalletViewSet, basename='seller-wallet')
router.register(r'withdrawals', WithdrawalRequestViewSet, basename='withdrawal-request')
router.register(r'settlements', SettlementViewSet, basename='settlement')

urlpatterns = router.urls
