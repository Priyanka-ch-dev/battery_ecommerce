from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import CategoryViewSet, BrandViewSet, VehicleViewSet, ProductViewSet, ProductReviewViewSet, ProductImageViewSet, ProductSpecificationViewSet, MakeViewSet, ModelViewSet, ComboProductViewSet

router = SimpleRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'product-images', ProductImageViewSet, basename='product-image')
router.register(r'product-specifications', ProductSpecificationViewSet, basename='product-specification')
router.register(r'reviews', ProductReviewViewSet, basename='product-review')
router.register(r'makes', MakeViewSet, basename='make')
router.register(r'models', ModelViewSet, basename='model')
router.register(r'combos', ComboProductViewSet, basename='combo-product')

urlpatterns = [
    path('types/', ProductViewSet.as_view({'get': 'types'}), name='product-types'),
    path('brands/', ProductViewSet.as_view({'get': 'brands'}), name='product-brands'),
    path('filter/', ProductViewSet.as_view({'get': 'filter'}), name='product-filter'),
    path('', ProductViewSet.as_view({'get': 'list', 'post': 'create'}), name='product-list'),
    path('<int:pk>/', ProductViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='product-detail'),
    path('', include(router.urls)),
]
