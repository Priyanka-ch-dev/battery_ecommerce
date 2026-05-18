from django.db import migrations

def update_existing_ids(apps, schema_editor):
    ComboProduct = apps.get_model('products', 'ComboProduct')
    ComboProductImage = apps.get_model('products', 'ComboProductImage')
    ComboProductSpecification = apps.get_model('products', 'ComboProductSpecification')
    
    # Try to get OrderItem and CartItem
    try:
        OrderItem = apps.get_model('orders', 'OrderItem')
    except LookupError:
        OrderItem = None
    try:
        CartItem = apps.get_model('cart', 'CartItem')
    except LookupError:
        CartItem = None
    
    # Move ComboProducts to start from 1000 to avoid collision with existing Products (max 12)
    for i, combo in enumerate(ComboProduct.objects.all().order_by('id')):
        old_id = combo.id
        new_id = 1000 + i
        
        # Update references
        ComboProductImage.objects.filter(combo_product_id=old_id).update(combo_product_id=new_id)
        ComboProductSpecification.objects.filter(combo_product_id=old_id).update(combo_product_id=new_id)
        if OrderItem:
            OrderItem.objects.filter(combo_product_id=old_id).update(combo_product_id=new_id)
        if CartItem:
            CartItem.objects.filter(combo_product_id=old_id).update(combo_product_id=new_id)
        
        # Update the combo itself
        ComboProduct.objects.filter(id=old_id).update(id=new_id)

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0018_comboproduct_pincodes_product_pincodes'),
    ]

    operations = [
        migrations.RunPython(update_existing_ids),
    ]
