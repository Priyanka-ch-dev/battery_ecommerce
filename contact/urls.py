from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactSettingsView, ContactMessageViewSet

router = DefaultRouter()
router.register(r'messages', ContactMessageViewSet, basename='contact-message')

urlpatterns = [
    path('contact-settings/', ContactSettingsView.as_view(), name='contact-settings'),
    path('', include(router.urls)),
]
