from core.permissions import IsAdminOrReadOnly, IsAdminUser, IsApprovedSeller
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Brand, Vehicle, Product, ProductReview, ProductImage, ProductSpecification
from .serializers import CategorySerializer, BrandSerializer, VehicleSerializer, ProductSerializer, ProductReviewSerializer, ProductImageSerializer, ProductSpecificationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets,filters,permissions
from rest_framework.parsers import MultiPartParser,FormParser

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['make', 'model', 'year']
    search_fields = ['make', 'model', 'variant', 'registration_number']
    ordering_fields = ['make', 'year']

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active', 'compatible_vehicles']
    search_fields = ['name', 'slug', 'sku', 'description']
    ordering_fields = ['price', 'created_at']
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAdminUser | IsApprovedSeller)()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        if self.request.user.role == 'ADMIN':
            # Admin can specify seller or leave it null
            serializer.save()
        else:
            # Sellers automatically get assigned their own profile
            from sellers.models import SellerProfile
            try:
                profile = self.request.user.seller_profile
                serializer.save(seller=profile)
            except AttributeError:
                # Should not happen due to IsApprovedSeller permission
                serializer.save()

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAdminUser | IsApprovedSeller)()]
        return [permissions.AllowAny()]

class ProductSpecificationViewSet(viewsets.ModelViewSet):
    queryset = ProductSpecification.objects.all()
    serializer_class = ProductSpecificationSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAdminUser | IsApprovedSeller)()]
        return [permissions.AllowAny()]

    @action(detail=False, methods=['get'])
    def battery_finder(self, request):
        reg_number = request.query_params.get('reg_number')
        
        if not reg_number:
            return Response({'error': 'reg_number parameter is required.'}, status=400)
            
        # Simulate external vehicle registration mock API latency
        import time
        time.sleep(1)
        
        try:
            vehicle = Vehicle.objects.get(registration_number=reg_number)
        except Vehicle.DoesNotExist:
            return Response({'error': 'Vehicle not found in mock RTO registry.'}, status=404)
            
        products = self.queryset.filter(compatible_vehicles=vehicle, is_active=True)
        serializer = self.get_serializer(products, many=True)
        
        return Response({
            'vehicle_identified': f"{vehicle.make} {vehicle.model} ({vehicle.year})",
            'compatible_batteries': serializer.data
        })

from core.permissions import IsAdminUser, IsOwnerOrAdmin

class ProductReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['product', 'user', 'rating', 'is_approved']
    search_fields = ['comment', 'user__email', 'product__name']
    ordering_fields = ['created_at', 'rating']

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = ProductReview.objects.all()
        # Non-admins only see approved reviews OR their own reviews
        if not (self.request.user.is_authenticated and self.request.user.role == 'ADMIN'):
            if self.request.user.is_authenticated:
                from django.db.models import Q
                queryset = queryset.filter(Q(is_approved=True) | Q(user=self.request.user))
            else:
                queryset = queryset.filter(is_approved=True)
        return queryset

    def perform_create(self, serializer):
        # Reviews are pending by default
        serializer.save(user=self.request.user, is_approved=False)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.is_approved = True
        review.save()
        return Response({'status': 'review approved', 'is_approved': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        review = self.get_object()
        review.is_approved = False
        review.save()
        return Response({'status': 'review rejected', 'is_approved': False})
