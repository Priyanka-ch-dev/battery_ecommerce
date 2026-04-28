from django.db import models
from django.conf import settings
from orders.models import Order

class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        COD = 'COD', 'Cash on Delivery'
        ONLINE = 'ONLINE', 'Online Payment'

    class CustomerStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COLLECTED = 'COLLECTED', 'Collected'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        PAID = 'PAID', 'Paid' # Keeping for compatibility

    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        VERIFIED = 'VERIFIED', 'Verified'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    
    # New separate tracking statuses
    customer_payment_status = models.CharField(max_length=20, choices=CustomerStatus.choices, default=CustomerStatus.PENDING)
    delivery_payment_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    
    # Sync with a general status for backward compatibility
    status = models.CharField(max_length=20, choices=CustomerStatus.choices, default=CustomerStatus.PENDING)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Razorpay Specific Fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_payments',
        limit_choices_to={'role': 'ADMIN'}
    )
    verification_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.status}"
