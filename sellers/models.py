from django.db import models
from django.conf import settings

from django.core.validators import RegexValidator

class SellerProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    # Validators
    gst_validator = RegexValidator(regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', message="Invalid GST format")
    pan_validator = RegexValidator(regex=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', message="Invalid PAN format")
    aadhaar_validator = RegexValidator(regex=r'^[0-9]{12}$', message="Invalid Aadhaar format (12 digits required)")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=255)
    gst_number = models.CharField(max_length=15, validators=[gst_validator], blank=True, null=True)
    pan_number = models.CharField(max_length=10, validators=[pan_validator], blank=True, null=True)
    aadhaar_number = models.CharField(max_length=12, validators=[aadhaar_validator], blank=True, null=True)
    shop_license_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Documents
    pan_card_copy = models.FileField(upload_to='seller_docs/pan/', blank=True, null=True)
    aadhaar_card_copy = models.FileField(upload_to='seller_docs/aadhaar/', blank=True, null=True)
    shop_license_copy = models.FileField(upload_to='seller_docs/license/', blank=True, null=True)
    authorized_letter = models.FileField(upload_to='seller_docs/auth/', blank=True, null=True)
    
    # Bank Details
    bank_account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_passbook_copy = models.FileField(upload_to='seller_docs/bank/', blank=True, null=True)
    
    # Address
    business_address = models.TextField(blank=True, null=True)

    # Images
    shop_image = models.ImageField(upload_to='seller_docs/shops/', blank=True, null=True)
    owner_image = models.ImageField(upload_to='seller_docs/owners/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_approved = models.BooleanField(default=False)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Percentage commission, e.g., 5.00 for 5%")
    
    def save(self, *args, **kwargs):
        # Sync is_approved with status
        self.is_approved = self.status == self.Status.APPROVED
        super().save(*args, **kwargs)

    def __str__(self):
        return self.business_name

class SellerWallet(models.Model):
    seller = models.OneToOneField(SellerProfile, on_delete=models.CASCADE, related_name='wallet')
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payable_to_admin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="COD commissions due to platform")
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Wallet - {self.seller.business_name}"

class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    class Category(models.TextChoices):
        SALE = 'SALE', 'Sale'
        COMMISSION = 'COMMISSION', 'Commission Deduction'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
        SETTLEMENT = 'SETTLEMENT', 'Settlement'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SETTLED = 'SETTLED', 'Settled'

    wallet = models.ForeignKey(SellerWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=Type.choices)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SALE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=255, help_text="Order ID or Withdrawal ID")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} of {self.amount} for {self.wallet.seller.business_name}"

class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        REJECTED = 'REJECTED', 'Rejected'

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.seller.business_name} - {self.amount} - {self.status}"

class Settlement(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    transactions = models.ManyToManyField(WalletTransaction, related_name='settlements')
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settlement - {self.seller.business_name} - {self.amount} - {self.status}"
