from django.db import models
from django.conf import settings
from products.models import Vehicle

class ServiceAvailability(models.Model):
    zipcode = models.CharField(max_length=20, unique=True)
    city = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Service Availabilities'

    def __str__(self):
        return f"{self.zipcode} - {self.city} ({'Available' if self.is_available else 'Not Available'})"

class ServiceBooking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_bookings')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_bookings')
    address = models.TextField()
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, related_name='service_bookings')
    scheduled_date = models.DateField()
    scheduled_time = models.CharField(max_length=50) # e.g. "10:00 AM - 12:00 PM"
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id} on {self.scheduled_date} by {self.customer.email}"
