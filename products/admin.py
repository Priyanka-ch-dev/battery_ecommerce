from django.contrib import admin
from .models import Category, Brand, Vehicle, Product, ProductImage, ProductSpecification, ProductReview, Make, VehicleModel, ComboProduct

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['make', 'model', 'year', 'variant', 'registration_number']
    search_fields = ['make', 'model', 'registration_number']

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'brand']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['compatible_vehicles']
    inlines = [ProductImageInline, ProductSpecificationInline]

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']

class VehicleModelInline(admin.TabularInline):
    model = VehicleModel
    extra = 1

@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']
    ordering = ['name']
    inlines = [VehicleModelInline]

@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'make']
    list_filter = ['make']
    search_fields = ['name']
    ordering = ['name']

@admin.register(ComboProduct)
class ComboProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'inverter', 'battery', 'is_active', 'created_at']
    list_filter = ['is_active', 'inverter', 'battery']
    search_fields = ['name']
