from rest_framework.routers import DefaultRouter
from .views import SellerProfileViewSet, SellerWalletViewSet, WithdrawalRequestViewSet

router = DefaultRouter()
router.register(r'profiles', SellerProfileViewSet, basename='seller-profile')
router.register(r'wallets', SellerWalletViewSet, basename='seller-wallet')
router.register(r'withdrawals', WithdrawalRequestViewSet, basename='withdrawal')

urlpatterns = router.urls
