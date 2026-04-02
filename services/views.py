from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ServiceAvailability, ServiceBooking
from .serializers import ServiceAvailabilitySerializer, ServiceBookingSerializer

class ServiceAvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceAvailability.objects.all()
    serializer_class = ServiceAvailabilitySerializer
    filterset_fields = ['is_available', 'city']
    search_fields = ['zipcode', 'city']
    ordering_fields = ['zipcode']

class ServiceBookingViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'scheduled_date']
    search_fields = ['address']
    ordering_fields = ['scheduled_date', 'created_at']

    def get_queryset(self):
        return ServiceBooking.objects.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        date = request.query_params.get('date')
        if not date:
            return Response({'error': 'Please provide a date'}, status=400)
            
        all_slots = ["10:00 AM - 12:00 PM", "12:00 PM - 02:00 PM", "02:00 PM - 04:00 PM", "04:00 PM - 06:00 PM"]
        available = []
        for slot in all_slots:
            if ServiceBooking.objects.filter(scheduled_date=date, scheduled_time=slot).count() < 3:
                available.append(slot)
                
        return Response({'date': date, 'available_slots': available})
