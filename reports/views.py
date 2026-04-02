from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.utils import timezone
from .models import ReportExportJob
from .serializers import ReportExportJobSerializer

from orders.models import Order
from users.models import User
from products.models import Product

class ReportsViewSet(viewsets.ModelViewSet):
    queryset = ReportExportJob.objects.all()
    serializer_class = ReportExportJobSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_date_filters(self, request):
        period = request.query_params.get('period') # e.g. 'daily', 'monthly'
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        from django.utils import timezone
        filters = {}
        if period == 'daily':
            filters['created_at__date'] = timezone.now().date()
        elif period == 'monthly':
            filters['created_at__month'] = timezone.now().month
            filters['created_at__year'] = timezone.now().year
        else:
            if start_date:
                filters['created_at__gte'] = start_date
            if end_date:
                filters['created_at__lte'] = end_date
        return filters

    @action(detail=False, methods=['get'])
    def sales_report(self, request):
        filters = self.get_date_filters(request)
        filters['status'] = Order.Status.COMPLETED
        qs = Order.objects.filter(**filters)
        
        data = qs.aggregate(
            total_sales_count=Count('id'),
            total_revenue=Sum('grand_total'),
            total_gst=Sum('tax')
        )
        return Response({
            'total_sales_count': data['total_sales_count'] or 0,
            'total_revenue': data['total_revenue'] or 0,
            'total_gst': data['total_gst'] or 0
        })

    @action(detail=False, methods=['get'])
    def order_report(self, request):
        filters = self.get_date_filters(request)
        qs = Order.objects.filter(**filters)
        
        return Response({
            'total_orders': qs.count(), 
            'completed': qs.filter(status=Order.Status.COMPLETED).count(),
            'pending': qs.filter(status=Order.Status.PENDING).count(),
            'cancelled': qs.filter(status=Order.Status.CANCELLED).count()
        })
        
    @action(detail=False, methods=['get'])
    def product_report(self, request):
        filters = self.get_date_filters(request)
        from orders.models import OrderItem
        
        oi_filters = {f"order__{k}": v for k, v in filters.items()} 
        oi_filters["order__status"] = Order.Status.COMPLETED

        top_selling = OrderItem.objects.filter(**oi_filters).values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:10]
        stock_levels = Product.objects.values('name', 'stock').order_by('stock')[:15]
        
        return Response({
            'top_selling_products': top_selling,
            'stock_levels': stock_levels
        })

    @action(detail=False, methods=['get'])
    def seller_report(self, request):
        from sellers.models import SellerWallet
        earnings = SellerWallet.objects.values('seller__business_name').annotate(
            total_cumulative_earned=Sum('total_earned'), 
            current_wallet_balance=Sum('balance')
        ).order_by('-total_cumulative_earned')
        
        return Response({
            'seller_earnings': earnings
        })
