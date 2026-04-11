from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from apps.adminpanel.models import Product, Category, Collection
from apps.home.models import Order
from django.contrib.auth import get_user_model
from apps.adminpanel.decorators import admin_required

User = get_user_model()


@admin_required
def admin_dashboard(request):
    # ── Stats cards ──
    total_products    = Product.objects.count()
    total_categories  = Category.objects.count()
    total_collections = Collection.objects.count()
    total_orders      = Order.objects.count()
    total_users       = User.objects.filter(is_staff=False).count()

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
        'recent_orders':     recent_orders,
    })