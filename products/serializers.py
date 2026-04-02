from rest_framework import serializers
from .models import Category, Brand, Vehicle, Product, ProductImage, ProductSpecification, ProductReview

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

    class Meta:
        model = ProductReview
        fields = '__all__'
        read_only_fields = ['user']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    compatible_vehicles_details = VehicleSerializer(source='compatible_vehicles', many=True, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['seller']

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
