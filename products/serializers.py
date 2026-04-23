from rest_framework import serializers
from .models import Category, Brand, Vehicle, Product, ProductImage, ProductSpecification, ProductReview, Make, VehicleModel, ComboProduct

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class MakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Make
        fields = ['id', 'name']

class ModelSerializer(serializers.ModelSerializer):
    make = serializers.PrimaryKeyRelatedField(queryset=Make.objects.all())

    class Meta:
        model = VehicleModel
        fields = ['id', 'name', 'make']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = '__all__'

class ProductReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = ProductReview
        fields = '__all__'
        read_only_fields = ['user', 'is_approved']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    compatible_vehicles_details = VehicleSerializer(source='compatible_vehicles', many=True, read_only=True)

    category_name = serializers.ReadOnlyField(source='category.name')
    brand_name = serializers.ReadOnlyField(source='brand.name')
    make_name = serializers.ReadOnlyField(source='make.name')
    model_name = serializers.ReadOnlyField(source='model.name')
    state_name = serializers.ReadOnlyField(source='state.name')
    city_name = serializers.ReadOnlyField(source='city.name')
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'description', 'price', 'special_price', 
            'stock', 'is_active', 'warranty', 'view_count', 'created_at',
            'category', 'category_name', 'brand', 'brand_name', 'seller',
            'make', 'make_name', 'model', 'model_name', 'state', 'state_name', 
            'city', 'city_name', 'image', 'exchange_available', 'exchange_discount',
            'images', 'specifications', 'reviews', 'compatible_vehicles_details'
        ]
        read_only_fields = ['seller']

    def get_image(self, obj):
        # Prefer primary image, fall back to first image
        primary_image = obj.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = obj.images.first()
        
        if primary_image and primary_image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        return None

    def __init__(self, *args, **kwargs):
        super(ProductSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Using string comparison for role to avoid early loading of User model if not already loaded
            if getattr(request.user, 'role', None) == 'ADMIN':
                from sellers.models import SellerProfile
                self.fields['seller'].read_only = False
                self.fields['seller'].required = False
                self.fields['seller'].queryset = SellerProfile.objects.all()

class ComboProductSerializer(serializers.ModelSerializer):
    inverter_name = serializers.ReadOnlyField(source='inverter.name')
    battery_name = serializers.ReadOnlyField(source='battery.name')

    class Meta:
        model = ComboProduct
        fields = ['id', 'name', 'price', 'image', 'inverter', 'battery', 'inverter_name', 'battery_name', 'is_active', 'created_at']

    def validate(self, data):
        inverter = data.get('inverter')
        battery = data.get('battery')
        
        if inverter and battery and inverter == battery:
            raise serializers.ValidationError("Inverter and Battery cannot be the same product.")
        return data
