from django.db.models.signals import post_save
from django.dispatch import receiver
from payments.models import Payment
from invoices.models import Invoice
from invoices.utils import send_invoice_email

@receiver(post_save, sender=Payment)
def generate_invoice_on_payment(sender, instance, created, **kwargs):
    order = instance.order
    
    # Determine payment status
    # In Payment model: CustomerStatus.SUCCESS, PAID, COLLECTED (COD)
    is_paid = instance.status in ['SUCCESS', 'PAID'] or (instance.method == 'COD' and instance.status == 'COLLECTED')
    payment_status = 'PAID' if is_paid else 'PENDING'

    # Handle existing invoices
    invoices = Invoice.objects.filter(order=order)
    if invoices.exists():
        for inv in invoices:
            old_status = inv.payment_status
            inv.payment_method = instance.method
            inv.payment_status = payment_status
            inv.save()
            
            # If it just became paid, or if it's paid and we haven't sent it (optional check)
            # User specifically asked to ensure it sends when successful/paid
            if payment_status == 'PAID' and old_status != 'PAID':
                send_invoice_email(inv)
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
            
        new_invoice = Invoice.objects.create(
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
        
        # Auto-send email to customer
        send_invoice_email(new_invoice)
