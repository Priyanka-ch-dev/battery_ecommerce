from django.db import models

class ContactSettings(models.Model):
    company_name = models.CharField(max_length=255)
    support_email = models.EmailField(max_length=255)
    support_phone = models.CharField(max_length=50)
    address = models.TextField()
    support_hours = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Contact Settings"

    def __str__(self):
        return "Global Contact Settings"

    def save(self, *args, **kwargs):
        # Singleton pattern: ensure only one row exists
        if not self.pk and ContactSettings.objects.exists():
            return
        super().save(*args, **kwargs)

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"
