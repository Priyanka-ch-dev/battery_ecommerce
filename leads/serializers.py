from rest_framework import serializers
from .models import Lead

class LeadSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Lead
        fields = ['id', 'user', 'user_email', 'name', 'contact_number', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
