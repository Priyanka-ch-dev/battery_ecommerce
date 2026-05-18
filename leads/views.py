from rest_framework import viewsets, permissions
from .models import Lead
from .serializers import LeadSerializer
from core.permissions import IsAdminUser, IsOwnerOrAdmin

class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    queryset = Lead.objects.all()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.AllowAny()]
        else:
            # Action 'list' or 'retrieve' (GET) -> Admin only!
            return [IsAdminUser()]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

    def get_queryset(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return Lead.objects.all()
            
        user = self.request.user
        if not user.is_authenticated:
            return Lead.objects.none()
            
        if getattr(user, 'role', '') == 'ADMIN' or getattr(user, 'is_superuser', False):
            return Lead.objects.all()
            
        return Lead.objects.filter(user=user)
