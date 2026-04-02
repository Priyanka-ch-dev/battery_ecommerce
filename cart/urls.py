from rest_framework.routers import DefaultRouter
from .views import CartViewSet, CartItemViewSet, CouponViewSet

router = DefaultRouter()
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'items', CartItemViewSet, basename='cart-item')
router.register(r'coupons', CouponViewSet, basename='coupon')

urlpatterns = router.urls
