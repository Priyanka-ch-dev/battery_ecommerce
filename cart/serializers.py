from rest_framework import serializers
from .models import Coupon, Cart, CartItem
from products.serializers import ProductSerializer

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source='product', read_only=True)
    combo_product_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = '__all__'
        read_only_fields = ['cart']

    def get_combo_product_detail(self, obj):
        if obj.combo_product:
            from products.serializers import ComboProductSerializer
            return ComboProductSerializer(obj.combo_product).data
        return None

    def validate(self, data):
        product = data.get('product')
        combo_product = data.get('combo_product')
        quantity = data.get('quantity', 1)

        if not product and not combo_product:
            raise serializers.ValidationError("Either product or combo_product must be provided.")
        
        if product and combo_product:
            raise serializers.ValidationError("Cannot provide both product and combo_product.")

        if product and product.stock < quantity:
            raise serializers.ValidationError({"quantity": f"Only {product.stock} items left in stock for {product.name}."})
        
        if combo_product and combo_product.stock < quantity:
            raise serializers.ValidationError({"quantity": f"Only {combo_product.stock} items left in stock for {combo_product.name}."})

        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ['user', 'session_key']
