from django.shortcuts import render
from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Brand, Product, ProductReview, ProductImage, ProductSpecification, Make, VehicleModel, ComboProduct, ComboProductImage, ComboProductSpecification, Vehicle
from .serializers import (
    CategorySerializer, BrandSerializer, ProductSerializer, 
    ProductReviewSerializer, ProductImageSerializer, ProductSpecificationSerializer,
    MakeSerializer, ModelSerializer, ComboProductSerializer, VehicleSerializer,ComboProductImageSerializer,ComboProductSpecificationSerializer,
    UnifiedProductSerializer
)
from core.permissions import IsAdminOrReadOnly, IsAdminUser, IsApprovedSeller

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']

class MakeViewSet(viewsets.ModelViewSet):
    queryset = Make.objects.all()
    serializer_class = MakeSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name']
    ordering_fields = ['name']

class ModelViewSet(viewsets.ModelViewSet):
    queryset = VehicleModel.objects.all()
    serializer_class = ModelSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['make']
    search_fields = ['name']
    ordering_fields = ['name']

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['make', 'model', 'year']
    search_fields = ['make', 'model', 'variant', 'registration_number']
    ordering_fields = ['make', 'year']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active', 'make', 'model', 'state', 'city']
    search_fields = ['name', 'slug', 'sku', 'description']
    ordering_fields = ['price', 'created_at', 'stock']

    def get_serializer_class(self):
        if self.action in ['list', 'filter']:
            return UnifiedProductSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all().prefetch_related('category', 'brand', 'make', 'model', 'state', 'city').select_related('seller')
        if not (self.request.user.is_authenticated and self.request.user.role == 'ADMIN'):
            queryset = queryset.filter(is_active=True)
        return queryset

    def list(self, request, *args, **kwargs):
        # Get filtered products
        product_qs = self.filter_queryset(self.get_queryset())
        
        # Get filtered combos
        combo_qs = ComboProduct.objects.all().prefetch_related(
            'category', 'brand', 'state', 'city', 'make', 'model', 'images', 'specifications'
        ).select_related('inverter', 'battery', 'seller')
        if not (request.user.is_authenticated and request.user.role in ['ADMIN', 'SELLER']):
            combo_qs = combo_qs.filter(is_active=True)
            
        # Manually apply same filters to combo_qs
        # Since filterset_fields are same, we can try to use filter_queryset if we trick it
        # But safer to just apply them or use a separate filter class.
        # Actually, filter_queryset uses self.filter_backends
        
        # We'll use a temporary view-like object to filter combos
        original_queryset = self.queryset
        self.queryset = ComboProduct.objects.all()
        filtered_combo_qs = self.filter_queryset(combo_qs)
        self.queryset = original_queryset # Restore
        
        # Combine
        combined = list(product_qs) + list(filtered_combo_qs)
        
        # Sort by created_at desc (standard for listings)
        combined.sort(key=lambda x: x.created_at, reverse=True)
        
        # Paginate
        page = self.paginate_queryset(combined)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(combined, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        # Try Product
        product = Product.objects.filter(pk=pk).first()
        if product:
            serializer = ProductSerializer(product, context={'request': request})
            return Response(serializer.data)
        
        # Try ComboProduct
        combo = ComboProduct.objects.filter(pk=pk).first()
        if combo:
            serializer = ComboProductSerializer(combo, context={'request': request})
            return Response(serializer.data)
            
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    def perform_create(self, serializer):
        images = self.request.FILES.getlist('uploaded_images')
        primary_index = self.request.data.get('primary_image_index')
        product = serializer.save()
        
        for i, image in enumerate(images):
            is_primary = str(i) == str(primary_index)
            ProductImage.objects.create(product=product, image=image, is_primary=is_primary)

    def perform_update(self, serializer):
        images = self.request.FILES.getlist('uploaded_images')
        primary_index = self.request.data.get('primary_image_index')
        product = serializer.save()
        
        if images:
            for i, image in enumerate(images):
                is_primary = str(i) == str(primary_index)
                ProductImage.objects.create(product=product, image=image, is_primary=is_primary)

    @action(detail=False, methods=['get'])
    def filter(self, request):
        make_ids = request.query_params.getlist('make_id')
        model_ids = request.query_params.getlist('model_id')
        state_ids = request.query_params.getlist('state_id')
        city_ids = request.query_params.getlist('city_id')
        
        def is_valid(vals):
            return vals and any(str(v).lower() not in ['null', 'undefined', 'none', ''] for v in vals)

        product_qs = self.get_queryset()
        combo_qs = ComboProduct.objects.all().prefetch_related(
            'category', 'brand', 'state', 'city', 'make', 'model', 'images', 'specifications'
        ).select_related('inverter', 'battery', 'seller')
        if not (request.user.is_authenticated and request.user.role in ['ADMIN', 'SELLER']):
            combo_qs = combo_qs.filter(is_active=True)

        if is_valid(make_ids):
            product_qs = product_qs.filter(make__id__in=make_ids)
            combo_qs = combo_qs.filter(make__id__in=make_ids)
        if is_valid(model_ids):
            product_qs = product_qs.filter(model__id__in=model_ids)
            combo_qs = combo_qs.filter(model__id__in=model_ids)
        if is_valid(state_ids):
            product_qs = product_qs.filter(state__id__in=state_ids)
            combo_qs = combo_qs.filter(state__id__in=state_ids)
        if is_valid(city_ids):
            product_qs = product_qs.filter(city__id__in=city_ids)
            combo_qs = combo_qs.filter(city__id__in=city_ids)
            
        combined = list(product_qs.distinct()) + list(combo_qs.distinct())
        combined.sort(key=lambda x: x.created_at, reverse=True)
        
        serializer = self.get_serializer(combined, many=True)
        return Response(serializer.data)

class ProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'is_approved']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.is_approved = True
        review.save()
        return Response({'status': 'review approved', 'is_approved': True})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        review = self.get_object()
        review.is_approved = False
        review.save()
        return Response({'status': 'review rejected', 'is_approved': False})

class ComboProductViewSet(viewsets.ModelViewSet):
    queryset = ComboProduct.objects.all()
    serializer_class = ComboProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'state', 'city', 'make', 'model']
    search_fields = ['name', 'slug', 'sku']
    ordering_fields = ['price', 'created_at']

    def get_queryset(self):
        queryset = ComboProduct.objects.all().prefetch_related(
            'category', 'brand', 'state', 'city', 'make', 'model'
        ).select_related(
            'inverter', 'battery', 'seller'
        )
        if self.action == 'list' and not (self.request.user.is_authenticated and self.request.user.role in ['ADMIN', 'SELLER']):
            return queryset.filter(is_active=True)
        return queryset

    @action(detail=False, methods=['get'])
    def filter(self, request):
        make_ids = request.query_params.getlist('make_id')
        model_ids = request.query_params.getlist('model_id')
        state_ids = request.query_params.getlist('state_id')
        city_ids = request.query_params.getlist('city_id')
        
        queryset = self.get_queryset().filter(is_active=True)
        
        def is_valid(vals):
            return vals and any(str(v).lower() not in ['null', 'undefined', 'none', ''] for v in vals)

        if is_valid(make_ids):
            queryset = queryset.filter(make__id__in=make_ids)
        if is_valid(model_ids):
            queryset = queryset.filter(model__id__in=model_ids)
        if is_valid(state_ids):
            queryset = queryset.filter(state__id__in=state_ids)
        if is_valid(city_ids):
            queryset = queryset.filter(city__id__in=city_ids)
            
        queryset = queryset.distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        images = self.request.FILES.getlist('uploaded_images')
        primary_index = self.request.data.get('primary_image_index')
        instance = serializer.save()
        
        for i, image in enumerate(images):
            is_primary = str(i) == str(primary_index)
            ComboProductImage.objects.create(combo_product=instance, image=image, is_primary=is_primary)
            if is_primary:
                instance.image = image
                instance.save()

    def perform_update(self, serializer):
        images = self.request.FILES.getlist('uploaded_images')
        primary_index = self.request.data.get('primary_image_index')
        instance = serializer.save()

        if images:
            for i, image in enumerate(images):
                is_primary = str(i) == str(primary_index)
                ComboProductImage.objects.create(combo_product=instance, image=image, is_primary=is_primary)
                if is_primary:
                    instance.image = image
                    instance.save()

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

class ProductSpecificationViewSet(viewsets.ModelViewSet):
    queryset = ProductSpecification.objects.all()
    serializer_class = ProductSpecificationSerializer
    permission_classes = [IsAdminOrReadOnly]

class ComboProductImageViewSet(viewsets.ModelViewSet):
    queryset = ComboProductImage.objects.all()
    serializer_class = ComboProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

class ComboProductSpecificationViewSet(viewsets.ModelViewSet):
    queryset = ComboProductSpecification.objects.all()
    serializer_class = ComboProductSpecificationSerializer
    permission_classes = [IsAdminOrReadOnly]
