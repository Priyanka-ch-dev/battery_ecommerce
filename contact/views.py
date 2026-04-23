from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import ContactSettings
from .serializers import ContactSettingsSerializer

class ContactSettingsView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get(self, request):
        settings = ContactSettings.objects.first()
        if not settings:
            # Return empty structure if none exists yet
            return Response({})
        serializer = ContactSettingsSerializer(settings)
        return Response(serializer.data)

    def post(self, request):
        settings = ContactSettings.objects.first()
        if settings:
            serializer = ContactSettingsSerializer(settings, data=request.data)
        else:
            serializer = ContactSettingsSerializer(data=request.data)
            
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED if not settings else status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import ContactMessage
from .serializers import ContactMessageSerializer
from rest_framework import viewsets

class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
