from rest_framework import viewsets, permissions
from core.permissions import IsAdminUser
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
    permission_classes = [IsAdminUser]

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
        filters['status'] = Order.Status.DELIVERED
        qs = Order.objects.filter(**filters)
        
        data = qs.aggregate(
            total_sales_count=Count('id'),
            total_revenue=Sum('grand_total'),
            total_gst=Sum('tax')
        )

        from orders.models import OrderItem
        commission_data = OrderItem.objects.filter(order__in=qs).aggregate(
            total_commission=Sum('admin_commission_amount')
        )

        return Response({
            'total_sales_count': data['total_sales_count'] or 0,
            'total_revenue': data['total_revenue'] or 0,
            'total_gst': data['total_gst'] or 0,
            'total_commission': commission_data['total_commission'] or 0
        })

    @action(detail=False, methods=['get'])
    def order_report(self, request):
        filters = self.get_date_filters(request)
        qs = Order.objects.filter(**filters)
        
        return Response({
            'total_orders': qs.count(), 
            'completed': qs.filter(status=Order.Status.DELIVERED).count(),
            'pending': qs.filter(status=Order.Status.PENDING).count(),
            'cancelled': qs.filter(status=Order.Status.CANCELLED).count()
        })
        
    @action(detail=False, methods=['get'])
    def product_report(self, request):
        filters = self.get_date_filters(request)
        from orders.models import OrderItem
        
        oi_filters = {f"order__{k}": v for k, v in filters.items()} 
        oi_filters["order__status"] = Order.Status.DELIVERED

        top_selling = OrderItem.objects.filter(**oi_filters).values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:10]
        stock_levels = Product.objects.values('name', 'stock').order_by('stock')[:15]
        
        return Response({
            'top_selling_products': top_selling,
            'stock_levels': stock_levels
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Unified dashboard summary data"""
        try:
            # 1. Lifetime & Avg Sales
            completed_orders = Order.objects.filter(status__in=[Order.Status.DELIVERED, Order.Status.COMPLETED])
            total_revenue = completed_orders.aggregate(total=Sum('grand_total'))['total'] or 0
            order_count = completed_orders.count()
            avg_value = total_revenue / order_count if order_count > 0 else 0

            # 2. Last Order & Real-time Metrics
            from django.utils import timezone
            today = timezone.now().date()
            
            last_order = Order.objects.order_by('-created_at').first()
            all_orders_count = Order.objects.count()
            seller_count = User.objects.filter(role=User.Role.SELLER).count()
            
            orders_today = Order.objects.filter(created_at__date=today).count()
            sellers_today = User.objects.filter(role=User.Role.SELLER, date_joined__date=today).count()
            sales_today = Order.objects.filter(created_at__date=today, status__in=[Order.Status.DELIVERED, Order.Status.COMPLETED]).aggregate(total=Sum('grand_total'))['total'] or 0
            
            # 3. Top Selling (Recharts)
            from orders.models import OrderItem
            best_sellers = OrderItem.objects.all().values('product__name').annotate(sales=Sum('quantity')).order_by('-sales')[:5]

            # 4. Most Viewed (Recharts)
            most_viewed = Product.objects.filter(is_active=True).values('name', 'view_count').order_by('-view_count')[:7]

            # 5. New Customers Growth (Recharts - last 7 weeks)
            from django.db.models.functions import TruncWeek
            customer_growth = User.objects.filter(role=User.Role.CUSTOMER).annotate(week=TruncWeek('date_joined')).values('week').annotate(count=Count('id')).order_by('week')[:7]

            # 6. Real Search Terms (Dynamic)
            from products.models import SearchQuery
            last_search_terms = SearchQuery.objects.order_by('-updated_at').values_list('query', flat=True)[:5]
            top_search_terms = SearchQuery.objects.order_by('-count').values_list('query', flat=True)[:5]

            return Response({
                'metrics': {
                    'lifetime_sales': float(total_revenue),
                    'lifetime_commission': float(OrderItem.objects.filter(order__in=completed_orders).aggregate(total=Sum('admin_commission_amount'))['total'] or 0),
                    'avg_order_value': round(float(avg_value), 2),
                    'total_orders': all_orders_count,
                    'total_sellers': seller_count,
                    'orders_today': orders_today,
                    'sellers_today': sellers_today,
                    'sales_today': float(sales_today),
                    'commission_today': float(OrderItem.objects.filter(order__in=Order.objects.filter(created_at__date=today, status__in=[Order.Status.DELIVERED, Order.Status.COMPLETED])).aggregate(total=Sum('admin_commission_amount'))['total'] or 0),
                    'last_order': {
                        'id': last_order.id if last_order else None,
                        'created_at': last_order.created_at if last_order else None
                    }
                },
                'best_sellers': best_sellers,
                'most_viewed': most_viewed,
                'customer_growth': [
                    {'name': f"Week {i+1}", 'count': c['count']} for i, c in enumerate(customer_growth)
                ],
                'last_search_terms': list(last_search_terms),
                'top_search_terms': list(top_search_terms)
            })
        except Exception as e:
            # Log the full error to server console for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Dashboard Summary Error: {str(e)}", exc_info=True)
            
            # Return partial but valid data structure
            return Response({
                'metrics': {'lifetime_sales': 0, 'avg_order_value': 0, 'last_order': None},
                'best_sellers': [],
                'most_viewed': [],
                'customer_growth': [],
                'last_search_terms': [],
                'top_search_terms': [],
                'error': str(e) # Pass error message for debugging in console
            }, status=200) # Status 200 to allow frontend to handle gracefully
