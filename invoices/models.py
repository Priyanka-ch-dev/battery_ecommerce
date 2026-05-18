from django.db import models
from orders.models import Order
from sellers.models import SellerProfile
import uuid

class Invoice(models.Model):
    class PaymentMethod(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        COD = 'COD', 'Cash on Delivery'
        
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'    
        
    invoice_id = models.CharField(max_length=50, unique=True, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='invoices')
    seller = models.ForeignKey(SellerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    seller_name = models.CharField(max_length=255)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    seller_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.ONLINE)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    invoice_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            # Generate a unique invoice ID
            self.invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_id} for Order {self.order.id}"

