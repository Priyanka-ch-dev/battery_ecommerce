from django.db import models
from sellers.models import SellerProfile
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

class Brand(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name

class Make(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class VehicleModel(models.Model):
    make = models.ForeignKey(Make, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('make', 'name')

    def __str__(self):
        return f"{self.make.name} {self.name}"

class Vehicle(models.Model):
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    variant = models.CharField(max_length=100, blank=True, null=True)
    registration_number = models.CharField(max_length=20, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year}) {self.variant}"

class Product(models.Model):
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    
    # Direct fields for Battery Finder and Location-based filtering
    make = models.ForeignKey(Make, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    model = models.ForeignKey(VehicleModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    state = models.ForeignKey('users.State', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    city = models.ForeignKey('users.City', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Exchange Feature
    exchange_available = models.BooleanField(default=False)
    exchange_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    special_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    warranty = models.CharField(max_length=255, null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Battery Finder Relation
    compatible_vehicles = models.ManyToManyField(Vehicle, related_name='compatible_batteries', blank=True)

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    key = models.CharField(max_length=100) # e.g., 'Ah', 'Voltage', 'Warranty'
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.product.name} - {self.key}: {self.value}"

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name} ({'Approved' if self.is_approved else 'Pending'})"

class ComboProduct(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='combos/', blank=True, null=True)
    inverter = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inverter_combos')
    battery = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='battery_combos')
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='combos', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def stock(self):
        # Combo stock is the minimum of its components
        return min(self.inverter.stock, self.battery.stock)

    def __str__(self):
        return self.name

class SearchQuery(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.query
