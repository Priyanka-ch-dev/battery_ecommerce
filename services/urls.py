from rest_framework.routers import DefaultRouter
from .views import ServiceAvailabilityViewSet, ServiceBookingViewSet

router = DefaultRouter()
router.register(r'availability', ServiceAvailabilityViewSet, basename='service-availability')
router.register(r'bookings', ServiceBookingViewSet, basename='service-booking')

urlpatterns = router.urls
