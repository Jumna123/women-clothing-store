from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q  # ← import Q directly, not models.Q
from apps.home.models import Order
import csv
from django.http import HttpResponse

def orders(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    orders_qs = Order.objects.select_related('user').order_by('-created_at')

    if q:
        orders_qs = orders_qs.filter(
            Q(id__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    if status:
        orders_qs = orders_qs.filter(status=status)

    paginator = Paginator(orders_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, "adminpanel/order.html", {
        "orders": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "current_status": status,
        "status_choices": Order.STATUS_CHOICES,
    })


@require_POST
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    valid = [s[0] for s in Order.STATUS_CHOICES]
    if new_status in valid:
        order.status = new_status
        order.save()
        messages.success(request, f"Order #{order.id} status updated to {new_status}.")
    return redirect('adminpanel:orders')


@require_POST
def handle_return(request, pk):
    order = get_object_or_404(Order, pk=pk)
    action = request.POST.get('action')
    if order.status == 'return_requested':
        if action == 'approve':
            order.status = 'returned'
            messages.success(request, f"Return approved for Order #{order.id}.")
        elif action == 'reject':
            order.status = 'delivered'
            messages.warning(request, f"Return rejected for Order #{order.id}.")
        order.save()
    return redirect('adminpanel:orders')



def export_orders(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    orders_qs = Order.objects.select_related('user').order_by('-created_at')

    if q:
        orders_qs = orders_qs.filter(
            Q(id__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    if status:
        orders_qs = orders_qs.filter(status=status)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'

    writer = csv.writer(response)

    # Header row
    writer.writerow([
        'Order ID', 'Customer Name', 'Email',
        'Date', 'Total Amount', 'Status',
        'Payment Method', 'Return Reason'
    ])

    # Data rows
    for order in orders_qs:
        writer.writerow([
            f'ORD-{order.id}',
            f'{order.user.first_name} {order.user.last_name}',
            order.user.email,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.total_amount,
            order.get_status_display(),
            order.get_payment_method_display() if hasattr(order, 'payment_method') else 'N/A',
            order.return_reason or '',
        ])

    return response