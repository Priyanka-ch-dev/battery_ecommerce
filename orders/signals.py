from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem, Order
from django.db import transaction
from decimal import Decimal

@receiver(post_save, sender=OrderItem)
def reduce_product_stock(sender, instance, created, **kwargs):
    if created and instance.product:
        with transaction.atomic():
            from products.models import Product
            product = Product.objects.select_for_update().get(id=instance.product.id)
            if product.stock >= instance.quantity:
                product.stock -= instance.quantity
                product.save()

@receiver(post_save, sender=Order)
def process_seller_commission(sender, instance, **kwargs):
    # Process payout only when order is COMPLETED
    if instance.status == Order.Status.COMPLETED:
        with transaction.atomic():
            from sellers.models import SellerWallet, WalletTransaction
            
            ref = f"Order #{instance.id}"
            
            # Prevent double-crediting
            if WalletTransaction.objects.filter(reference=ref).exists():
                return
                
            for item in instance.items.all():
                if item.product and item.seller:
                    seller_earnings = item.seller_earning
                    
                    wallet, _ = SellerWallet.objects.get_or_create(seller=item.seller)
                    wallet.balance += round(seller_earnings, 2)
                    wallet.total_earned += round(seller_earnings, 2)
                    wallet.save()
                    
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type=WalletTransaction.Type.CREDIT,
                        amount=round(seller_earnings, 2),
                        reference=ref
                    )

from django.db.models.signals import pre_save
import re

@receiver(pre_save, sender=Order)
def handle_order_cancellation(sender, instance, **kwargs):
    if instance.pk:
        try:
            original = Order.objects.get(pk=instance.pk)
            if original.status != Order.Status.CANCELLED and instance.status == Order.Status.CANCELLED:
                # Decrement current bookings
                if instance.delivery_date and instance.delivery_time:
                    pincode = None
                    match = re.search(r'\b\d{6}\b', instance.shipping_address)
                    if match:
                        pincode = match.group(0)
                    
                    if pincode:
                        from .models import DeliverySlot
                        slot = DeliverySlot.objects.filter(
                            date=instance.delivery_date,
                            time_slot=instance.delivery_time,
                            pincode=pincode
                        ).first()
                        if slot and slot.current_bookings > 0:
                            slot.current_bookings -= 1
                            slot.save()
        except Order.DoesNotExist:
            pass

