from django.db import models
from django.utils import timezone
from datetime import timedelta

class OTPRecord(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = 'REGISTER', 'Registration'
        LOGIN = 'LOGIN', 'Login'
        DELIVERY = 'DELIVERY', 'Delivery Verification'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'

    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # OTP expires in 5 minutes by default
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.purpose} OTP for {self.phone_number} (Verified: {self.is_verified})"
    

    