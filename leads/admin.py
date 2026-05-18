from django.contrib import admin
from .models import Lead

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'contact_number', 'user', 'created_at']
    search_fields = ['name', 'contact_number', 'user__email']
    list_filter = ['created_at']
