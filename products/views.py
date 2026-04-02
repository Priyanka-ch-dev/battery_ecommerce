from rest_framework import viewsets, permissions, filters, serializers
from core.permissions import IsAdminUserOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Brand, Vehicle, Product, ProductReview
from .serializers import CategorySerializer, BrandSerializer, VehicleSerializer, ProductSerializer, ProductReviewSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filterset_fields = ['make', 'model', 'year']
    search_fields = ['make', 'model', 'variant', 'registration_number']
    ordering_fields = ['make', 'year']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active', 'compatible_vehicles']
    search_fields = ['name', 'slug', 'sku', 'description']
    ordering_fields = ['price', 'created_at']
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'ADMIN':
            # Admin can create products without a seller profile
            # If 'seller' is passed in data, it will be used (now writable for admins in serializer)
            serializer.save()
        else:
            try:
                # Check if the user has a SellerProfile (related_name is 'seller_profile')
                seller = user.seller_profile
                serializer.save(seller=seller)
            except AttributeError:
                # This happens if request.user has no 'seller_profile' (e.g. non-admin without profile)
                raise serializers.ValidationError({
                    "detail": "User has no associated SellerProfile. A seller profile is required to create products for sellers."
                })


    def get_permissions(self):
        from core.permissions import IsSellerOrAdmin, IsProductOwnerOrAdmin
        if self.action == 'create':
            return [IsSellerOrAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsProductOwnerOrAdmin()]
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

class ProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at', 'rating']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
