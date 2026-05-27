from rest_framework import serializers
from .models import Category, Brand, Vehicle, Product, ProductImage, ProductSpecification, ProductReview, Make, VehicleModel, ComboProduct, ComboProductSpecification, ComboProductImage

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
        read_only_fields = ['user', 'is_approved', 'status']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    compatible_vehicles_details = VehicleSerializer(source='compatible_vehicles', many=True, read_only=True)

    category_names = serializers.SerializerMethodField()
    brand_names = serializers.SerializerMethodField()
    make_names = serializers.SerializerMethodField()
    model_names = serializers.SerializerMethodField()
    state_names = serializers.SerializerMethodField()
    city_names = serializers.SerializerMethodField()
    pincode_names = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()

    def get_product_type(self, obj):
        return 'single'

    def get_reviews(self, obj):
        # Only return approved reviews on the public product views
        approved_reviews = obj.reviews.filter(status=obj.reviews.model.Status.APPROVED)
        return ProductReviewSerializer(approved_reviews, many=True, context=self.context).data

    def get_category_names(self, obj):
        return [c.name for c in obj.category.all()]

    def get_brand_names(self, obj):
        return [b.name for b in obj.brand.all()]

    def get_make_names(self, obj):
        return [m.name for m in obj.make.all()]

    def get_model_names(self, obj):
        return [m.name for m in obj.model.all()]

    def get_state_names(self, obj):
        return [s.name for s in obj.state.all()]

    def get_city_names(self, obj):
        return [c.name for c in obj.city.all()]

    def get_pincode_names(self, obj):
        return [p.pincode for p in obj.pincodes.all()]

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'description', 'price', 'special_price', 
            'stock', 'is_active', 'warranty', 'view_count', 'created_at',
            'category', 'category_names', 'brand', 'brand_names', 'seller',
            'make', 'make_names', 'model', 'model_names', 'state', 'state_names', 
            'city', 'city_names', 'pincodes', 'pincode_names', 'image', 'exchange_available', 'exchange_discount',
            'images', 'specifications', 'reviews', 'compatible_vehicles_details', 'product_type'
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

    def validate(self, data):
        makes = data.get('make', [])
        models = data.get('model', [])
        if makes and not models:
            raise serializers.ValidationError({"model": "At least one model is required if make is provided."})
        if models and not makes:
            raise serializers.ValidationError({"make": "At least one make is required if model is provided."})
        return data

class ComboProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComboProductSpecification
        fields = ['id', 'combo_product', 'key', 'value']
        extra_kwargs = {'combo_product': {'required': False}}

class ComboProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComboProductImage
        fields = ['id', 'combo_product', 'image', 'is_primary']
        extra_kwargs = {'combo_product': {'required': False}}

class ComboProductSerializer(serializers.ModelSerializer):
    inverter_name = serializers.ReadOnlyField(source='inverter.name')
    battery_name = serializers.ReadOnlyField(source='battery.name')
    state_names = serializers.SerializerMethodField()
    city_names = serializers.SerializerMethodField()
    pincode_names = serializers.SerializerMethodField()
    make_names = serializers.SerializerMethodField()
    model_names = serializers.SerializerMethodField()
    category_names = serializers.SerializerMethodField()
    brand_names = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()

    def get_product_type(self, obj):
        return 'combo'

    def get_stock(self, obj):
        """Return effective stock as min of component stocks."""
        try:
            return min(obj.inverter.stock, obj.battery.stock)
        except Exception:
            return 0

    def get_image(self, obj):
        """Return absolute URL of primary image, with fallback chain."""
        request = self.context.get('request')
        # 1. Try images related set (preferred source of truth)
        primary_image = obj.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = obj.images.first()
        if primary_image and primary_image.image:
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        # 2. Fallback to the model's direct image field
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_category_names(self, obj):
        return [c.name for c in obj.category.all()]

    def get_brand_names(self, obj):
        return [b.name for b in obj.brand.all()]

    def get_make_names(self, obj):
        return [m.name for m in obj.make.all()]

    def get_model_names(self, obj):
        return [m.name for m in obj.model.all()]

    def get_state_names(self, obj):
        return [s.name for s in obj.state.all()]

    def get_city_names(self, obj):
        return [c.name for c in obj.city.all()]

    def get_pincode_names(self, obj):
        return [p.pincode for p in obj.pincodes.all()]

    compatible_vehicles_details = VehicleSerializer(source='compatible_vehicles', many=True, read_only=True)
    specifications = ComboProductSpecificationSerializer(many=True, read_only=True)
    images = ComboProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ComboProduct
        fields = [
            'id', 'name', 'slug', 'sku', 'price', 'special_price', 'description', 'image', 'inverter', 'battery',
            'inverter_name', 'battery_name', 'warranty', 'is_active', 'created_at', 'view_count', 'stock',
            'category', 'category_names', 'brand', 'brand_names',
            'state', 'state_names', 'city', 'city_names', 'pincodes', 'pincode_names', 'make', 'make_names',
            'model', 'model_names', 'compatible_vehicles', 'compatible_vehicles_details',
            'exchange_available', 'exchange_discount',
            'specifications', 'images', 'product_type'
        ]
        read_only_fields = ['stock']

    def validate(self, data):
        inverter = data.get('inverter')
        battery = data.get('battery')
        
        if inverter and battery and inverter == battery:
            raise serializers.ValidationError("Inverter and Battery cannot be the same product.")
            
        makes = data.get('make', [])
        models = data.get('model', [])
        if makes and not models:
            raise serializers.ValidationError({"model": "At least one model is required if make is provided."})
        if models and not makes:
            raise serializers.ValidationError({"make": "At least one make is required if model is provided."})
            
        return data

class UnifiedProductSerializer(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(instance, Product):
            return ProductSerializer(instance, context=self.context).data
        elif isinstance(instance, ComboProduct):
            return ComboProductSerializer(instance, context=self.context).data
        return super().to_representation(instance)
