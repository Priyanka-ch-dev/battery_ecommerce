from rest_framework import viewsets, permissions, generics
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Address, Wishlist, State, City
from .serializers import UserSerializer, AddressSerializer, WishlistSerializer, CustomTokenObtainPairSerializer, RegisterSerializer, StateSerializer, CitySerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['role']

    def get_queryset(self):
        if self.request.user.role == User.Role.ADMIN:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

from core.permissions import IsOwnerOrAdmin

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user', 'address_type', 'is_default']

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = Address.objects.all() if self.request.user.role == User.Role.ADMIN else Address.objects.filter(user=self.request.user)
        
        # Explicitly handle user filtering for Admins
        user_id = self.request.query_params.get('user')
        if user_id and self.request.user.role == User.Role.ADMIN:
            queryset = queryset.filter(user_id=user_id)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role="CUSTOMER")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


from rest_framework.views import APIView
from rest_framework.response import Response

class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from core.permissions import IsAdminUser
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.AllowAny()]

class CityViewSet(viewsets.ModelViewSet):
    serializer_class = CitySerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from core.permissions import IsAdminUser
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        state_id = self.request.query_params.get('state_id')
        if state_id:
            return City.objects.filter(state_id=state_id)
        return City.objects.all()

from .models import ServiceableCity
from .serializers import ServiceableCitySerializer

class ServiceableCityViewSet(viewsets.ModelViewSet):
    queryset = ServiceableCity.objects.all()
    serializer_class = ServiceableCitySerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from core.permissions import IsAdminUser
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.AllowAny()]

class ServiceAvailabilityView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            from core.permissions import IsAdminUser
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.AllowAny()]

    def get(self, request):
        """Public: Check if a city is serviceable"""
        city_id = request.query_params.get('city_id')
        city_name = request.query_params.get('city')
        state_id = request.query_params.get('state_id')
        state_name = request.query_params.get('state')
        
        query = ServiceableCity.objects.all()
        if city_id:
            query = query.filter(city_id=city_id)
        elif city_name:
            query = query.filter(city__name__iexact=city_name)
            
        # Apply State filtering if provided (supports ID or name)
        if state_id:
            query = query.filter(city__state_id=state_id)
        elif state_name:
            query = query.filter(city__state__name__iexact=state_name)

        if query and query.exists():
            obj = query.first()
            return Response({
                "service_available": obj.is_service_available,
                "message": "Service available" if obj.is_service_available else "City not serviceable"
            })
        
        return Response({
            "service_available": False,
            "message": "City not serviceable"
        }, status=200)

    def post(self, request):
        """Admin: Create a new serviceable city record"""
        serializer = ServiceableCitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
