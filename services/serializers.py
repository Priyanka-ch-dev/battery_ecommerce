from rest_framework import serializers
from .models import ServiceAvailability, ServiceBooking

class ServiceAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceAvailability
        fields = '__all__'

class ServiceBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceBooking
        fields = '__all__'
        read_only_fields = ['customer', 'status']

    def validate_scheduled_date(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Scheduled date cannot be in the past.")
        return value

    def validate(self, data):
        date = data.get('scheduled_date')
        time = data.get('scheduled_time')
        if date and time:
            if ServiceBooking.objects.filter(scheduled_date=date, scheduled_time=time).count() >= 3:
                raise serializers.ValidationError({"scheduled_time": "This time slot is fully booked."})
        return data
