from django.db import models
from django.conf import settings
from products.models import Product
from sellers.models import SellerProfile

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        SHIPPED = 'SHIPPED', 'Shipped'
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', 'Out for Delivery'
        DELIVERED = 'DELIVERED', 'Delivered'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUND_REQUESTED = 'REFUND_REQUESTED', 'Refund Requested'
        REFUNDED = 'REFUNDED', 'Refunded'
        COMPLETED = 'COMPLETED','Completed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='deliveries',
        limit_choices_to={'role': 'SELLER'}
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_exchange = models.BooleanField(default=False)
    
    delivery_date = models.DateField(null=True, blank=True)
    delivery_time = models.CharField(max_length=50, null=True, blank=True)
    
    # Store addresses as text to prevent issues if the Address model is changed/deleted
    shipping_address = models.TextField()
    billing_address = models.TextField()
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # GST India
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    is_refunded = models.BooleanField(default=False)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.TextField(blank=True, null=True)

    # Installation Fields
    before_image = models.ImageField(upload_to='installations/before/', null=True, blank=True)
    after_image = models.ImageField(upload_to='installations/after/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    combo_product = models.ForeignKey('products.ComboProduct', on_delete=models.SET_NULL, null=True, blank=True)
    seller = models.ForeignKey(SellerProfile, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at the time of order
    quantity = models.PositiveIntegerField(default=1)
    is_exchange = models.BooleanField(default=False)
    exchange_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Commission storage
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)
    admin_commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    seller_earning = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quantity} of {self.product.name if self.product else 'Deleted Product'}"

class OrderTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_history')
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order.id} - {self.status} at {self.created_at}"
