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
                    item_total = item.price * item.quantity
                    commission_rate = item.seller.commission_rate
                    
                    admin_cut = (item_total * commission_rate) / Decimal('100.00')
                    seller_earnings = item_total - admin_cut
                    
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
