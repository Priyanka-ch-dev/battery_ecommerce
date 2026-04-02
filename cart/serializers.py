from rest_framework import serializers
from .models import Coupon, Cart, CartItem
from products.serializers import ProductSerializer

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = CartItem
        fields = '__all__'
        read_only_fields = ['cart']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)
        if product and product.stock < quantity:
            raise serializers.ValidationError({"quantity": f"Only {product.stock} items left in stock for {product.name}."})
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ['user', 'session_key']
