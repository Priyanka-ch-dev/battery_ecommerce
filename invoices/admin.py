from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_id', 'order', 'seller_name', 'total_amount', 'payment_status', 'invoice_date']
    list_filter = ['payment_status', 'payment_method', 'invoice_date']
    search_fields = ['invoice_id', 'customer_name', 'customer_email', 'seller_name']
    readonly_fields = ['invoice_id', 'invoice_date']
