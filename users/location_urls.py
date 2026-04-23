from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import StateViewSet, CityViewSet, ServiceableCityViewSet, ServiceAvailabilityView

router = SimpleRouter()
router.register(r'states', StateViewSet, basename='state')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'serviceable-cities', ServiceableCityViewSet, basename='serviceable-city')

urlpatterns = [
    path('service-availability/', ServiceAvailabilityView.as_view(), name='service-availability'),
    path('', include(router.urls)),
]
