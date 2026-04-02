from django.db import models
from django.conf import settings

class ReportExportJob(models.Model):
    class ReportType(models.TextChoices):
        SALES = 'SALES', 'Sales Report'
        ORDERS = 'ORDERS', 'Orders Report'
        CUSTOMERS = 'CUSTOMERS', 'Customer Report'
        PRODUCTS = 'PRODUCTS', 'Product Report'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.report_type} requested by {self.requested_by.email} - {self.status}"
