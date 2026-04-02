from rest_framework import serializers
from .models import ReportExportJob

class ReportExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportExportJob
        fields = '__all__'
        read_only_fields = ['requested_by', 'status', 'file_url', 'completed_at']
