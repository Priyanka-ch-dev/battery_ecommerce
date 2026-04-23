from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from products.views import CategoryViewSet, BrandViewSet, ProductReviewViewSet
from services.views import ServiceBookingViewSet
from sellers.views import SellerProfileViewSet
from reports.views import ReportsViewSet
from cart.views import CouponViewSet
from rest_framework.routers import DefaultRouter
from users.views import CustomTokenObtainPairView,CustomerViewSet
from contact.views import ContactSettingsView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'reviews', ProductReviewViewSet, basename='review')
router.register(r'installations', ServiceBookingViewSet, basename='installation')
router.register(r'sellers', SellerProfileViewSet, basename='seller')
router.register(r'reports', ReportsViewSet, basename='report')
router.register(r'coupons', CouponViewSet, basename='core-coupon')
router.register(r'customers', CustomerViewSet,basename='customer')


from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... existing paths ...
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('admin/', admin.site.urls),
    path('api/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/contact-settings/', ContactSettingsView.as_view(), name='api-contact-settings'),
    path('api/', include(router.urls)), # Top-level categories, reviews, etc.
    path('api/users/', include('users.urls')),
    path('api/sellers/', include('sellers.urls')),
    path('api/seller/', include('sellers.urls')),
    path('api/products/', include('products.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/services/', include('services.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/contact/', include('contact.urls')),
    path('api/locations/', include('users.location_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

