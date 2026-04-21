from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import CategoryViewSet, BrandViewSet, VehicleViewSet, ProductViewSet, ProductReviewViewSet, ProductImageViewSet, ProductSpecificationViewSet

router = SimpleRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'product-images', ProductImageViewSet, basename='product-image')
router.register(r'product-specifications', ProductSpecificationViewSet, basename='product-specification')
router.register(r'reviews', ProductReviewViewSet, basename='product-review')

urlpatterns = [
    path('', ProductViewSet.as_view({'get': 'list', 'post': 'create'}), name='product-list'),
    path('<int:pk>/', ProductViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='product-detail'),
    path('', include(router.urls)),
]
