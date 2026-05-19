from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, DeliverySlotViewSet

router = DefaultRouter()
router.register(r'delivery-slots', DeliverySlotViewSet, basename='delivery-slot')
router.register(r'', OrderViewSet, basename='order')

urlpatterns = router.urls
