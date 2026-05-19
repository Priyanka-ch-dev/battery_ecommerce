from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AddressViewSet, WishlistViewSet,CustomerViewSet

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'wishlists', WishlistViewSet, basename='wishlist')
router.register(r'', UserViewSet, basename='user')


from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView, RegisterView, VerifyRegistrationView, ResetPasswordView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-registration/', VerifyRegistrationView.as_view(), name='verify-registration'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
] + router.urls
