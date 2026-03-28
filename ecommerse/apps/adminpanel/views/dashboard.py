from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from apps.adminpanel.models import Product, Category, Collection
from apps.home.models import Order
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'Only admin can access')
        return redirect('accounts:admin_login')

    # ── Stats cards ──
    total_products   = Product.objects.count()
    total_categories = Category.objects.count()
    total_collections = Collection.objects.count()
    total_orders     = Order.objects.count()
    total_users      = User.objects.filter(is_staff=False).count()

    # ── Revenue this month ──
    now = timezone.now()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0)
    monthly_revenue = Order.objects.filter(
        created_at__gte=first_of_month,
        status__in=['delivered', 'shipped', 'processing']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # ── Weekly revenue for chart (last 4 weeks) ──
    weeks = []
    for i in range(3, -1, -1):
        week_start = now - timedelta(weeks=i+1)
        week_end   = now - timedelta(weeks=i)
        revenue = Order.objects.filter(
            created_at__gte=week_start,
            created_at__lt=week_end,
            status__in=['delivered', 'shipped', 'processing']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        weeks.append(float(revenue))

    # Normalize for SVG chart (0–200 range)
    max_val = max(weeks) if max(weeks) > 0 else 1
    chart_points = [round(200 - (w / max_val * 180)) for w in weeks]

    # ── Recent orders ──
    recent_orders = Order.objects.select_related(
        'user'
    ).prefetch_related(
        'items__product__images'
    ).order_by('-created_at')[:5]

    return render(request, 'adminpanel/dashboard.html', {
        'total_products':    total_products,
        'total_categories':  total_categories,
        'total_collections': total_collections,
        'total_orders':      total_orders,
        'total_users':       total_users,
        'monthly_revenue':   monthly_revenue,
        'weeks':             weeks,
        'chart_points':      chart_points,
        'recent_orders':     recent_orders,
    })