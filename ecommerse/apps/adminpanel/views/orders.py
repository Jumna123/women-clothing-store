from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.home.models import Order, OrderItem, ReturnRequest
from django.contrib.admin.views.decorators import staff_member_required

import csv
from django.http import HttpResponse

@staff_member_required(login_url='accounts:userlogin')
def orders(request):
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    orders_qs = Order.objects.select_related('user').prefetch_related(
        'items__product', 'return_requests'
    ).order_by('-created_at')

    if q:
        orders_qs = orders_qs.filter(
            Q(id__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    if status == 'exchange_requested':
        orders_qs = orders_qs.filter(
            status='return_requested',
            return_requests__return_type='exchange'
        ).distinct()
    elif status == 'return_requested':
        orders_qs = orders_qs.filter(
            status='return_requested',
            return_requests__return_type='return'
        ).distinct()
    elif status:
        orders_qs = orders_qs.filter(status=status)

    paginator = Paginator(orders_qs, 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, "adminpanel/order.html", {
        "orders":         page_obj,
        "page_obj":       page_obj,
        "total_count":    paginator.count,
        "current_status": status,
        "status_choices": Order.STATUS_CHOICES,
    })


@staff_member_required(login_url='accounts:userlogin')
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('user', 'address').prefetch_related('items__product'),
        pk=pk
    )
    return render(request, "adminpanel/order_detail.html", {"order": order})


@staff_member_required(login_url='accounts:userlogin')
@require_POST
def update_order_status(request, pk):
    order      = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    valid      = [s[0] for s in Order.STATUS_CHOICES]
    if new_status in valid:
        order.status = new_status
        if new_status == 'delivered':
            order.delivered_at = timezone.now()
        order.save()
        messages.success(request, f"Order #{order.id} updated to {order.get_status_display()}.")
    return redirect('adminpanel:orders')


# ── Return management ──────────────────────────────────────────────────────────

@staff_member_required(login_url='accounts:userlogin')
def return_requests(request):
    status_filter = request.GET.get('status', '')
    type_filter   = request.GET.get('type', '')

    items_qs = OrderItem.objects.select_related(
        'order', 'order__user', 'product'
    ).exclude(return_status='none').order_by('-return_requested_at')

    if status_filter:
        items_qs = items_qs.filter(return_status=status_filter)

    # Filter by return type via the related ReturnRequest
    if type_filter in ('return', 'exchange'):
        items_qs = items_qs.filter(
            return_requests__return_type=type_filter
        ).distinct()

    paginator = Paginator(items_qs, 15)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, "adminpanel/return_requests.html", {
        "items":                 page_obj,
        "page_obj":              page_obj,
        "return_status_choices": OrderItem.RETURN_STATUS_CHOICES,
        "current_status":        status_filter,
        "current_type":          type_filter,
    })


@staff_member_required(login_url='accounts:userlogin')
@require_POST
def handle_return(request, pk):
    order = get_object_or_404(Order, pk=pk)
    action = request.POST.get('action')

    return_req = order.return_requests.order_by('-created_at').first()
    if not return_req:
        messages.error(request, "No return request found for this order.")
        return redirect('adminpanel:orders')

    is_exchange = return_req.return_type == 'exchange'
    label = "Exchange" if is_exchange else "Return"

    # ── approve ───────────────────────────────────────────────────────────────
    if action == 'approve' and return_req.status == 'requested':
        return_req.status = 'approved'
        return_req.save()
        return_req.items.filter(
            return_status__in=['return_requested', 'exchange_requested']
        ).update(return_status='return_approved')
        messages.success(request, f"{label} #{return_req.id} approved for Order #{order.id}.")

    # ── reject ────────────────────────────────────────────────────────────────
    elif action == 'reject' and return_req.status == 'requested':
        rejected_reason = request.POST.get('rejected_reason', 'Not eligible')
        return_req.status = 'rejected'
        return_req.rejected_reason = rejected_reason
        return_req.save()
        order.status = 'delivered'
        order.save()
        return_req.items.all().update(return_status='return_rejected')
        messages.warning(request, f"{label} #{return_req.id} rejected for Order #{order.id}.")

    # ── schedule_pickup ───────────────────────────────────────────────────────
    elif action == 'schedule_pickup' and return_req.status == 'approved':
        return_req.status = 'pickup_scheduled'
        return_req.save()
        return_req.items.all().update(return_status='pickup_scheduled')
        messages.success(request, f"Pickup scheduled for {label} #{return_req.id}.")

    # ── mark_received ─────────────────────────────────────────────────────────
    elif action == 'mark_received' and return_req.status in ('pickup_scheduled', 'picked_up', 'in_transit'):
        return_req.status = 'received'
        return_req.save()
        return_req.items.all().update(return_status='received_at_warehouse')
        messages.info(request, f"{label} #{return_req.id} marked as received at warehouse.")

    # ── inspection_pass ───────────────────────────────────────────────────────
    elif action == 'inspection_pass' and return_req.status == 'received':
        return_req.status = 'inspection_passed'
        return_req.inspection_notes = request.POST.get('inspection_notes', '')
        return_req.save()
        return_req.items.all().update(return_status='inspection_passed')
        if is_exchange:
            messages.success(request, f"Inspection passed for Exchange #{return_req.id}. Ready to process exchange.")
        else:
            messages.success(request, f"Inspection passed for Return #{return_req.id}. Ready to refund ₹{return_req.total_refund_amount}.")

    # ── inspection_fail ───────────────────────────────────────────────────────
    elif action == 'inspection_fail' and return_req.status == 'received':
        return_req.status = 'inspection_failed'
        return_req.inspection_notes = request.POST.get('inspection_notes', 'Failed quality check')
        return_req.save()
        return_req.items.all().update(return_status='inspection_failed')
        messages.warning(request, f"Inspection failed for {label} #{return_req.id}.")

    # ── process_refund / process_exchange ─────────────────────────────────────
    elif action == 'process_refund' and return_req.status == 'inspection_passed':
        refund_method = request.POST.get('refund_method', 'original')
        return_req.status = 'refund_initiated'
        return_req.refund_method = refund_method
        if not is_exchange:
            return_req.refund_amount = return_req.total_refund_amount
        return_req.save()
        return_req.items.all().update(return_status='refund_initiated')
        if is_exchange:
            messages.success(request, f"Exchange processing initiated for Exchange #{return_req.id}.")
        else:
            messages.success(request, f"Refund of ₹{return_req.refund_amount} initiated for Return #{return_req.id}.")

    # ── mark_refunded / mark_exchange_complete ────────────────────────────────
    elif action == 'mark_refunded' and return_req.status in ('refund_initiated', 'refund_processing'):
        refund_ref = request.POST.get('refund_ref', f'REF-{order.id}-{return_req.id}')
        return_req.status = 'refunded'
        return_req.refund_ref = refund_ref
        return_req.save()
        if is_exchange:
            return_req.items.all().update(return_status='exchanged')
            order.status = 'delivered'  # exchange done — order goes back to delivered
            order.save()
            messages.success(request, f"Exchange #{return_req.id} completed. Replacement should now be dispatched for Order #{order.id}.")
        else:
            return_req.items.all().update(return_status='refunded')
            order.status = 'returned'
            order.save()
            messages.success(request, f"Return #{return_req.id} fully refunded. Order #{order.id} marked as returned.")

    else:
        messages.error(request, f"Invalid action '{action}' for current {label.lower()} status '{return_req.status}'.")

    return redirect('adminpanel:orders')


@staff_member_required(login_url='accounts:userlogin')
@require_POST
def handle_return_item(request, item_id):
    item   = get_object_or_404(OrderItem.objects.select_related('order', 'product'), id=item_id)
    order  = item.order
    action = request.POST.get('action')

    # Determine if this item belongs to an exchange request
    return_req  = item.return_requests.order_by('-created_at').first()
    is_exchange = return_req and return_req.return_type == 'exchange'
    label       = "exchange" if is_exchange else "return"

    if action == 'approve':
        if item.return_status in ('return_requested', 'exchange_requested'):
            item.return_status = 'return_approved'
            item.save()
            messages.success(request, f"Approved {label} for '{item.product.product_name}'.")

    elif action == 'reject':
        if item.return_status in ('return_requested', 'exchange_requested'):
            item.return_status = 'return_rejected'
            item.save()
            _maybe_revert_order(order)
            messages.warning(request, f"Rejected {label} for '{item.product.product_name}'.")

    elif action == 'schedule_pickup':
        if item.return_status == 'return_approved':
            item.return_status       = 'pickup_scheduled'
            item.pickup_scheduled_at = timezone.now()
            item.save()
            messages.success(request, f"Pickup scheduled for '{item.product.product_name}'.")

    elif action == 'mark_picked_up':
        if item.return_status == 'pickup_scheduled':
            item.return_status = 'picked_up'
            item.save()

    elif action == 'mark_in_transit':
        if item.return_status in ('picked_up', 'return_approved'):
            item.return_status = 'in_transit'
            item.save()

    elif action == 'mark_received':
        if item.return_status in ('in_transit', 'picked_up'):
            item.return_status = 'received_at_warehouse'
            item.save()
            messages.info(request, f"'{item.product.product_name}' received. Ready for inspection.")

    elif action == 'inspection_pass':
        if item.return_status == 'received_at_warehouse':
            item.return_status    = 'inspection_passed'
            item.inspection_notes = request.POST.get('inspection_notes', '')
            item.inspected_at     = timezone.now()
            if not is_exchange:
                item.refund_amount = item.subtotal
            item.save()
            if is_exchange:
                messages.success(request, f"Inspection passed for '{item.product.product_name}'. Ready to process exchange.")
            else:
                messages.success(request, f"Inspection passed. Refund ₹{item.refund_amount} ready.")

    elif action == 'inspection_fail':
        if item.return_status == 'received_at_warehouse':
            item.return_status    = 'inspection_failed'
            item.inspection_notes = request.POST.get('inspection_notes', '')
            item.inspected_at     = timezone.now()
            item.save()
            messages.warning(request, f"Inspection failed for '{item.product.product_name}'.")

    elif action == 'initiate_refund':
        if item.return_status == 'inspection_passed':
            from decimal import Decimal
            item.return_status = 'refund_initiated'
            item.refund_method = request.POST.get('refund_method', 'original')
            if not is_exchange:
                custom_amount = request.POST.get('refund_amount', '')
                if custom_amount:
                    item.refund_amount = Decimal(custom_amount)
            item.save()
            if is_exchange:
                messages.success(request, f"Exchange processing initiated for '{item.product.product_name}'.")
            else:
                messages.success(request, f"Refund ₹{item.refund_amount} initiated for '{item.product.product_name}'.")

    elif action == 'complete_refund':
        if item.return_status in ('refund_initiated', 'refund_processing'):
            if is_exchange:
                item.return_status = 'exchanged'
            else:
                item.return_status = 'refunded'
            item.refunded_at = timezone.now()
            item.save()
            _maybe_close_return(order)
            if is_exchange:
                messages.success(request, f"Exchange completed for '{item.product.product_name}'. Dispatch the replacement.")
            else:
                messages.success(request, f"Refund completed for '{item.product.product_name}'.")

    return redirect('adminpanel:return_requests')


def _maybe_revert_order(order):
    still_pending = order.items.filter(
        return_status__in=['return_requested', 'exchange_requested']
    ).exists()
    if not still_pending:
        order.status = 'delivered'
        order.save()


def _maybe_close_return(order):
    unresolved = order.items.exclude(
        return_status__in=[
            'refunded', 'returned', 'exchanged',
            'none', 'return_rejected', 'inspection_failed'
        ]
    ).exists()
    if not unresolved:
        has_exchanged = order.items.filter(return_status='exchanged').exists()
        has_refunded  = order.items.filter(return_status='refunded').exists()
        if has_exchanged and not has_refunded:
            order.status = 'delivered'  # exchange done, order active again
        else:
            order.status = 'returned'
        order.save()


@staff_member_required(login_url='accounts:userlogin')
def export_orders(request):
    q      = request.GET.get('q', '').strip()
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

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer   = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Date', 'Total', 'Status', 'Payment', 'Return Reason'])

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