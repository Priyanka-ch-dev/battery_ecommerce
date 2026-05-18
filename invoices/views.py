from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from .models import Invoice
from .serializers import InvoiceSerializer
from .utils import generate_invoice_pdf
from core.permissions import IsAdminUser, IsApprovedSeller, IsCustomer

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows invoices to be viewed or listed.
    """
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['payment_status', 'payment_method', 'seller', 'order']
    search_fields = ['customer_name', 'customer_email', 'invoice_id', 'order__id']
    ordering_fields = ['invoice_date', 'total_amount']
    ordering = ['-invoice_date']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Invoice.objects.none()
            
        if getattr(user, 'role', '') == 'ADMIN' or getattr(user, 'is_superuser', False):
            return Invoice.objects.all()
        elif getattr(user, 'role', '') == 'SELLER':
            return Invoice.objects.filter(seller__user=user)
        else:
            # Assume CUSTOMER
            return Invoice.objects.filter(order__user=user)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Action to download the invoice as a PDF file.
        """
        invoice = self.get_object()
        
        # Generate the PDF file (returns a ContentFile)
        pdf_file = generate_invoice_pdf(invoice)
        
        # Get the binary content
        pdf_content = pdf_file.read()
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_id}.pdf"'
        # Ensure the browser knows the length
        response['Content-Length'] = len(pdf_content)
        return response
