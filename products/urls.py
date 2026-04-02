from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BrandViewSet, VehicleViewSet, ProductViewSet, ProductReviewViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'catalog', ProductViewSet, basename='product')
router.register(r'reviews', ProductReviewViewSet, basename='product-review')

urlpatterns = router.urls
