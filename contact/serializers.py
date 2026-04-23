from rest_framework import serializers
from .models import ContactSettings

from .models import ContactSettings, ContactMessage

class ContactSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSettings
        fields = ['id', 'company_name', 'support_email', 'support_phone', 'address', 'support_hours']

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ['is_read', 'created_at']
