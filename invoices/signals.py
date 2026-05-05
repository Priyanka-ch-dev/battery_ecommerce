from django.db.models.signals import post_save
from django.dispatch import receiver
from payments.models import Payment
from invoices.models import Invoice

@receiver(post_save, sender=Payment)
def generate_invoice_on_payment(sender, instance, created, **kwargs):
    order = instance.order
    
    # Determine payment status
    # In Payment model: CustomerStatus.SUCCESS, PAID, COLLECTED (COD)
    is_paid = instance.status in ['SUCCESS', 'PAID'] or (instance.method == 'COD' and instance.status == 'COLLECTED')
    payment_status = 'PAID' if is_paid else 'PENDING'

    # If invoices already exist for this order, just update their payment status
    invoices = Invoice.objects.filter(order=order)
    if invoices.exists():
        invoices.update(
            payment_method=instance.method,
            payment_status=payment_status
        )
        return

    # Group order items by seller to create one invoice per seller
    seller_items = {}
    for item in order.items.all():
        seller = item.seller
        if seller not in seller_items:
            seller_items[seller] = []
        seller_items[seller].append(item)

    for seller, items in seller_items.items():
        total_amount = sum(item.total_amount for item in items)
        commission_amount = sum(item.admin_commission_amount for item in items)
        seller_amount = sum(item.seller_earning for item in items)
        
        seller_name = seller.business_name if seller else "Admin/Company"
        customer_name = f"{order.user.first_name} {order.user.last_name}".strip()
        if not customer_name:
            customer_name = order.user.email
            
        Invoice.objects.create(
            order=order,
            seller=seller,
            customer_name=customer_name,
            customer_email=order.user.email,
            seller_name=seller_name,
            total_amount=total_amount,
            commission_amount=commission_amount,
            seller_amount=seller_amount,
            payment_method=instance.method,
            payment_status=payment_status
        )
